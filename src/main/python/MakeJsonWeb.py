#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import json
import logging

import MakeJson
import MakePDF

from Util import *

"""
Build a web tree of the form

static
|- figures
  |- *.png
|- pdf
  |- *.pdf
WEB-INF
|- templates
   |- rutherford
      |- *.json
|- classes
   |- resources.json

by converting each of the tex source files found in inputDir
"""
def execute(inputDir,outputDir):

    figureDir = os.path.join(outputDir,"static","figures")
    pdfDir = os.path.join(outputDir,"static","pdf")
    jsonDir = os.path.join(outputDir,"json")
    jsonFilename = os.path.join(outputDir,"WEB-INF","classes","resources.json")

    metaData = {}

    def convert(arg,dirname,fnames):
        if dirname[-6:] == "common":
            return
        for filename in fnames:
            if re.match(r'^[^\.].*\.json$',filename):
                jsonMetaFile = os.path.join(inputDir,dirname,filename)

                logging.info("%s: processing" % jsonMetaFile)

                fileHandle = open(jsonMetaFile)
                metaData = json.load(fileHandle)

                texFile = os.path.join(inputDir,"%s" % metaData['src'])

                # pdfFile = os.path.join(pdfDir,"%s.%s" % (metaData["id"],"pdf"))
                # MakePDF.execute(inputFile,pdfFile)
                jsonFile = os.path.join(jsonDir,"%s" % filename)
                MakeJson.execute(jsonMetaFile,jsonFile,inputDir,outputDir)

    os.path.walk(inputDir,convert,None)

    # HACK TIME:

    # topicPDFDir = os.path.join(inputDir,"..","..","pdf/")
    # ensureDirectory(pdfDir+"/")
    # #logging.info("topics.json")
    # #shutil.copy(os.path.join(topicPDFDir,"topics.json"),os.path.join(outputDir,"WEB-INF","classes","topics.json"))
    # for filename in os.listdir(topicPDFDir):
    #     if re.match(r'.*\.pdf$',filename):
    #         logging.info(filename)
    #         shutil.copy(os.path.join(topicPDFDir,filename),os.path.join(pdfDir,filename))
    
def main(argv):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("inputDir")
    parser.add_argument("outputDir")
    parser.add_argument("--workingDir",default=".")
    args = parser.parse_args()
    (inputDir,outputDir,workingDir) = map(os.path.abspath,(args.inputDir,args.outputDir,args.workingDir))
    ensureDirectory(workingDir+"/")
    os.chdir(workingDir)
    execute(inputDir,outputDir)


if __name__ == "__main__":
    main(sys.argv[1:])
