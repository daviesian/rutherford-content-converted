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

class label(Command):
    args = '{label}'      

class ref(Command):
    args = '{ref}'      

class qq(Command):
    args = '{question}{answer}'

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


def isNode(node,name):
    if node.nodeName == name:
        return True
    for child in node.childNodes:
        if isNode(child,name):
            return True
    return False

def findNode(node,name):
    if node.nodeName == name:
        return node

    if node.nextSibling != None:
        searchResult = findNode(node.nextSibling, name)
        if searchResult != None:
            return searchResult

    for child in node.childNodes:
        searchResult = findNode(child, name)
        if searchResult != None:
            return searchResult

    return None

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
    tex.ownerDocument.context['label'] = label
    tex.ownerDocument.context['ref'] = ref
    tex.ownerDocument.context['qq'] = qq

    tex=tex.parse()

    isQuestion = False
    if(None != meta['TYPE'] and meta['TYPE'].lower() == "question"):
        # Use question logic if different
        isQuestion = True
        # expecting a problem with 4 bgroups
    
    figureMap = dict()

    def render(node,escapeBraces):
        result = []
        terminal = False

        def text(attr):
            result = node.getAttribute(attr)
            if result:
                return escape(result.textContent)
            return ""

        def escape(text):
            if escapeBraces:
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
                                result.append(render(questionText,escapeBraces))
                        elif bgroupCount == 1:
                            result.append('{call shared.questions.questionFooter}{param footer}%s{/param}{/call}' % n.textContent)
                            terminal = True      
                        elif bgroupCount == 2:
                            result.append('{call shared.questions.questionExplanation}{param explanation}%s{/param}{/call}' % n.textContent)
                        bgroupCount+=1

            # questionText and options
            # This will need fixing as currently it will affect any enumerate whether it is an options list or not
            if node.nodeName == "enumerate" and (meta['QUESTIONTYPE'] == 'scq' or meta['QUESTIONTYPE'] == 'mcq'): 
                paramType = "checkbox"
                questionType = meta['QUESTIONTYPE']
                if questionType == 'scq':
                    paramType = 'radio'
                    questionType = 'mcq'
                elif questionType == 'mcq':
                    paramType = 'checkbox'

                result.append('{call shared.questions.%s}\n{param type: \'%s\' /}\n{{param choices: [' % (questionType,paramType))  
            elif node.nodeName == "item" and (meta['QUESTIONTYPE'] == 'scq' or meta['QUESTIONTYPE'] == 'mcq'):
                body = node.childNodes[0]
                answer = ",'ans':true" if isNode(node,"answer") else ""
                if node.nextSibling is not None:
                    result.append('[\'desc\': \'%s\'%s],' % (render(body,False).replace('\\','\\\\').replace('{{','{ {').replace('}}','} }'),answer))
                else:
                    result.append('[\'desc\': \'%s\'%s]]/}}\n{/call}' % (render(body,False),answer))
                terminal = True
            elif meta['QUESTIONTYPE'] == 'numeric':
                pass
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
            figureNode = findNode(node, "label")
            if figureNode is not None:
                figureLabel = figureNode.getAttribute("label").textContent
                figureNumber = ''
                if figureLabel in figureMap.keys():
                    figureNumber = figureMap[figureLabel]
                else:
                    figureNumber = len(figureMap.keys()) + 1
                    figureMap[figureLabel] = figureNumber

                equationOutput = '<div id="%s">$$ %s $$</div>' % (figureLabel,escape(node.childrenSource))
            else:
                equationOutput = '<div>$$ %s $$</div>' % escape(node.childrenSource)

            result.append(equationOutput)

            terminal = True
        elif eq("par") and not isQuestion:
            result.append("<p>")
        elif eq("wrapfigure"):
            result.append('<figure>')
        elif eq("includegraphics"):
            filename = os.path.join("static","figures",os.path.split(changeExtension(node.getAttribute("file"),"png"))[1])        
            result.append('<img src="{$ij.proxyPath}/%s"/>' % filename)
        elif eq("caption"):
            figureNode = findNode(node, "label")
            if figureNode is not None:
                figureLabel = figureNode.getAttribute("label").textContent
                figureNumber = ''
                if figureLabel in figureMap.keys():
                    figureNumber = figureMap[figureLabel]
                else:
                    figureNumber = len(figureMap.keys()) + 1
                    figureMap[figureLabel] = figureNumber
                result.append('<figcaption id="#%s">Figure %s: %s</figcaption>' % (figureLabel,figureNumber,text("self")))
            else:
                result.append('<figcaption>%s</figcaption>' % text("self"))                
            terminal = True
        elif eq("label"):
            if text("label") not in figureMap.keys():
                figureNumber = len(figureMap.keys())
                figureMap[text("label")] = figureNumber
        elif eq("ref"):
            if text("ref") in figureMap:
                result.append(str(figureMap[text("ref")]))
            else:
                figureNumber = len(figureMap.keys())
                figureMap[text("ref")] = figureNumber
                #result.append("###ERROR - REFERENCE NOT FOUND###")
        elif eq("enumerate") and not isQuestion:
            result.append("<ol>")
        elif eq("itemize") and not isQuestion:
            result.append("<ul>")
        elif eq("item") and not isQuestion:
            # sometimes they number their list manually. This horrible
            # hack looks up the numbering assigned (attr) and slips it
            # inside the content generated by the children if possible
            text = render(node.childNodes[0],escapeBraces)
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
                body = render(body,escapeBraces)
            else:
                body = ""
            if color != "black":
                result.append('<span class="color-%s">%s' % (color,body))
            else:
                result.append('</span>')            
        elif eq("qq"):
            answerNode = findNode(node.parentNode, "bgroup")
            if answerNode == None:
               answerNode = node.getAttribute("answer")

            if answerNode != None:
               result.append('<div class="quick-question"><div class="question">%s</div><div class="answer hidden">%s</div></div>' % (text("question"),answerNode.textContent))
            #print findNode(node.parentNode,"bgroup")
        else:
            pass

        if not terminal:
            for child in node.childNodes:
                result.append(render(child,escapeBraces))

        if eq("par") and not isQuestion:
            result.append("</p>")
        elif eq("wrapfigure"):
            result.append("</figure>")
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

    doc = render(tex,True).encode('UTF-8','ignore')

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
