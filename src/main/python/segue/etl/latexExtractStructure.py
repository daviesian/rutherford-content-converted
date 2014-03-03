#!/usr/bin/python

import sys
import os
import re
import subprocess
import argparse
import shutil
import logging
import simplejson, json
from pprint import pprint

import string
from plasTeX.Renderers import Renderer
from plasTeX.TeX import TeX
from plasTeX import Command,Environment
from plasTeX.Packages import wrapfig

from Util import *
from latexConvert import *

class qq(Command):
    args = '{question}{answer}' 

class Concepttitle(Command):
    args = '{text}'

#Had to add so that the parser knows to expect n number of arguments.
class valuedef(Command):
    args = '{first}{second}{third}'

class vari(Command):
    args = '{first}'

class quantity(Command):
    args = '{first}{second}'

#used for questions
class hinta(Command):
    args = '[questionid]{hintText}'

class exposition(Command):
    args = '{expositionText}'

class question(Command):
    args = '[questionid]{questionText}'

class answer(Command):
    args = '[questionid]{answerText}'

class choice(Command):
    args = '[choiceid]{answerText}'

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

def configureParser(texInput):
    tex = TeX()
    tex.input(texInput)
    tex.disableLogging()
    tex.ownerDocument.context.loadPackage(tex,"graphicx")
    tex.ownerDocument.context.loadPackage(tex,"wrapfig")
    tex.ownerDocument.context.loadPackage(tex,"amsmath")
    tex.ownerDocument.context['qq'] = qq
    tex.ownerDocument.context['question'] = question
    tex.ownerDocument.context['answer'] = answer
    tex.ownerDocument.context['choice'] = choice
    tex.ownerDocument.context['exposition'] = exposition
    tex.ownerDocument.context['hinta'] = hinta
    tex.ownerDocument.context['valuedef'] = valuedef
    tex.ownerDocument.context['vari'] = vari
    tex.ownerDocument.context['quantity'] = quantity
    tex.ownerDocument.context['Concepttitle'] = Concepttitle   

    tex.ownerDocument.context.newdef("half",'',r'\frac{1}{2}')
    tex.ownerDocument.context.newdef("quarter",'',r'\frac{1}{4}')
    tex.ownerDocument.context.newdef("third",'',r'\frac{1}{3}')
    tex.ownerDocument.context.newdef("eigth",'',r'\frac{1}{8}')
    return tex

'''
Merge syntax example:
{
  "src": "a_toboggan.tex", 
  ...
  "overrides":[{
    "qid" : 0,
    "type" :"scq",
    "choices" : {
        "b" : {
          "correct" : true,
          "content" : "is constant",
          "encoding" : "html"
        }
      }
  }]
}
'''
# This function should take the important parts of the json metadata to merge them with the now extracted structure
def mergeStructure(jsonMetaData,structuredOutput):
    if jsonMetaData.get('overrides'):
        # we need to try and augment the structured output we have with the data already in the jsonMetaData object
        for overrideItem in jsonMetaData.get('overrides'):
            # find the question we are interested in.
            question = findQuestionInStructuredOutput(overrideItem.get('qid'), structuredOutput)

            if overrideItem.get('type') == 'scq':
                if overrideItem.get('choices'):
                    for key, choice in overrideItem.get('choices').iteritems():
                        if question.get('choices').get(key):
                            question.get('choices').get(key).update(choice)
                        else:
                            question['choices'][key] = choice
                    question['type'] = "choiceQuestion"

        # remove override key from structured output because we should have finished with it by now
        del jsonMetaData['overrides']

    # flatten choices data structure so that it is a list of choices rather than a map. After this point we can no longer use the merge syntax defined in the comments.
    for content in structuredOutput:
        if content.get('questionid') != None and content.get('choices') != None:
            convertChoiceMapToList(content)

    return structuredOutput

def findQuestionInStructuredOutput(questionid, structuredOutput):
    for question in structuredOutput:
        if("questionid" in question and question['questionid'] == questionid):
            return question

    return None

def convertChoiceMapToList(questionWithChoices):
    newChoiceList = list()
    for choice in questionWithChoices['choices'].itervalues():
        newChoiceList.append(choice)
    
    questionWithChoices['choices'] = newChoiceList
    return questionWithChoices


# This function will accept jsonMetaData array and some latex source and will attempt to extract a structure which is has some more semantic meaning.
def extractStructure(jsonMetaData, latexSourceToConvert):
    meta = jsonMetaData
    inputFile = meta['src']

    structuredOutput = list()

    leftbr = latexSourceToConvert.count("{")
    rightbr = latexSourceToConvert.count("}")
    if ((leftbr+rightbr) % 2) == 1:
        logging.warning("Odd number of brackets {} (%s) detected in %s. This could be an indicator of a problem or maybe just commented out latex." % (leftbr+rightbr,jsonMetaData['src']))

    # filter the source file because \nonumber commands break the parser
    latexSourceToConvert = re.sub(r'\\nonumber','',latexSourceToConvert)

    tex = configureParser(latexSourceToConvert)
    extractStructure.questionNum = 0
    tex=tex.parse()

    def render(node,escapeBraces):
        result = []
        terminal = False

        def text(attr):
            result = node.getAttribute(attr)
            if result:
                return escape(result.textContent)
            return ""


        def isNode(node,name):
            if node.nodeName == name:
                return True
            for child in node.childNodes:
                if isNode(child,name):
                    return True
            return False            

        def extractLatex(node):
            if node != None:
                return "{%s}" % node.source

        def eq(string):
            return node.nodeName == string
        
        def findLastContentNode():
            for content in structuredOutput[::-1]:
                if content['type'] == "content":
                    return content
            return None

        def findLastQuestionNode():
            for question in structuredOutput[::-1]:   
                if "questionid" in question:
                    return question
            return None

        # Utility function that will use findQuestionInStructuredOutput or findLastQuestion as a last resort to try and locate a question of interest
        def questionFinder(questionid=None):
            question = None
            if questionid != None: 
                question = findQuestionInStructuredOutput(questionid, structuredOutput)
            
            if question == None:
                # assume that it is the last question we saw
                question = findLastQuestionNode()

            if question == None:
                logging.debug("Unable to find question using question finder.")

            return question

        if eq("question"):

            '''
            intermediate json structure 
            {
                encoding: LaTeX
                content: "some latex content"
                questionid: x
                type: question
                answers:{}
                
            }
            '''

            standardQuestionObject = dict()
            if node.getAttribute("questionid") != None: 
                standardQuestionObject['questionid'] = node.getAttribute("questionid").textContent
            else:
                standardQuestionObject['questionid'] = extractStructure.questionNum
            extractStructure.questionNum+=1

            standardQuestionObject['value'] = extractLatex(node.getAttribute("questionText"))
            standardQuestionObject['encoding'] = 'latex'
            standardQuestionObject['type'] = 'question'
            structuredOutput.append(standardQuestionObject)
        
        elif eq("answer"):
            '''
            Assumption that if not declared in the [questionid] that the answer refers to the last seen question in the file.
            intermediate json structure 
            {
                encoding: LaTeX
                content: "some latex content"
                type: content

            }
            '''
            question = None

            if node.getAttribute("questionid") != None: 
                question = questionFinder(node.getAttribute("questionid").textContent)
            else:
                question = questionFinder()

            if question == None or node.getAttribute("answerText") == None:
                logging.warning("%s - Malformed answer detected or unable to find associated question - skipping answer" % jsonMetaData['id'])
            else:
                if('answer' not in question):
                    question['answer'] = dict()
                question['answer']['encoding'] = "latex"
                question['answer']['value'] = extractLatex(node.getAttribute("answerText"))
                question['answer']['type'] = "content"

        elif eq("choice"):
            '''
            Assumption that the choice will always refer to last seen question in structuredOutput
            intermediate json structure 
            choiceid : {
                encoding: LaTeX
                content: "some latex content"
                type: choice
            }
            '''
            question = findLastQuestionNode()
            choiceid = node.getAttribute("choiceid").textContent
            # first choice item for this question so we need to setup the dictionary
            if('choices' not in question):
                question['choices'] = dict()

            question['choices'][choiceid]=dict()
            question['choices'][choiceid]['encoding'] = "latex"
            question['choices'][choiceid]['type'] = "choice"
            question['choices'][choiceid]['value'] = extractLatex(node.getAttribute("answerText"))

            if(node.nextSibling.nodeName == 'correct'):
                question['choices'][choiceid]['correct'] = True

            # mark question as being a question with options
            question['type'] = "choiceQuestion"

        elif eq("exposition"):
            '''
            intermediate json structure 
            {
                encoding: LaTeX
                content: "some latex content"
            }
            '''
            standardQuestionObject = dict()
            if node.getAttribute("expositionText") != None: 
                standardQuestionObject['value'] = extractLatex(node.getAttribute("expositionText"))
                standardQuestionObject['encoding'] = 'latex'
                standardQuestionObject['type'] = 'content'
                structuredOutput.append(standardQuestionObject)
            else:
                logging.warning("%s - exposition declared but no text provided." % jsonMetaData['id'])
        
        elif eq("hinta"):
            '''
            Assumption that if not declared in the [questionid] that the answer refers to the last seen question in the file.
            intermediate json structure 
            {
                encoding: LaTeX
                content: "some latex content"
                layout: "question-hint"
                type: content

            }
            '''
            question = None
            if node.getAttribute("questionid") != None: 
                question = questionFinder(node.getAttribute("questionid").textContent)
            else:
                question = questionFinder()

            if question == None or node.getAttribute("hintText") == None:
                logging.warning("%s - Malformed hint detected or unable to find associated question - skipping hint" % jsonMetaData['id'])
            else:
                if('hints' not in question):
                    question['hints'] = []
                hint = dict()
                hint['encoding'] = "latex"
                hint['type'] = "content"
                hint['value'] = extractLatex(node.getAttribute("hintText"))
                question['hints'].append(hint)

        # horrible thing added to try and extract the attribution
        elif 'question' in jsonMetaData['type'] and eq("#document"):
            bgroupCount = 0
            for n in node.childNodes:
                if(n.nodeName == "bgroup"):
                    if bgroupCount == 1:
                        jsonMetaData['attribution'] = n.textContent
                    bgroupCount+=1

        elif jsonMetaData['type'] == 'concept':
            # we need to do a bit more work to extract structure
            # for each section we will create a new content object with a list of content (probably just one) but this is to cope with quick questions
            '''
            intermediate json structure for concepts
            {
                encoding: LaTeX
                content: [{
                    encoding:latex,
                    content: "concept section information",
                    type:"content"
                },
                {
                    encoding:latex,
                    content: "",
                    answer:{},
                    type:"quick-question"
                }]
                type: concept                
            }
            '''

            if eq("section"):
                conceptObject = dict()
                conceptObject['encoding'] = "latex"
                conceptObject['type'] = "content"
                conceptObject['value'] = "%s" % node.attributes['title'].textContent
                structuredOutput.append(conceptObject)
                terminal = True

                for child in node.childNodes:
                    render(child, True)

            elif eq("subsection") or eq("subsection*"):
                conceptObject = dict()
                conceptObject['encoding'] = "latex"
                conceptObject['type'] = "content"
                conceptObject['value'] = "%s" % node.attributes['title'].textContent
                structuredOutput.append(conceptObject)
                terminal = True

                for child in node.childNodes:
                    render(child, True)
            elif eq("par"):
                terminal = True
                for fragment in node.childNodes:
                    render(fragment, True)

            elif eq("includegraphics"):
                terminal = True
                figureObject = dict()
                figureObject['encoding'] = "latex"
                figureObject['type'] = "image"
                latexFigurePath = changeExtension(node.getAttribute("file"),"svg")
                figureObject['src'] = os.path.basename(latexFigurePath)
                label = findNode(node.parentNode, "label")
                caption = findNode(node.parentNode, "caption")
                if label != None:
                    figureObject['id'] = label.getAttribute("label")

                if caption != None:
                    figureObject['value'] = caption.getAttribute("self").source
                structuredOutput.append(figureObject)

            elif eq("equation") or eq("equation*") or eq("eqnarray"):
                terminal = True
                equationObject = dict()
                equationObject['encoding'] = "latex"
                equationObject['type'] = "content"
                equationObject['value'] = node.source
                structuredOutput.append(equationObject)

            elif eq("qq"):
                terminal = True
                answerNode = node.getAttribute("answer")
                # if not then lets try and find something that could be the answer - horrible hack necessary when LaTeX is structured differently
                if answerNode == None:
                    answerNode = findNode(node.parentNode, "bgroup")
                    logging.debug("Had to guess at which node is the answer node in quick question: %s" % text("question"))

                if answerNode != None:
                    quickQuestion = dict()
                    quickQuestion['encoding'] = "latex"
                    quickQuestion['type'] = "question"
                    quickQuestion['value'] = node.getAttribute("question").source
                    quickQuestion['answer'] = {"value":node.getAttribute("answer").source, "type" : "content", "encoding":"latex"} 
                    structuredOutput.append(quickQuestion)
                else:
                    logging.warning('Unable to locate answer node for quick question with text: %s' % text("question"))
            # things to ignore and not to recursively look through as we have already dealt with them
            elif eq("caption") or eq("label") or eq("item") or eq("bf") or eq("addtolength") or eq("pagebreak"):
                terminal = True
                pass
            # things to ignore but we still want to explore their children.
            elif eq("#document") or eq("input") or eq("document") or eq("wrapfigure") or eq("center") or eq("centering") or eq("figure") or eq("vspace") or eq("setlength"):
                pass
            else:
                if len(structuredOutput) > 0 and structuredOutput[-1]['type'] == 'content':
                    structuredOutput[-1]['value'] = "%s %s" % (structuredOutput[-1]['value'], node.source.strip())

                else:
                    conceptObject = dict()
                    conceptObject['encoding'] = "latex"
                    conceptObject['type'] = "content"
                    conceptObject['value'] = node.source.strip()

                    if conceptObject['value'] != "": #len(conceptObject['content']) > 0:
                        structuredOutput.append(conceptObject)
                pass
        else:
            pass

        if not terminal:
            for child in node.childNodes:
                result.append(render(child,escapeBraces))

        # remove any whitespace-only elements
        result = filter(lambda x:x.strip()!='',result)

        return u'\n'.join(result)

    doc = render(tex,True).encode('UTF-8','ignore')

    if len(structuredOutput) == 0:
        logging.warning("%s - No content extracted for this file." % jsonMetaData['id'])
    else:
        logging.debug("Extraction complete.")
        # here we need to run the merge operation which should use any overrides specified in the json metadata.
        structuredOutput = mergeStructure(jsonMetaData, structuredOutput)

    return structuredOutput