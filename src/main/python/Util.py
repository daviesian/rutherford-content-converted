import re
import os
import shutil

def changeExtension(f,newExtension):
    return re.sub("(.*)\..*","\\1.%s" % newExtension,f)

def isNewer(f1,f2):
    f1m = os.path.getmtime(f1) if os.path.exists(f1) else 0
    f2m = os.path.getmtime(f2) if os.path.exists(f2) else 0
    return f1m >= f2m

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
