import re
import os
import shutil
import subprocess
import logging

def changeExtension(f,newExtension):
    return re.sub("(.*)\..*","\\1.%s" % newExtension,f)

def isNewer(f1,f2):
    f1m = os.path.getmtime(f1) if os.path.exists(f1) else 0
    f2m = os.path.getmtime(f2) if os.path.exists(f2) else 0
    return f1m >= f2m

def attemptFigureConversion(sourceDirectory, filename,extension,conversionFn):
    sourceFile = os.path.join(sourceDirectory,changeExtension(filename,extension))
    logging.info("SourceDir %s" % sourceDirectory)
    logging.info("filename %s" % filename)

    if os.path.exists(sourceFile):
        if isNewer(sourceFile,filename):
            logging.debug('New figure source file detected. Converting %s' % filename)
            ensureDirectory(filename)
            conversionFn(sourceFile,filename)
        else:
            logging.debug('Skipping image file (%s) as it has not changed since last time it was generated.' % filename)
        return True
    logging.warning('Figure does not exist. Unable to locate %s' % sourceFile)
    return False

def svgToEps(sourceFile,destinationFile):
    p = subprocess.Popen(['inkscape','-D','-z','-P',destinationFile,sourceFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.communicate()

def jpgToEps(sourceFile,destinationFile):
    p = subprocess.Popen(['convert',sourceFile,destinationFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.communicate()  

def svgToPng(sourceFile,destinationFile):
    p = subprocess.Popen(['inkscape','-D','-z','-e',destinationFile,sourceFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.communicate()

def jpgToPng(sourceFile,destinationFile):
    p = subprocess.Popen(['convert',sourceFile,destinationFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.communicate()    

"""
Takes a filename and makes sure that the directory exists
"""
def ensureDirectory(f):
    dirName = os.path.split(f)[0]
    if not os.path.exists(dirName):
        os.makedirs(dirName)

def copy(sourceFile,destinationFile):
    if os.path.abspath(sourceFile) != os.path.abspath(destinationFile) and isNewer(sourceFile,destinationFile):
        ensureDirectory(destinationFile)
        shutil.copyfile(sourceFile,destinationFile)
