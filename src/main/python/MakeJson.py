#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import logging
import simplejson, json

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

def textDefault(self, node):
    return node.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


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

def convertToHtml(inputFile,inputDir,outputDir,jsonMetaData):
    (sourceDirectory,sourceFile) = os.path.split(inputFile)
    commonDirectory = os.path.join(sourceDirectory,"common")

    # this is the returned data structure that gets merged with the metadata one
    jsonOutput = dict()

    meta = jsonMetaData

    # filter the source file because \nonumber commands break the parser
    source = '\n'.join(file(inputFile))
    source = re.sub(r'\\nonumber','',source)
    source = re.sub(r'\\\&',r'#amp#',source) # horrible find replace hack #1 because ampersands seemed to get consumed by a random (and unknown) part of the parser
    output = file("filtered.tex","w")
    output.write(source)
    output.flush()

    tex = TeX(file="filtered.tex")
    tex.disableLogging()
    tex.ownerDocument.context.loadPackage(tex,"graphicx")
    tex.ownerDocument.context.loadPackage(tex,"wrapfig")
    tex.ownerDocument.context.loadPackage(tex,"amsmath")
    tex.ownerDocument.context.newcommand("vtr",1,r'\mathit{\underline{\boldsymbol{#1}}}')
    tex.ownerDocument.context.newcommand("vari",1,r'$#1$')
    tex.ownerDocument.context.newcommand("quantity",2,r'${{#1\,}}$#2')
    tex.ownerDocument.context.newcommand("valuedef",3,r'$#1{\,=#2\,}$#3')
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
    if(None != meta['type'] and (meta['type'].lower() == "question") or 'legacy_latex_question' in meta['type']):
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
            return text

        def eq(string):
            return node.nodeName == string

        #checks to see if the current node is the document node. If it is, we shall try and build a simple map containing both the questionText, questionNode, explanation and attribution
        def extractCommonQuestionMap():
            rawQuestionMap = dict()
            if eq("#document"):
                bgroupCount = 0
                for n in node.childNodes:
                    if(n.nodeName == "bgroup"):
                        if bgroupCount == 0:
                            questionContent = ""
                            for questionText in n.childNodes:
                                questionContent+=("<p>" + render(questionText,escapeBraces) + '</p>')
                            rawQuestionMap['questionText'] = questionContent
                            rawQuestionMap['rawQuestionNode'] = n
                            terminal = True
                        elif bgroupCount == 1:
                            rawQuestionMap['attribution'] = n.textContent
                            terminal = True
                        elif bgroupCount == 2:
                            rawQuestionMap['explanation'] = render(n, False)
                            terminal = True
                        bgroupCount+=1
                return rawQuestionMap


        def extractMcqObjects(questionNode,correctAnswerExplanation):
            mcqObject = None

            # Build mcq object which will hold all possible choices
            if questionNode.nodeName == "enumerate":
                mcqObject = dict()
                mcqChoicesList = list()
                for item in questionNode.childNodes:
                    mcqChoicesList.append(extractMcqObjects(item, correctAnswerExplanation))
                mcqObject['content'] = mcqChoicesList
                mcqObject['type']='mcq'
                mcqObject['layout']="random_order"
            # build choices objects
            elif questionNode.nodeName == "item":
                mcqChoice = dict()
                body = questionNode.childNodes[0]
                answer = True if isNode(questionNode,"answer") else False

                mcqChoice['type']='choice'
                mcqChoice['content']=render(body,False)
                mcqChoice['correct']=answer
                if answer:
                    mcqChoice['explanation'] = correctAnswerExplanation
                return mcqChoice
            # if we have children then we should search through them to see if we can find the enumerate node
            elif len(questionNode.childNodes) > 0:
                for child in questionNode.childNodes:
                    output = extractMcqObjects(child, correctAnswerExplanation)
                    if output != None:
                        mcqObject = output
            # if we do not have children then stop.
            elif questionNode.childNodes == None or len(questionNode.childNodes) <=0:
                return None

            return mcqObject

        #logging.warning(node.nodeName)
        
        bgroupCount = 0
        # question stuff 
        if isQuestion:
            if eq("#document"):
                rawQuestionMap = extractCommonQuestionMap()

                questionContentList = list()
                questionContentDataStructure = dict()
                questionContentDataStructure['encoding'] = "html"
                questionContentDataStructure['content'] = rawQuestionMap['questionText']
                questionContentList.append(questionContentDataStructure)

                if(meta['type'] == 'legacy_latex_question_scq'):
                    questionContentList.append(extractMcqObjects(rawQuestionMap['rawQuestionNode'],rawQuestionMap['explanation']))

                jsonOutput['attribution']=rawQuestionMap['attribution']

                result.append(json.dumps(questionContentList))
                # needed to stop double output
                for n in node.childNodes:                    
                    if(n.nodeName == "bgroup"):

                        if bgroupCount == 0:
                            pass
                        elif bgroupCount == 1:
                            pass
                            terminal = True
                        elif bgroupCount == 2:
                            pass
                        bgroupCount+=1

            # questionText and options
            # This will need fixing as currently it will affect any enumerate whether it is an options list or not
            if meta['type'] == 'legacy_latex_question_scq' or meta['type'] == 'legacy_latex_question_mcq':
                # This is legacy and pending removal
                if node.nodeName == "enumerate":
                    pass 
                elif node.nodeName == "item" and (meta['type'] == 'legacy_latex_question_scq' or meta['type'] == 'legacy_latex_question_mcq'):                
                    terminal = True
            # Hack to get numeric and symbolic questions displaying properly and omitting the answer for now
            elif meta['type'] == 'legacy_latex_question_numeric' or meta['type'] == 'legacy_latex_question_symbolic': 
                if node.nodeName == 'answer':
                    logging.warning("Found %s Question %s - Omitting answer: %s %s" % (meta['type'],meta['id'],text('value'),text('units')))
                    terminal = True
                elif eq("enumerate"):
                    result.append('<ol>')
                    for enumerate_items in node.childNodes:
                        result.append(render(enumerate_items, escapeBraces))
                        terminal = True
                    result.append('</ol>')
                elif eq("item"):
                    for enumerate_items in node.childNodes:
                        result.append('<li>%s</li>' % render(enumerate_items, escapeBraces))
                        terminal = True
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
            latexFigurePath = os.path.join(os.path.split(os.path.abspath(inputFile))[0],changeExtension(node.getAttribute("file"),"png"))
            #remove absolute path information
            htmlFigurePath = os.path.abspath(latexFigurePath.replace(os.path.abspath(inputDir),''))[1:]    
            result.append('<img src="%s"/>' % htmlFigurePath)
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
    
    jsonOutput['content'] = doc
    
    # check to see if the content is actually a string and convert it - horrible hack due to the way I have to pass a string back after each recursive call.
    if "\"content\":" in jsonOutput['content']:
        #print jsonOutput['content']
        jsonOutput['content'] = json.loads(jsonOutput['content'])
    return jsonOutput
    

def execute(inputFile,inputDir,outputDir):
    (sourceDirectory,sourceFile) = os.path.split(inputFile)
    commonDirectory = os.path.join(sourceDirectory,"common")

    jsonMetaData = buildOutlineJson(inputFile)

    texFile = os.path.join(os.path.split(os.path.abspath(inputFile))[0],jsonMetaData['src'])

    for fig in findFigures(texFile):
        fig = changeExtension(fig,"png")
        figureLocationDirectory = os.path.abspath(os.path.join(sourceDirectory,os.path.split(fig)[0]))

        attemptFigureConversion(figureLocationDirectory,os.path.split(fig)[1],"svg",svgToPng) or \
            attemptFigureConversion(figureLocationDirectory,os.path.split(fig)[1],"jpg",jpgToPng) 
        
        figureSourceLocation = os.path.abspath(os.path.join(os.path.split(os.path.abspath(texFile))[0],fig))
        figureDestination = figureSourceLocation.replace(os.path.abspath(inputDir),os.path.abspath(outputDir))

        copy(os.path.split(fig)[1],figureDestination)

    convertedHtml = convertToHtml(texFile,inputDir,outputDir,jsonMetaData)

    del jsonMetaData['src']

    jsonMetaData['encoding'] = "html"

    # combine metadata file with the one generated by the initial import script
    jsonMetaData.update(convertedHtml)

    newJsonFile = os.path.join(outputDir,"json",jsonMetaData['id']+'.json')

    if isNewer(inputFile,newJsonFile):
        ensureDirectory(newJsonFile)

    with open(newJsonFile, 'w') as outfile:
        json.dump(jsonMetaData, outfile, indent=1)

def buildOutlineJson(inputFile):
    # read json meta data to find tex file
    fileHandle = open(inputFile)
    data = json.load(fileHandle)

    return data

def main(argv):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("inputFile")
    parser.add_argument("inputDir")
    parser.add_argument("outputFile")
    parser.add_argument("outputDir")
    parser.add_argument("--workingDir",default=".")
    parser.add_argument("--outputFigDir",default=".")
    args = parser.parse_args()
    (inputFile,outputFile,l) = map(os.path.abspath,(args.inputFile,args.outputFile,args.inputDir,args.outputDir))
    os.chdir(args.workingDir)
    execute(inputFile,inputDir,outputDir)


if __name__ == "__main__":
    main(sys.argv[1:])
