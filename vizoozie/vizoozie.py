#!/usr/bin/env python
import getopt, sys, re, os
from xml.dom.minidom import parseString
from os.path import isfile, isdir
from os import listdir
from subprocess import call

VERSION='0.1'

def sText(text):
    return text.replace('-', '_')       

class VizOozie(object):
    
    properties = {}
    
    def loadProperties(self):
        with open("vizoozie/vizoozie.properties") as f:
            for line in f:
                key, val = line.split('=')
                self.properties[key] = val
    
    def getName(self, node):
        attr = self.getAttribute(node, "name")
        return attr
    
    def getTo(self, node):
        attr = self.getAttribute(node, "to")
        return attr
    
    def getAttribute(self, node, attributeName):
        attr = node.getAttribute(attributeName)
        return attr
    
    def getOK(self, node):
        ok = node.getElementsByTagName("ok")[0]
        return ok
    
    def getError(self, node):
        return node.getElementsByTagName("error")[0]

    def getOKTo(self, node):
        return self.getTo(self.getOK(node))

    def getErrorTo(self, node):
        return self.getTo(self.getError(node))
    
    def processHeader(self, name):
        output = "digraph{\nsize = \"8,8\";ratio=fill;node[fontsize=24];labelloc=\"t\";label=\"" + name + "\";\nsubgraph{\n"
        return output

    def processStart(self, doc):
        output = ''
        start = doc.getElementsByTagName("start")[0]
        to = self.getTo(start)
        output = '\n' + "start -> " + to.replace('-', '_') + ";\n"
        return output

    def getFirstElementChildNode(self, node):
        for aNode in node.childNodes:
            if aNode.nodeType == aNode.ELEMENT_NODE:
                return aNode
        return None     

    def processAction(self, doc):
        output = ''
        for node in doc.getElementsByTagName("action"):
            name = self.getName(node)
            action_node = self.getFirstElementChildNode(node)
            color = "white"
            for key, value in self.properties.iteritems():
                if len(node.getElementsByTagName(key)) != 0:
                    color = value
                    break 
            if action_node.tagName == "sub-workflow":
                url = self.getFirstElementChildNode(action_node).childNodes[0].data
                url = url.replace("${subworkflowPath}", "")
                url = re.sub('.xml$', '.svg', url)
                output += '\n'+sText(name) + " [URL=\""+url+"\",shape=box,style=filled,color=" + color + "];\n"
            else:
                output += '\n'+sText(name) + " [shape=box,style=filled,color=" + color + "];\n"
            output += '\n'+sText(name) + " -> " + sText(self.getOKTo(node)) + ";\n"
            output += '\n'+sText(name) + " -> " + sText(self.getErrorTo(node)) + "[style=dotted,fontsize=10];\n"
        return output
    
    def processFork(self, doc):
        output = ''
        for node in doc.getElementsByTagName("fork"):
            name = self.getName(node)
            output += '\n' + name.replace('-', '_') + " [shape=octagon];\n"
            for path in node.getElementsByTagName("path"):
                start = path.getAttribute("start")
                output += '\n' + name.replace('-', '_') + " -> " + start.replace('-', '_') + ";\n"
        return output


    def processJoin(self, doc):
        output = ''
        for node in doc.getElementsByTagName("join"):
            name = self.getName(node)
            to = self.getTo(node)
            output += '\n' + name.replace('-', '_') + " [shape=octagon];\n"
            output += '\n' + name.replace('-', '_') + " -> " + to.replace('-', '_') + ";\n"
        return output


    def processDecision(self, doc):
        output = ''
        for node in doc.getElementsByTagName("decision"):
            name = self.getName(node)
            switch = node.getElementsByTagName("switch")[0]
            output += '\n' + name.replace('-', '_') + " [shape=diamond];\n"
            for case in switch.getElementsByTagName("case"):
                to = case.getAttribute("to")
                caseValue = case.childNodes[0].nodeValue.replace('"', '')
                output += '\n' + name.replace('-', '_') + " -> " + to.replace('-', '_') + "[style=bold,fontsize=20];\n"
            
            default = switch.getElementsByTagName("default")[0]
            to = default.getAttribute("to")
            output += '\n' + name.replace('-', '_') + " -> " + to.replace('-', '_') + "[style=dotted,fontsize=20];\n"
        return output


    def processCloseTag(self):
        output = '\n' + "}"+'\n' + "}"
        return output


    def convertWorkflowXMLToDOT(self, input_str, name):
        self.loadProperties()
        doc = parseString(input_str)

        if doc.getElementsByTagName("workflow-app").length == 0 : return None

        output = self.processHeader(name)
        output += self.processStart(doc)
        output += self.processAction(doc)
        output += self.processFork(doc)
        output += self.processJoin(doc)
        output += self.processDecision(doc)
        output += self.processCloseTag()
        return output

    def processWorkflow(self, in_file, out_file, relative_name):
        inputFile = open(in_file, 'r')    
        input_str = inputFile.read()
        output = self.convertWorkflowXMLToDOT(input_str, relative_name)
        if output == None : return
        out_file_dirname = os.path.dirname(out_file)
        if not os.path.exists(out_file_dirname):
            os.makedirs(out_file_dirname)
        outputFile = open(out_file, 'w+')
        outputFile.write(str(output))
        outputFile.close()
        call(["dot", "-Tsvg", out_file, "-o", os.path.splitext(out_file)[0] + ".svg"])
    
def main():
    vizoozie = VizOozie()
    if len(sys.argv) < 3:
        print("Usage: python vizoozie.py <Input Oozie workflow xml file name> <output dot file name>")
        exit(1)
    if isfile(sys.argv[1]) :
        vizoozie.processWorkflow(sys.argv[1], sys.argv[2])
    elif isdir(sys.argv[1]):
        in_base_dir = os.path.realpath(sys.argv[1])
        out_base_dir = os.path.realpath(sys.argv[2])
        for root, dirs, files in os.walk(sys.argv[1]):
            for file in files:
                if file.endswith(".xml"):
                    in_file = os.path.realpath(os.path.join(root,file))
                    out_file = os.path.splitext(in_file.replace(in_base_dir, out_base_dir))[0] + ".dot"
                    vizoozie.processWorkflow(in_file, out_file, in_file.replace(in_base_dir, ""))
    
if __name__ == "__main__":
    main()