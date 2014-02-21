#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import json
import logging
import etlFileManager

from Util import *

"""
Run through the various scripts to output files which can be ingested by the segue api

example usage
./makeWeb.py ~/workspace/rutherford-content/src/main/resources/ ~/Desktop/test_new/json/

"""
def execute(inputDir,outputDir):
    jsonDir = os.path.join(outputDir,"json")

    def convert(arg,dirname,fnames):
        if dirname[-6:] == "common":
            return
        for filename in fnames:
            # look for json meta data files
            if re.match(r'^[^\.].*\.json$',filename):
                jsonMetaFile = os.path.join(inputDir,dirname,filename)
                logging.info("%s: processing" % jsonMetaFile)

                # Go off to the etlfilemanager to convert / embed this file into some useful json
                convertedObject = etlFileManager.initiateFileBuilder(jsonMetaFile)

                if convertedObject != None:
                    newJsonFile = os.path.join(outputDir,convertedObject.id+'.json')

                    # for now we can write to a file
                    with open(newJsonFile, 'w') as outfile:
                        json.dump(convertedObject.__dict__, outfile, indent=1)
                        logging.debug("writing to file %s " % outfile)

    os.path.walk(inputDir,convert,None)
    logging.info("Extraction complete! Woo hoo!")
    
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
