#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import logging

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

#used for numeric questions
class answer(Command):
    args = '{units}{value}'      

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
    source = re.sub(r'\\%',r'#37;',source) # horrible find replace hack #1 because ampersands seemed to get consumed by a random (and unknown) part of the parser    
    source = re.sub(r'\\\& ',r'#amp# ',source) # horrible find replace hack #1 because ampersands seemed to get consumed by a random (and unknown) part of the parser
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
    tex.ownerDocument.context['answer'] = answer
    
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
            # The following are required for html encoding as python 2.7 doesn't do it for me.
            text = re.sub(r'#amp#','&amp;', text) # horrible find replace hack #2 puts the correct html encoded value in now as it doesn't get removed after this point.
            text = re.sub(u'\u2019','&apos;', text)
            text = re.sub(u'\u2014','&mdash;', text)
            text = re.sub(u'\u2013','&ndash;', text)
            text = re.sub(r'\'','&apos;', text)
            text = re.sub(r'#37;','&#37;', text) # horrible find replace hack #3 puts the correct html encoded value in now as it doesn't get removed after this point this is for % signs

            if escapeBraces:
                text = re.sub(r'\{',"{lb}",text)
                text = re.sub(r'(?<!\{lb)\}',"{rb}",text)
                #text.decode('latin9').encode('utf8')     
            return text

        def eq(string):
            return node.nodeName == string

        #logging.warning(node.nodeName)
        #result.append(node.nodeName)
        
        bgroupCount = 0
        # question stuff 
        if isQuestion:
            if eq("#document"):                
                for n in node.childNodes:
                    
                    if(n.nodeName == "bgroup"):
                        if bgroupCount == 0:
                            for questionText in n.childNodes:
                                result.append("<p>" + render(questionText,escapeBraces) + '</p>')
                        elif bgroupCount == 1:
                            result.append('{call shared.questions.questionFooter}{param footer}%s{/param}{/call}' % n.textContent)
                            terminal = True      
                        elif bgroupCount == 2 and not (meta['QUESTIONTYPE'] == 'numeric' or meta['QUESTIONTYPE'] == 'symbolic'):
                            result.append('{call shared.questions.questionExplanation}{param explanation}%s{/param}{/call}' % render(n,escapeBraces))
                        bgroupCount+=1

            # questionText and options
            # This will need fixing as currently it will affect any enumerate whether it is an options list or not
            if meta['QUESTIONTYPE'] == 'scq' or meta['QUESTIONTYPE'] == 'mcq':
                if node.nodeName == "enumerate":
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
                        result.append('[\'desc\': \'%s\'%s]]/}}\n{/call}' % (render(body,False).replace('\\','\\\\').replace('{{','{ {').replace('}}','} }'),answer))
                    terminal = True
            # Hack to get numeric and symbolic questions displaying properly and omitting the answer for now
            # TODO allow numeric questions to accept answers
            elif meta['QUESTIONTYPE'] == 'numeric' or meta['QUESTIONTYPE'] == 'symbolic': 
                if node.nodeName == 'answer':
                    logging.debug("Found %s Question %s - Omitting answer: %s %s" % (meta['QUESTIONTYPE'],meta['ID'],text('value'),text('units')))
                    terminal = True
                elif eq("enumerate"):
                    result.append('<ol>')
                    for enumerate_items in node.childNodes:
                        result.append(render(enumerate_items, escapeBraces))
                        terminal = True
                    result.append('</ol>')
                elif eq("item"):
                    result.append("<li>")
                    for enumerate_items in node.childNodes:
                        result.append('%s' % render(enumerate_items, escapeBraces))
                        terminal = True
                    result.append("</li>")
                    terminal = True
        if eq("#text"):
            result.append(escape(node.textContent))
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
                result.append('<figcaption id="#%s">Figure %s: %s</figcaption>' % (figureLabel,figureNumber,render(node.getAttribute("self"),escapeBraces)))
            else:
                result.append('<figcaption>%s</figcaption>' % render(node.getAttribute("self"),escapeBraces))                
            terminal = True
        elif eq("label"):
            if text("label") not in figureMap.keys():
                figureNumber = len(figureMap.keys())
                figureMap[text("label")] = figureNumber
        elif eq("ref"):
            if text("ref") in figureMap:
                result.append(str(figureMap[text("ref")]))
            else:
                figureNumber = len(figureMap.keys()) + 1
                figureMap[text("ref")] = figureNumber
                logging.debug("Forward referencing of a figure - generating a figure number and adding to the map")
                result.append(str(figureMap[text("ref")]))
        elif eq("enumerate") and not isQuestion:
            result.append("<ol>")
        elif eq("itemize") and not isQuestion:
            result.append("<ul>")
        elif eq("item") and not isQuestion:
            itemContent = ""

            # sometimes they number their list manually. This horrible
            # hack looks up the numbering assigned (attr) and slips it
            # inside the content generated by the children if possible
            text = render(node.childNodes[0],escapeBraces)
            attr = node.getAttribute("term")
            if attr:
                attr = attr.textContent
                if text[0:3] == "<p>":
                    text = "<p class=\"item-number\">%s" % (attr)
                    itemContent+=text

            if len(node.childNodes) > 0:
                for enumerate_items in node.childNodes:
                    itemContent+='%s' % render(enumerate_items, escapeBraces)

            result.append("<li>%s</li>" % itemContent)
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
            # first check if there is something in the attribute that we can use as the answer
            answerNode = node.getAttribute("answer")
            # if not then lets try and find something that could be the answer - horrible hack necessary when LaTeX is structured differently
            if answerNode == None:
                answerNode = findNode(node.parentNode, "bgroup")
                logging.debug("Had to guess at which node is the answer node in quick question: %s" % text("question"))

            if answerNode != None:
                result.append('<div class="quick-question"><div class="question"><p>%s</p></div><div class="answer hidden"><p>%s</p></div></div>' % (render(node.getAttribute("question"),escapeBraces),render(answerNode,escapeBraces)))
            else:
                logging.warning('Unable to locate answer node for quick question with text: %s' % text("question"))
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
        elif eq("eqnarray") or eq("equation*"):
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
    soy.write("/**\n Autogenerated template - generated from %s - DO NOT EDIT\n*/\n" % os.path.split(inputFile)[1])
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
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

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
