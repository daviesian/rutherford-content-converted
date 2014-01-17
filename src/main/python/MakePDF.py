#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import logging

from Util import *

def compileLatex(texFile):
    (sourceDirectory,sourceFile) = os.path.split(texFile)

    dviFile = changeExtension(sourceFile,"dvi")
    psFile = changeExtension(sourceFile,"ps")
    pdfFile = changeExtension(sourceFile,"pdf")
    if isNewer(texFile,dviFile):
        stem = sourceDirectory
        while not os.path.exists(os.path.join(stem,"common")):
            stem = os.path.split(stem)[0]
        commonDirectory = os.path.join(stem,"common")
        latexEnv = os.environ.copy()
        latexEnv['TEXINPUTS'] = os.pathsep.join((sourceDirectory,commonDirectory,".")) + os.pathsep
        log = None
        while not log or re.search("Label\\(s\\) may have changed. Rerun to get cross-references right.",log):
            p = subprocess.Popen(['latex','-interaction=nonstopmode','-halt-on-error',texFile],env=latexEnv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            log = p.communicate()[0]
            logging.info(log)

    if isNewer(dviFile,psFile):
        subprocess.Popen(['dvips','-o',psFile,dviFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT).communicate()

    if isNewer(psFile,pdfFile):
        subprocess.Popen(['ps2pdf',psFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT).communicate()

def execute(inputFile,outputFile):

    doc = "\n".join(file(inputFile))
    if not re.search(r'\\begin{document}',doc):
        logging.info("%s: skipping pdf generation - Detected LaTeX fragment file" % os.path.split(inputFile)[1])
        return

    (sourceDirectory,sourceFile) = os.path.split(inputFile)
    commonDirectory = os.path.join(sourceDirectory,"common")
    for fig in findFigures(inputFile):
        attemptFigureConversion(sourceDirectory,fig,"svg",svgToEps) or attemptFigureConversion(sourceDirectory,fig,"jpg",jpgToEps)
    compileLatex(inputFile)

    pdfFile = changeExtension(sourceFile,"pdf")
    copy(pdfFile,outputFile)


def main(argv):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("inputFile")
    parser.add_argument("outputFile")
    parser.add_argument("--workingDir",default=".")
    args = parser.parse_args()
    (inputFile,outputFile) = (os.path.abspath(args.inputFile),os.path.abspath(args.outputFile))
    os.chdir(args.workingDir)
    execute(inputFile,outputFile)


if __name__ == "__main__":
    main(sys.argv[1:])
