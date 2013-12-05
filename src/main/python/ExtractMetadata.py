import sys
import os
from os import walk
from argparse import ArgumentParser
from pprint import pprint
import re
import json

def find_files(dir, ext):
    files = []
    for dirpath, dirnames, filenames in walk(dir):
        files.extend([(dirpath.replace(os.sep,"/"),f) for f in filenames if f.endswith(ext)])
    return files

def parse_metadata(lines):

    line_metadata = {}
    for line in lines:
        match = re.match("%% (?P<key>[A-Z]*): (?P<val>.*)", line)
        if match:
            m = match.groupdict()

            if m["val"].strip() != "":
                key = m["key"]
                vals = m["val"].split(",")

                if len(vals) == 1:
                    line_metadata[key] = vals[0]
                else:
                    line_metadata[key] = [v.strip() for v in vals]


    return line_metadata

def update_metadata(metadata, path, tex_file):

    path_parts = path.split("src/main/resources/")
    new_m = {"id": metadata["ID"],
             "src": path_parts[1] + "/" + tex_file,
             "layout": "1-col",
             "encoding": "latex"}
  
    new_m["attribution"] = None
    new_m["related_content"] = []

    new_m["author"] = metadata["AUTHOR"] if metadata.has_key("AUTHOR") else None
    new_m["title"] = metadata["TITLE"] if metadata.has_key("TITLE") else None

    if metadata.has_key("CONCEPTS"):
        if type(metadata["CONCEPTS"]) is list:
            new_m["related_content"].extend(metadata["CONCEPTS"])
        else:
            new_m["related_content"].append(metadata["CONCEPTS"])

    if metadata.has_key("VIDEOS"):
        if type(metadata["VIDEOS"]) is list:
            new_m["related_content"].extend([v.replace(".mp4","_video").replace(".mov","_video") for v in metadata["VIDEOS"]])
        else:
            new_m["related_content"].append(metadata["VIDEOS"].replace(".mp4","_video").replace(".mov","_video"))

    if metadata["TYPE"] == "maths" or metadata["TYPE"] == "physics":
        new_m["type"] = "concept"
        
    elif metadata["TYPE"] == "question":
        new_m["type"] = "legacy_latex_question"
        
    else:
        raise "Unknown content type"


    return new_m

def extract_metadata(path, tex_file, remove_from_tex=False):
    print "Extracting metadata from %s/%s" % (path,tex_file)

    infile = open(path + "/" + tex_file, "r")

    first_line = infile.readline()
    if first_line.startswith("%% ID:"):
        # This file has metadata that we're interested in.

        metadata_lines = [first_line]

        # Keep reading lines until we get one that isn't metadata, discarding empty lines
        line = infile.readline()
        while line.startswith("%% ") or line.strip() == "":
            if line.strip() != "":
                metadata_lines.append(line)
            line = infile.readline()

        # Read the rest of the file. This is the content
        content_lines = [line]
        content_lines.extend(infile.readlines())

        infile.close()

        # Write metadata to sidecar file
        metadata = parse_metadata(metadata_lines)
        new_metadata = update_metadata(metadata, path, tex_file)

        with open(path + "/" + tex_file.replace(".tex", ".json"), "w") as metadata_file:
            metadata_file.write(json.dumps(new_metadata, indent=2))
            #metadata_file.writelines(metadata_lines)

        if remove_from_tex:
            # Replace input file with just content_lines
            with open(path + "/" + tex_file, "w") as orig_file:
                orig_file.writelines(content_lines)

    else:
        infile.close()

def main(argv):

    parser = ArgumentParser()
    parser.add_argument("input_dir")

    args = parser.parse_args(argv)

    print "Searching for .tex files in %s" % args.input_dir

    tex_files = find_files(args.input_dir, ".tex")

    for (path, name) in tex_files:
        extract_metadata(path,name, remove_from_tex=False)
    

if __name__ == "__main__":
    main(sys.argv[1:])