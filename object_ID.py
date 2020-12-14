#Importing packages
from geomeppy import IDF, extractor
import esoreader
import matplotlib.pyplot as plt

epluspath = '//usr//local//'

#selecting the E+ version and .idd file
IDF.setiddname(epluspath+"Energy+.idd")
#selecting the emty template file
idf = IDF(epluspath+"ExampleFiles/Minimal.idf")

ObjectName = open('Idf_Obj.txt','w')
for key in idf.idfobjects.keys():
    ObjectName.write(key+'\n')
ObjectName.close()


