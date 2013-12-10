import sys
import os
from os import walk
from argparse import ArgumentParser
from pprint import pprint
import json
from pymongo import MongoClient

# This is copied from ExtractMetadata.py. Should be in utils.
def find_files(dir, ext):
    """Perform a recursive search of dir, and return 
a list of (directory, filename) tuples for all files
with the specified extension."""
    files = []
    for dirpath, dirnames, filenames in walk(dir):
        files.extend([(dirpath.replace(os.sep,"/"),f) for f in filenames if f.endswith(ext)])
    return files

def import_content_document(doc):
    if type(content['content']) is unicode:
        print "Importing %s/%s" % (path,name)
        content['contentLiteral'] = content.pop("content")
        client.rutherford.content.insert(content)

    elif type(content['content']) is list:
        content['contentReferenced'] = content.pop("content")
        client.rutherford.content.insert(content)

    elif type(content['content']) is dict:

        pass
    else:
        print "Skipping content %s in %s/%s." % (type(content['content']),path,name)

def main(argv):

    parser = ArgumentParser()
    parser.add_argument("--jsonDir")
    parser.add_argument("--mongo")

    args = parser.parse_args(argv)

    json_files = find_files(args.jsonDir, ".json")

    client = MongoClient(args.mongo)

    for (path,name) in json_files:
        with open(path + "/" + name) as j:
            content = json.load(j)
            if type(content['content']) is unicode:
                print "Importing %s/%s" % (path,name)
                content['contentLiteral'] = content.pop("content")
                client.rutherford.content.insert(content)

            elif type(content['content']) is list:
                content['contentReferenced'] = content.pop("content")
                client.rutherford.content.insert(content)

            elif type(content['content']) is dict:

                pass
            else:
                print "Skipping content %s in %s/%s." % (type(content['content']),path,name)

    print "Import complete. Press return to continue..."
    raw_input()

    

if __name__ == "__main__":
    main(sys.argv[1:])