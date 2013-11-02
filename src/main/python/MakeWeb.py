#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil

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

    for filename in os.listdir(inputDir):
        if re.match(r'.*\.tex',filename):
            print filename
            inputFile = os.path.join(inputDir,filename)
            pdfFile = os.path.join(pdfDir,changeExtension(filename,"pdf"))
            MakePDF.execute(inputFile,pdfFile)
            soyFile = os.path.join(soyDir,changeExtension(filename,"soy"))
            MakeSoy.execute(inputFile,soyFile,figureDir)


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
