#Importing packages
import os
import sys
path2addgeom = os.path.join(os.path.dirname(os.getcwd()),'geomeppy')
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)
from geomeppy import IDF, extractor
import esoreader
import matplotlib.pyplot as plt

keyPath = {'epluspath' : ''}
with open('Pathways.txt', 'r') as PathFile:
    Paths = PathFile.readlines()
    for line in Paths:
        for key in keyPath:
            if key in line:
                keyPath[key] = os.path.normcase(line[line.find(':')+1:-1])

    epluspath = keyPath['epluspath']

#selecting the E+ version and .idd file
IDF.setiddname(epluspath+"Energy+.idd")
#selecting the emty template file
idf = IDF(epluspath+"ExampleFiles/Minimal.idf")

ObjectName = open('Idf_Obj.txt','w')
for key in idf.idfobjects.keys():
    ObjectName.write(key+'\n')
ObjectName.close()


