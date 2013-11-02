rutherford-content
==================

Python programs for doing conversions are in src/main/python

To convert tex to PDF use MakePDF.py
------------------------------------

    MakePDF.py [--workingDir WORKINGDIR] inputFile outputFile


The inputFile should be the name of the tex file to convert, the outputFile is the name of the PDF file you'd like to end up with.  workingDir if set will be the place where it puts all the temp files it needs (converted figures etc.).  If it finds the things it needs in workingDir then it doesn't recreate them (like make).


To convert tex to Soy use MakeSoy.py
------------------------------------

    MakeSoy.py [--workingDir WORKINGDIR] [--outputFigDir OUTPUTFIGDIR] inputFile outputFile

The inputfile should be the name of the tex file to convert, the outputFile is the name of the soy template.  Use outputFigDir to specify where you'd like the script to put the PNG images it makes.  



To convert all source use MakeWeb.py
------------------------------------

    MakeWeb.py [--workingDir WORKINGDIR] inputDir outputDir

This takes an inputDirectory and will convert all the tex it finds ready for the website.  This means it calls both MakeSoy and MakePDF.  It creates an output tree needed by the rutherford-server webapp - in outputDir you'll find 'static' and 'WEB-INF' - these can be just written in to the obvious place and everything should work e.g.

    ./MakeWeb.py ../resources/ /local/own/acr31/apache-tomcat-7.0.42/wtpwebapps/rutherford-server/ --workingDir=../../../target/working/
