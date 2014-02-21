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

#Vari value etc
class vari(Command):
    args = '{variable}'

class quantity(Command):
    args = '{amount}{units}' 

class valuedef(Command):
    args = '{variable}{amount}{units}'     

    # tex.ownerDocument.context.newcommand("vari",1,r'$#1$')
    # tex.ownerDocument.context.newcommand("quantity",2,r'${{#1\,}}$#2')
    # tex.ownerDocument.context.newcommand("valuedef",3,r'$#1{\,=#2\,}$#3')

# macros
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

def configureParser(latexSourceToConvert):
    latexSourceToConvert = "{%s}" % latexSourceToConvert

    tex = TeX()
    tex.input(latexSourceToConvert)
    tex.disableLogging()
    tex.ownerDocument.context.loadPackage(tex,"graphicx")
    tex.ownerDocument.context.loadPackage(tex,"wrapfig")
    tex.ownerDocument.context.loadPackage(tex,"amsmath")
    # tex.ownerDocument.context.newcommand("vtr",1,r'\mathit{\underline{\boldsymbol{#1}}}')
    # tex.ownerDocument.context.newcommand("vari",1,r'$#1$')
    # tex.ownerDocument.context.newcommand("quantity",2,r'${{#1\,}}$#2')
    # tex.ownerDocument.context.newcommand("valuedef",3,r'$#1{\,=#2\,}$#3')
    # tex.ownerDocument.context.newdef("half",'',r'\frac{1}{2}')
    # tex.ownerDocument.context.newdef("quarter",'',r'\frac{1}{4}')
    # tex.ownerDocument.context.newdef("third",'',r'\frac{1}{3}')
    # tex.ownerDocument.context.newdef("eigth",'',r'\frac{1}{8}')
    # tex.ownerDocument.context.newdef("e",'',r'{\textrm{e}}')
    # tex.ownerDocument.context.newdef("d",'',r'{\operatorname{d}\!}')
    tex.ownerDocument.context['Concepttitle'] = Concepttitle
    tex.ownerDocument.context['caption'] = caption
    tex.ownerDocument.context['color'] = color
    tex.ownerDocument.context['problem'] = problem
    tex.ownerDocument.context['label'] = label
    tex.ownerDocument.context['ref'] = ref
    tex.ownerDocument.context['qq'] = qq
    tex.ownerDocument.context['answer'] = answer

    tex.ownerDocument.context['vari'] = vari
    tex.ownerDocument.context['valuedef'] = valuedef
    tex.ownerDocument.context['quantity'] = quantity
    return tex

# This function will accept jsonMetaData array and some latex source and will attempt to convert the latex source (whether it is a fragment or not) and produce some html
def convertToHtml(jsonMetaData, latexSourceToConvert):
    meta = jsonMetaData
    inputFile = meta['src']

    # filter the source file because \nonumber commands break the parser
    latexSourceToConvert = re.sub(r'\\nonumber','',latexSourceToConvert)
    latexSourceToConvert = re.sub(r'\\%',r'#37;',latexSourceToConvert) # horrible find replace hack #1 because ampersands seemed to get consumed by a random (and unknown) part of the parser    
    latexSourceToConvert = re.sub(r'\\\& ',r'#amp# ',latexSourceToConvert) # horrible find replace hack #1 because ampersands seemed to get consumed by a random (and unknown) part of the parser
    latexSourceToConvert = re.sub(r'\[resume\]','',latexSourceToConvert)
    latexSourceToConvert = re.sub(u"\u2019", "'",latexSourceToConvert)
    latexSourceToConvert = re.sub(u"\u2018", "'",latexSourceToConvert)
    latexSourceToConvert = re.sub(u"\u201c", '"',latexSourceToConvert)
    latexSourceToConvert = re.sub(u"\u201d", '"',latexSourceToConvert)
    
    tex = configureParser(latexSourceToConvert)
    tex=tex.parse()
    
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

        if eq("#text"):
            result.append(escape(node.textContent))
        elif eq("section"):
            result.append("<h4>%s</h4>" % text("title"))
        elif eq("subsection"):
            result.append("<h5>%s</h5>" % text("title"))            
        elif eq("Concepttitle"):
            result.append("<h3>%s</h3>" % text("text"))
            terminal = True
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
        elif eq("par"):
            result.append("<p>")
        elif eq("wrapfigure"):
            result.append('<figure>')
        elif eq("includegraphics"):
            latexFigurePath = os.path.join(os.path.split(os.path.abspath(inputFile))[0],changeExtension(node.getAttribute("file"),"png"))
            #remove absolute path information
            htmlFigurePath = os.path.abspath(latexFigurePath.replace(os.path.split(os.path.abspath(inputFile))[0],''))[1:]    
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
        elif eq("enumerate"):
            result.append("<ol>")
        elif eq("itemize"):
            result.append("<ul>")
        elif eq("item"):
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
        elif eq("vari"):
            result.append("$\\vari{%s}$" % node.getAttribute("variable").textContent)
            pass
        elif eq("valuedef"):
            variable = ("" if node.getAttribute("variable") == None else node.getAttribute("variable").textContent)
            amount = ("" if node.getAttribute("amount") == None else node.getAttribute("amount").textContent)
            units = ("" if node.getAttribute("units") == None else node.getAttribute("units").textContent)

            result.append("$\\valuedef{%s}{%s}{%s}$" % (variable,amount, units))
            pass
        elif eq("quantity"):
            variable = ("" if node.getAttribute("variable") == None else node.getAttribute("variable").textContent)
            amount = ("" if node.getAttribute("amount") == None else node.getAttribute("amount").textContent)
            units = ("" if node.getAttribute("units") == None else node.getAttribute("units").textContent)

            result.append("$\\quantity{%s}{%s}$" % (amount, units))
            pass

        # TODO: This logic should only be in the extract structure part of the process
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

        if eq("par"):
            result.append("</p>")
        elif eq("wrapfigure"):
            result.append("</figure>")
        elif eq("enumerate"):
            result.append("</ol>")
        elif eq("eqnarray") or eq("equation*"):
            result.append("</table>")
        elif eq("ArrayRow"):
            result.append("</tr>")
        elif eq("itemize"):
            result.append("</ul>")
        elif eq("nl"):
            result.append("<br/>")
        # remove any whitespace-only elements
        result = filter(lambda x:x.strip()!='',result)

        # strip out empty pairs of <p></p>
        if len(result) > 1 and result[-1] == "</p>" and result[-2] == "<p>":
            result = result[:-2]

        if latexSourceToConvert == result:
            return latexSourceToConvert

        return u'\n'.join(result)

    doc = render(tex,True).encode('UTF-8','ignore')

    return doc