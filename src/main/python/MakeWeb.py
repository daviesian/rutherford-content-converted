#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import json

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

by converting each of the tex source files found in inputDir
"""
def execute(inputDir,outputDir):

    figureDir = os.path.join(outputDir,"static","figures")
    pdfDir = os.path.join(outputDir,"static","pdf")
    soyDir = os.path.join(outputDir,"WEB-INF","templates","rutherford","content");
    jsonFilename = os.path.join(outputDir,"WEB-INF","resources.json")

    metaData = []

    for filename in os.listdir(inputDir):
        if re.match(r'.*\.tex$',filename):
            print filename
            inputFile = os.path.join(inputDir,filename)
            meta = {}
            for line in file(inputFile):
                m = re.match("%% ([A-Z]+): (.*)",line.strip())
                if m:
                    meta[m.group(1)] = m.group(2)
            metaData.append(meta)   

            pdfFile = os.path.join(pdfDir,"%s.%s" % (meta["ID"],"pdf"))
            MakePDF.execute(inputFile,pdfFile)
            soyFile = os.path.join(soyDir,"%s.%s" % (meta["ID"],"soy"))
            MakeSoy.execute(inputFile,soyFile,figureDir)

    ensureDirectory(jsonFilename)
    jsonFile = file(jsonFilename,"w")
    jsonFile.write(json.dumps(metaData)+"\n")
    jsonFile.flush()

def main(argv):
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
