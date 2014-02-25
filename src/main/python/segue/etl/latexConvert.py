#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import logging
import simplejson, json

import string

from Util import *
from latexConvertToHtml import *
from latexExtractStructure import *

#TODO need to stop accessing object dictionary directly throughout the code or may as well just use a dictionary
class Content():
    def __init__(self, jsonMetaData):
        self.__dict__ = jsonMetaData

    def to_JSON(self):
        return json.dumps(self,default=lambda o: o.__dict__, sort_keys=True, indent=4)

# Base abstract class for content builder objects
class ContentBuilderBase():
    def __init__(self):
        """
        Override with state initialization
        """
        pass
    
    def process(self):
        """
        Override with processing step
        """
        pass
    
    def finalize(self):
        """
        Override with any post-processing step (e.g. save file)
        """
        pass

# Latex content builder - should handle the conversion process for a given json metadata file
# this builder expects a jsonMetaData object that contains a src property pointing to a latex file and for the source file to be in latex format
# the metadata json will be unioned with the content generated from this builder
class LaTeXContentBuilder(ContentBuilderBase):
    def __init__(self, jsonMetaData):
        """
        1. Find LaTeX from json metadata file specified
        """
        self.jsonMetaData = jsonMetaData
        # read latex file into memory so we can do stuff with it
        self.latexSourceContents = '\n'.join(file(self.jsonMetaData['src']))
        pass
    
    def process(self):
        """
        1. Extract structure from LaTeX 
        2. Convert content extracted into HTML
        """
        contentObject = Content(self.jsonMetaData)
        if self.jsonMetaData['type'] == 'concept':
            # Currently for concept pages we want to convert the entire document into a single content object
            contentObject.children = extractStructure(self.jsonMetaData, self.latexSourceContents)

            self.convertToMarkupRecursively(contentObject.__dict__)

        elif 'legacy_latex_question' in self.jsonMetaData['type']: #or any type of question really
            # we want to extract the parts of the question that we are interested in e.g exposition, question, answers etc
            contentObject.children = extractStructure(self.jsonMetaData, self.latexSourceContents)
            
            # now we want to convert content into html
            self.convertToMarkupRecursively(contentObject.__dict__)
        else:
            logging.error("%s - Unknown content type - unable to convert latex file" % self.jsonMetaData['src'])
            return
        
        return self.finalise(contentObject)
    
    def finalise(self, objectToFinalise):
        """
        Override with any post-processing step (e.g. save file)
        """

        def recursivelyRemoveUnnecessaryProperties(objectDataStructure):
            if type(objectDataStructure) is dict:
                for propertyName, value in objectDataStructure.iteritems():
                    recursivelyRemoveUnnecessaryProperties(value)
                if 'questionid' in objectDataStructure:
                    del objectDataStructure['questionid']

            # if we are a list then we need to go through each item in the list
            elif type(objectDataStructure) is list:
                for contentItem in objectDataStructure:
                    recursivelyRemoveUnnecessaryProperties(contentItem)

        del objectToFinalise.src
        
        recursivelyRemoveUnnecessaryProperties(objectToFinalise.__dict__)

        return objectToFinalise

    '''
    Recursive function to convert our intermediate format into html
    '''
    def convertToMarkupRecursively(self,objectToConvert):
        # if we are a dictionary go through each property
        if type(objectToConvert) is dict:
            for propertyName, value in objectToConvert.iteritems():
                self.convertToMarkupRecursively(value)   

            if objectToConvert.get('encoding') == 'latex':
                if isinstance(objectToConvert.get('value'), basestring):
                    objectToConvert['value'] = convertToHtml(self.jsonMetaData, objectToConvert.get('value'))
                
                if isinstance(objectToConvert.get('answer'),basestring):
                    objectToConvert['answer'] = convertToHtml(self.jsonMetaData,objectToConvert.get('answer'))
                
                objectToConvert['encoding'] = "html"

        # if we are a list then we need to go through each item in the list
        elif type(objectToConvert) is list:
            for contentItem in objectToConvert:
                self.convertToMarkupRecursively(contentItem)