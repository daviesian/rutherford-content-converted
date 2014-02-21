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

def findFigures(texFile):
    for line in file(texFile):
        m = re.search(r'^[^%]*\\includegraphics.*?\{(.*?)\}',line)
        if m:
            yield m.group(1)

# This function assumes that the current os working directory has been set as all figures will be dumped here.
def attemptFigureConversion(sourceDirectory,filename,extension,conversionFn):
    sourceFile = os.path.join(sourceDirectory,changeExtension(filename,extension))

    if os.path.exists(sourceFile):
        if isNewer(sourceFile,filename):
            logging.info('New figure source file detected. Converting %s using %s' % (filename,conversionFn.__name__))
            ensureDirectory(os.path.abspath(filename))
            conversionFn(sourceFile,filename)
        else:
            logging.info('Skipping image file (%s) as it has not changed since last time it was generated.' % filename)
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
        logging.info("Directory %s does not exist. Creating it..." % dirName)
        os.makedirs(dirName)

def copy(sourceFile,destinationFile):
    if os.path.abspath(sourceFile) != os.path.abspath(destinationFile) and isNewer(sourceFile,destinationFile):
        ensureDirectory(destinationFile)
        logging.info("Copying file %s to %s" % (sourceFile,destinationFile))
        shutil.copyfile(sourceFile,destinationFile)
