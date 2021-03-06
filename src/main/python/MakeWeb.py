#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import json
import logging

import MakeSoy
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
      |- *.soy
|- classes
   |- resources.json

by converting each of the tex source files found in inputDir
"""
def execute(inputDir,outputDir):

    figureDir = os.path.join(outputDir,"static","figures")
    pdfDir = os.path.join(outputDir,"static","pdf")
    soyDir = os.path.join(outputDir,"WEB-INF","templates","rutherford","content");
    jsonFilename = os.path.join(outputDir,"WEB-INF","classes","resources.json")

    metaData = {}

    def convert(arg,dirname,fnames):
        if dirname[-6:] == "common":
            return
        for filename in fnames:
            if re.match(r'^[^\.].*\.tex$',filename):
                inputFile = os.path.join(inputDir,dirname,filename)
                meta = {}
                for line in file(inputFile):
                    m = re.match("%% ([A-Z]+): (.*)",line.strip())
                    if m:
                        (key,value) = (m.group(1),m.group(2))
                        if key[-1] == "S":
                            value = re.split(r' *, *',value)
                        meta[key] = value
                if not meta.has_key("ID"):
                    logging.warning("%s: skipped - no ID defined" % filename)
                else:
                    logging.info("%s: processing" % filename)
                    metaData[meta["ID"]] = meta
                    pdfFile = os.path.join(pdfDir,"%s.%s" % (meta["ID"],"pdf"))
                    MakePDF.execute(inputFile,pdfFile)
                    soyFile = os.path.join(soyDir,"%s.%s" % (meta["ID"],"soy"))
                    MakeSoy.execute(inputFile,soyFile,figureDir)

    os.path.walk(inputDir,convert,None)

    ensureDirectory(jsonFilename)
    jsonFile = file(jsonFilename,"w")
    jsonFile.write(json.dumps(metaData)+"\n")
    jsonFile.flush()

    # HACK TIME:

    topicPDFDir = os.path.join(inputDir,"..","..","pdf/")
    ensureDirectory(pdfDir+"/")
    logging.info("topics.json")
    shutil.copy(os.path.join(topicPDFDir,"topics.json"),os.path.join(outputDir,"WEB-INF","classes","topics.json"))
    for filename in os.listdir(topicPDFDir):
        if re.match(r'.*\.pdf$',filename):
            logging.info(filename)
            shutil.copy(os.path.join(topicPDFDir,filename),os.path.join(pdfDir,filename))
    


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
