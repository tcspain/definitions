#!/usr/bin/env python
from argparse import ArgumentError

########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################

'''
Extracts documentation from NXDL files and builds the NeXus manual page.

For an example of what the DocBook page provides, see
http://download.nexusformat.org/doc/html/ClassDefinitions-Base.html#NXentry
'''


import sys, os
import lxml.etree
import db2rst


class Describe:
    
    def __init__(self):
        self.nxdlFile = None
        self.nxdlType = None
        self.nxdlName = None
        self.fileSuffix = '.rst'
        self.ns = {'nx': 'http://definition.nexusformat.org/nxdl/3.1'}
    
    def parse(self, nxdlFile):
        self.nxdlFile = os.path.normpath( nxdlFile )
        
        stem, self.nxdlName = os.path.split(nxdlFile[:nxdlFile.find('.nxdl.xml')])
        self.nxdlType = os.path.split(stem)[1]
        
        self.tree = lxml.etree.parse(nxdlFile)
        pass
    
    def report(self, outputDir = '.'):
        rstFile = os.path.join(outputDir, self.nxdlType , self.nxdlName+ self.fileSuffix)
        path, _ = os.path.split(self.nxdlFile)
        
        root = self.tree.getroot()
        
        rest = self.make_heading(self.nxdlName, 1, self.nxdlName, True)

        rest += ".. index::  ! . NXDL %s; %s\n\n" % (self.nxdlType, self.nxdlName)
        rest += self.make_definition('category:', self.nxdlType)
        #N = ":index:`%s <single: ! %s; %s>`" % (self.nxdlName, self.nxdlType, self.nxdlName)
        URL = "http://svn.nexusformat.org/definitions/trunk/%s/%s.nxdl.xml" % (self.nxdlType, self.nxdlName)
        rest += self.make_definition('NXDL source:', "%s\n\n(%s)" % (self.nxdlName, URL) )
        rest += self.make_definition('version:', root.get('version', 'unknown') )
        rest += self.make_definition('SVN Id:', root.get('svnid', 'none') )
        extends = root.get('extends', 'none')
        if extends != "none":
            extends = ":ref:`%s`" % extends
        rest += self.make_definition('extends class:', extends )
        rest += self.make_definition('other classes included:', self.groups_list(root) )
        rest += self.make_definition('documentation:', self.get_doc(root, "No documentation provided.") )  # TODO: 

        rest += "\n"
        rest += ".. rubric:: Basic Structure of **%s**\n\n" % self.nxdlName
        # make the XSLT transformation, see: http://lxml.de/xpathxslt.html#xslt
        self.xsltFile = "nxdlformat.xsl"                        # could learn from the XML file?
        xsltFile = os.path.join(path, self.xsltFile)
        xslt = lxml.etree.XSLT( lxml.etree.parse(xsltFile) )    # prepare the transform
        text = ":linenos:\n\n"
        text += str( xslt( self.tree ) )                         # make the transform
        rest += ".. code-block:: text\n" + self.indented_lines(4, text)
        
        rest += self.symbols_table(root) + "\n\n"
        
        rest += "\n.. rubric:: Comprehensive Structure of **%s**\n\n" % self.nxdlName
        t = Table()
        t.labels = ('Name and Attributes', 'Type', 'Units', 'Description (and Occurrences)', )
        t.rows.append( ['class', 'NX_FLOAT', '..', '..', ] )
        rest += t.reST()
        
        '''
Table 3.3. NXaperture
Name and Attributes    Type    Units    Description (and Occurrences)
     NXgeometry          

location and shape of aperture
     NXgeometry          

location and shape of each blade
material     NX_CHAR         

Absorbing material of the aperture
description     NX_CHAR         

Description of aperture
     NXnote          

describe an additional information in a note*
        '''
        
        return rstFile, rest
    
    def make_heading(self, title, level, ref = None, upperBar = False):
        '''Return a formatted ReST heading
        
        :param str title: the text of the title
        :param int level: level number (1, 2, 3, 4, ...)
        :param str ref: (optional) text of the reference label
        :param bool upperBar: (optional) add an upper bar to the heading
        '''
        s = ""
        if ref is not None:
            s += "..  _%s:\n\n" % ref
        
        symbols = "# = - ~ ^ . * + _".split()
        if level < 1 or level > len(symbols):
            raise ArgumentError, "level must be between 1 and %d, received %d" % (len(symbols), level)
        
        bar = symbols[level-1]*len(title) + "\n"
        if upperBar:
            s += bar
        s += title + "\n" + bar + "\n"
        
        return s
    
    def make_definition(self, term, definition):
        '''Return a string-formatted ReST definition
        
        :param str term: the thing to be defined
        :param str definition: the words to describe the term
        '''
        s = term + "\n"
        s += self.indented_lines(4, definition)
        s += "\n"
        return s
    
    def indented_lines(self, numSpaces, lines):
        '''Return a string of indented lines from text with line breaks
        
        :param int numSpaces: number of spaces to indent
        :param str lines: text with embedded line breaks (assumes UNIX EOL - might be a problem)
        '''
        s = ""
        indent = " "*numSpaces
        for line in lines.split("\n"):
            s += "%s%s\n" % (indent, line)
        return s
    
    def groups_list(self, root):
        '''Return a string of ReST references to the groups used
        in this NXDL, sorted alphabetically
        
        :param root: root of XML tree
        '''
        groups = lxml.etree.ETXPath( './/{%s}group' % self.ns['nx'] )(root)
        if len(groups) > 0:
            L = []
            for G in groups:
                N = ":ref:`%s`" % G.get('type')
                if N not in L:
                    L.append( N )
            groups = ", ".join(sorted( L ))
        else:
            groups = "none"
        return groups
    
    def symbols_table(self, root):
        '''Return a table of ReST references to the symbols defined
        in this NXDL
        
        :param root: root of XML tree
        '''
        rest = "\n.. rubric:: Symbols used in definition of **%s**\n\n" % self.nxdlName
        symbols = "none"
        node = root.find( '{%s}symbols' % self.ns['nx'] )
        if node is None:
            rest += 'No symbols are defined in this NXDL file\n'
        else:
            table = Table()
            table.labels = ('Symbol', 'Description', )
            title = self.get_doc(node, None)
            if title is not None:
                rest += title + "\n"
            for SN in lxml.etree.ETXPath( './/{%s}symbol' % self.ns['nx'] )(node):
                symbol = "``%s``" % SN.get('name')
                desc = "%s" % self.get_doc(SN).strip('\n')
                table.rows.append( [symbol, desc] )
            rest += table.reST()
        return rest

    def get_doc(self, node, undefined = ""):
        DN = node.find( '{%s}doc' % self.ns['nx'] )
        if DN is None:
            doc = undefined
        else:
            # TODO: this could be much, much better
            ns = "http://definition.nexusformat.org/nxdl/3.1"
            obj = db2rst.Convert(DN, namespace=ns)
            doc = str(obj).strip() + "\n"
            #doc = DN.text
        return doc


class Table:
    ''' construct a table in reST '''
    
    def __init__(self):
        self.rows = []
        self.labels = []
    
    def reST(self, indentation = ''):
        '''return the table in reST format'''
        if len(self.rows) == 0:
            return ''
        
    
        width = []    # find the widths of all columns
        height = []   # find the height of all rows
        for label in self.labels:
            parts = label.split("\n")
            width.append( max( map(len, parts) ) )
            height.append( len(parts) )
        for row in self.rows:
            rowHeight = -1
            for i in range( len(row) ):
                parts = row[i].split("\n")
                w = max( map(len, parts) )
                width[i] = max(width[i], w)
                rowHeight = max( rowHeight, len(parts) )
            height.append( rowHeight )
        
        separator = '+'
        labelSep = '+'
        for w in width:
            separator += '-'*(w+2) + '+'
            labelSep += '='*(w+2) + '+'
        
        rest = '%s%s' % (indentation, separator)                                           # top line
        rest += self._reST_table_line(self.labels, height.pop(0), width, indentation)      # labels
        rest += '\n%s%s' % (indentation, labelSep)                                         # label separator line
        for row in self.rows:
            rest += self._reST_table_line(row, height.pop(0), width, indentation)          # table rows
            rest += '\n%s%s' % (indentation, separator)                                    # line below each table row
        return rest
    
    def _reST_table_line(self, items, height, width, indentation):
        '''
        return a single line of the reST table
        
        :param [str] items: table values
        :param int height: maximum number of rows this line takes (as determined by \n line breaks)
        :param [int] width: list of column widths
        :note: len(width) must be equal to len(items)
        '''
        if len(width) != len(width):
            raise RuntimeError, "len(width) != len(items)"
        line = ''
        for r in range(height):
            line += '\n%s|' % indentation
            for i in range( len(items) ):
                f = ' %%-%ds ' % width[i]
                line += f % items[i].split('\n')[r] + '|'
        return line


if __name__ == '__main__':
    
    
    NXDL_DIRS = ['../base_classes', '../applications', '../contributed_definitions', ]
    OUTPUT_DIR = os.path.join(*list('./source/volume2/NXDL'.split('/')))
    nxdl_file_list = []
    for dir in NXDL_DIRS:
        fulldir = os.path.abspath(dir)
        for _, dirs, files in os.walk(dir):
            if '.svn' in dirs:
                dirs.remove('.svn')
            for file in files:
                if file.endswith('.nxdl.xml'):
                    nxdlFile = os.path.join(fulldir, file)
                    nxdl_file_list.append(nxdlFile)
                    obj = Describe()
                     # TODO: add and handle optional argument of a namespace dictionary
                    obj.parse(nxdlFile)
                    rstFile, restText = obj.report(OUTPUT_DIR)
                    print rstFile
                    print restText
                    f = open (rstFile, 'w')
                    f.write(restText + "\n")
                    f.close()
    print len(nxdl_file_list), ' NXDL files discovered'