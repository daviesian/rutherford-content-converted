import sys
import os
from os import walk
from argparse import ArgumentParser
from pprint import pprint
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests

# This is copied from ExtractMetadata.py. Should be in utils.
def find_files(dir, ext):
    """Perform a recursive search of dir, and return 
a list of (directory, filename) tuples for all files
with the specified extension."""
    files = []
    for dirpath, dirnames, filenames in walk(dir):
        files.extend([(dirpath.replace(os.sep,"/"),f) for f in filenames if f.endswith(ext)])
    return files

def warn(msg):
    print "WARNING: %s" % msg
    print "Press return to continue..."
    raw_input()


def save_doc(doc):
    r = requests.post("http://localhost:8080/rutherford-server/api/content/save", {"doc": json.dumps(doc)})
    if r.status_code == 200:
        _id = r.json()['newId']
        return _id
    else:
        warn("Error from SAVE: %s" % r.json()["error"])
        return None


def import_content_document(mongo, doc):
    _id = None

    if type(doc['content']) is unicode:
        print "\t(literal content)"
        doc['contentLiteral'] = doc.pop("content")

        _id = save_doc(doc);
        print "\tCreated object %s" % _id

    elif type(doc['content']) is list:
        print "\t(content list)"

        doc['contentReferenced'] = []
        lst = doc.pop("content")
        for c in lst:
            if type(c) is unicode:
                print "\t\tReferencing %s" % c
                doc['contentReferenced'].append(c)
                pass
            elif type(c) is dict:
                print "\t\tRecursively importing literal content object."
                subId = import_content_document(mongo,c)

                if not c.has_key("id"):
                    # Add the db _id as our id.
                    c['_id'] = subId
                    c['id'] = str(subId) 
                    save_doc(c)

                print "\t\tReferencing %s" % str(subId)
                # Add the new id to our list of referenced content
                doc['contentReferenced'].append(str(subId))
                pass
            else:
                warn("Unknown content type in list: %s" % type(c))
                
        
        #doc['contentReferenced'] = 
        _id = save_doc(doc)

    else:
        warn("\t(Skipping content %s)" % type(doc['content']))

    return _id

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
            print "Importing %s/%s" % (path, name)
            import_content_document(client, content)

    print "Import complete. Press return to continue..."
    raw_input()

    

if __name__ == "__main__":
    main(sys.argv[1:])