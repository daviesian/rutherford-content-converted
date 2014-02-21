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
import traceback

from latexConvert import *

def loadJsonMetaData(inputFile):
    # read json meta data to find tex file
    fileHandle = open(inputFile)
    data = json.load(fileHandle)
    return data

def initiateFileBuilder(jsonInputFile):
    # load jsonMetaDataFile for the current file of interest so we can pick which conversion process to use
    try:
        jsonMetaData = loadJsonMetaData(jsonInputFile)

        # need to provide an abspath so that other parts of the etl process can find the file
        jsonMetaData['src'] = os.path.join(os.path.split(jsonInputFile)[0], jsonMetaData['src'])
        jsonResult = jsonMetaData

        # TODO: if content property is a list then we might need to route this to various places
        # figure out what content builder to send it to - might need to loop if we have a list
        if jsonMetaData['encoding'] == 'latex':
            # send it to the LaTex Content Builder and return the object
            latexBuilder = LaTeXContentBuilder(jsonMetaData)
            contentObject = latexBuilder.process()
            return contentObject

        # TODO: aggregate the content objects into one nice structure
    except IOError:
        logging.error("%s - Unable to find referenced file. Skipping file." % jsonMetaData['src'])
        return None
    except Exception, e:
        traceback.print_exc(limit=sys.getrecursionlimit())
        print "\n"
        raw_input('Press ENTER to skip file (%s) and continue processing.' % (jsonInputFile))

        return None


def main(argv):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonInputFile")
    parser.add_argument("outputFile")
    parser.add_argument("--workingDir",default=".")
    args = parser.parse_args()
    (jsonInputFile,outputFile) = map(os.path.abspath,(args.jsonInputFile,args.outputFile))
    os.chdir(args.workingDir)

    initiateFileBuilder(jsonInputFile)

if __name__ == "__main__":
    main(sys.argv[1:])