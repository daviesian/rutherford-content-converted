#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil

import string
from plasTeX.Renderers import Renderer
from plasTeX.TeX import TeX
from plasTeX import Command,Environment
from plasTeX.Packages import wrapfig

from Util import *

class Concepttitle(Command):
    args = 'text'

class caption(Command):
    args = 'self'  

class color(Command):
    args = '{color} [text]'

class problem(Command):
    args = '{problem} [id]'      

def findFigures(texFile):
    for line in file(texFile):
        m = re.search(r'^[^%]*\\includegraphics.*?\{(.*?)\}',line)
        if m:
            yield m.group(1)

def svgToPng(sourceFile,destinationFile):
    p = subprocess.Popen(['inkscape','-D','-z','-e',destinationFile,sourceFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.communicate()

def jpgToPng(sourceFile,destinationFile):
    p = subprocess.Popen(['convert',sourceFile,destinationFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.communicate()

def attemptFigureConversion(sourceDirectory, filename,extension,conversionFn):
    sourceFile = os.path.join(sourceDirectory,changeExtension(filename,extension))
    if os.path.exists(sourceFile):
        if isNewer(sourceFile,filename):
            ensureDirectory(filename)
            conversionFn(sourceFile,filename)
        return True
    return False


def convertToSoy(inputFile,outputFile,outputFigDir):
    (sourceDirectory,sourceFile) = os.path.split(inputFile)
    commonDirectory = os.path.join(sourceDirectory,"common")

    if isNewer(inputFile,outputFile):
        ensureDirectory(outputFile)
    
    meta = {}
    for line in file(inputFile):
        m = re.match("%% ([A-Z]+): (.*)",line.strip())
        if m:
            meta[m.group(1)] = m.group(2)

    # filter the source file because \nonumber commands break the parser
    source = '\n'.join(file(inputFile))
    source = re.sub(r'\\nonumber','',source)
    output = file("filtered.tex","w")
    output.write(source)
    output.flush()

    tex = TeX(file="filtered.tex")
    tex.disableLogging()
    tex.ownerDocument.context.loadPackage(tex,"graphicx")
    tex.ownerDocument.context.loadPackage(tex,"wrapfig")
    tex.ownerDocument.context.loadPackage(tex,"amsmath")
    tex.ownerDocument.context.newcommand("vtr",1,r'\mathit{\underline{\boldsymbol{#1}}}')
    tex.ownerDocument.context.newdef("half",'',r'\frac{1}{2}')
    tex.ownerDocument.context.newdef("quarter",'',r'\frac{1}{4}')
    tex.ownerDocument.context.newdef("third",'',r'\frac{1}{3}')
    tex.ownerDocument.context.newdef("eigth",'',r'\frac{1}{8}')
    tex.ownerDocument.context.newdef("e",'',r'{\textrm{e}}')
    tex.ownerDocument.context.newdef("d",'',r'{\operatorname{d}\!}')
    tex.ownerDocument.context['Concepttitle'] = Concepttitle
    tex.ownerDocument.context['caption'] = caption
    tex.ownerDocument.context['color'] = color
    tex.ownerDocument.context['problem'] = problem
    
    tex=tex.parse()

    isQuestion = False
    if(None != meta['TYPE'] and meta['TYPE'].lower() == "question"):
        # Use question logic if different
        isQuestion = True
        # expecting a problem with 4 bgroups
        

    def render(node):
        result = []
        terminal = False

        def text(attr):
            result = node.getAttribute(attr)
            if result:
                return escape(result.textContent)
            return ""

        def escape(text):
            text = re.sub(r'\{',"{lb}",text)
            text = re.sub(r'(?<!\{lb)\}',"{rb}",text)
            return text

        def eq(string):
            return node.nodeName == string

        #result.append(node.nodeName)
        bgroupCount = 0
        # question stuff tested with sample file A1988PIQ7l.tex
        if isQuestion:
            if eq("#document"):                
                for n in node.childNodes:
                    
                    if(n.nodeName == "bgroup"):
                        if bgroupCount == 0:
                            for questionText in n.childNodes:
                                result.append(render(questionText))
                        elif bgroupCount == 1:
                            result.append('{call .questionFooter}{param footer}%s{/param}{/call}' % n.textContent)
                            terminal = True      
                        elif bgroupCount == 2:
                            result.append('{call .questionExplanation}{param explanation}%s{/param}{/call}' % n.textContent)
                        bgroupCount+=1

            # questionText and options
            # This will need fixing as currently it will affect any enumerate whether it is an options list or not
            if node.nodeName == "enumerate": 
                result.append('{call %s}\n{param type: \'checkbox\' /}\n{param choices: [' % meta['QUESTIONTYPE'])  
            elif node.nodeName == "item":
                if node.nextSibling != None:
                    result.append('[\'desc\': \'%s\'],' % node.textContent.strip(' '))
                else:
                    result.append('[\'desc\': \'%s\']]/}\n{/call}' % node.textContent.strip(' '))                      
                terminal = True

        if eq("#text"):
            result.append(node.textContent)
        elif eq("section"):
            result.append("<h4>%s</h4>" % text("title"))
        elif eq("subsection"):
            result.append("<h5>%s</h5>" % text("title"))
        elif eq("Concepttitle"):
            result.append("<h3>%s</h3>" % text("text"))
        elif eq("math"):
            result.append(escape(node.source))
            terminal = True
        elif eq("equation"):
            result.append("$$")
            result.append(escape(node.childrenSource))
            result.append("$$")
            terminal = True
        elif eq("par") and not isQuestion:
            result.append("<p>")
        elif eq("wrapfigure"):
            result.append('<div class="figure">')
        elif eq("includegraphics"):
            filename = os.path.join("static","figures",os.path.split(changeExtension(node.getAttribute("file"),"png"))[1])        
            result.append('<img src="{$ij.proxyPath}/%s"/>' % filename)
        elif eq("caption"):
            result.append('<div class="caption">%s</div>' % text("self"))
            terminal = True
        elif eq("enumerate") and not isQuestion:
            result.append("<ol>")
        elif eq("itemize") and not isQuestion:
            result.append("<ul>")
        elif eq("item") and not isQuestion:
            # sometimes they number their list manually. This horrible
            # hack looks up the numbering assigned (attr) and slips it
            # inside the content generated by the children if possible
            text = render(node.childNodes[0])
            attr = node.getAttribute("term")
            if attr:
                attr = attr.textContent
                if text[0:3] == "<p>":
                    text = "<p>%s %s" % (attr,text[3:])
                else:
                    text = attr +" " + text
            result.append("<li>%s</li>" % text)
            terminal = True
        elif eq("eqnarray") or eq("equation*"):
            result.append("<table>")
        elif eq("ArrayRow"):
            result.append("<tr>")
        elif eq("ArrayCell"):
            result.append("<td>%s</td>" % escape(node.source))
            terminal = True
        elif eq("color"):
            # this one is especially horrible.  There seems to be a
            # practice of \color{red}[SOMETHING]\color{black} however
            # sometimes SOMETHING has line breaks in it and so only
            # half of it is captured as text on the color node
            # therefore open the span on color != red and close it
            # again on color = black and hope they never forget to
            # apply this pattern
            color = text("color")
            body = node.getAttribute("text")
            if body:
                body = render(body)
            else:
                body = ""
            if color != "black":
                result.append('<span class="color-%s">%s' % (color,body))
            else:
                result.append('</span>')            
        else:
            pass

        if not terminal:
            for child in node.childNodes:
                result.append(render(child))

        if eq("par") and not isQuestion:
            result.append("</p>")
        elif eq("wrapfigure"):
            result.append("</div>")
        elif eq("enumerate") and not isQuestion:
            result.append("</ol>")
        elif eq("eqnarray") or eq("equation*") and not isQuestion:
            result.append("</table>")
        elif eq("ArrayRow"):
            result.append("</tr>")
        elif eq("itemize") and not isQuestion:
            result.append("</ul>")

        # remove any whitespace-only elements
        result = filter(lambda x:x.strip()!='',result)

        # strip out empty pairs of <p></p>
        if len(result) > 1 and result[-1] == "</p>" and result[-2] == "<p>":
            result = result[:-2]

        return u'\n'.join(result)

    doc = render(tex).encode('UTF-8','ignore')

    soy = file(outputFile,"w")
    soy.write("{namespace rutherford.content}\n")
    soy.write("/**\n Autogenerated template - DO NOT EDIT\n*/\n")
    soy.write("{template .%s}\n" % meta["ID"])
    soy.write(doc+"\n")
    soy.write("{/template}\n")

def execute(inputFile,outputFile,outputFigDir):
    (sourceDirectory,sourceFile) = os.path.split(inputFile)
    commonDirectory = os.path.join(sourceDirectory,"common")
    for fig in findFigures(inputFile):
        fig = changeExtension(fig,"png")
        attemptFigureConversion(sourceDirectory,fig,"svg",svgToPng) or \
            attemptFigureConversion(sourceDirectory,fig,"jpg",jpgToPng) 
        figFilename = os.path.join(outputFigDir,os.path.split(fig)[1])
        copy(fig,figFilename)

    convertToSoy(inputFile,outputFile,outputFigDir)

def main(argv):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("inputFile")
    parser.add_argument("outputFile")
    parser.add_argument("--workingDir",default=".")
    parser.add_argument("--outputFigDir",default=".")
    args = parser.parse_args()
    (inputFile,outputFile,outputFigDir) = map(os.path.abspath,(args.inputFile,args.outputFile,args.outputFigDir))
    os.chdir(args.workingDir)
    execute(inputFile,outputFile,outputFigDir)


if __name__ == "__main__":
    main(sys.argv[1:])
