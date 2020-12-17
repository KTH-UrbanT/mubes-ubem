import sys
import os

path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)

#add needed packages
import pygeoj
import CoreFiles.GeomScripts as GeomScripts
import CoreFiles.Set_Outputs as Set_Outputs
import CoreFiles.Sim_param as Sim_param
import CoreFiles.Load_and_occupancy as Load_and_occupancy
import pickle
import time
from DataBase.DB_Building import DB_Build
from geomeppy import IDF
import os

start = time.time()
MainPath = os.getcwd()
#e+ parameters
epluspath = 'C:\\EnergyPlusV9-1-0\\'
#selecting the E+ version and .idd file
IDF.setiddname(epluspath+"Energy+.idd")
#district / building input files (from main database)
loadedfile = 'C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\Minneberg_Sweref99TM\\Buildings.geojson'
Buildingsfile = pygeoj.load(loadedfile)
loadedfile = 'C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\Minneberg_Sweref99TM\\Walls.geojson'
Shadingsfile = pygeoj.load(loadedfile)

SimDir = os.path.join(os.getcwd(),'CaseFiles')
if not os.path.exists(SimDir):
    os.mkdir(SimDir)
os.chdir(SimDir)

Res = {}
for nbcase in range(len(Buildingsfile)):
    if nbcase==7:
        print('Building ', nbcase, '/', len(Buildingsfile), 'process starts')
        CaseName = 'run'
        # erasing all older file from previous simulation if present
        for file in os.listdir():
            if CaseName in file[0:len(CaseName)]:
                #print('Removing', file, ' from folder')
                os.remove(file)

        # selecting the emty template file
        idf = IDF(epluspath + "ExampleFiles\\Minimal.idf")
        # location and weather definition
        Sim_param.Location_and_weather(idf)
        #Changes in the simulation parameters
        Sim_param.setSimparam(idf)

        #Geometry related modification
        #creatin of an instance of building class with the available data in the dataBase
        building = DB_Build('Building'+str(nbcase),Buildingsfile,Shadingsfile,nbcase,MainPath)
        end = time.time()
        print('First step time : '+str(end-start))
        if not building.height:
            print('Building ',nbcase,' stop, Not enough data to proceed')

        else:
            idf.idfname = building.name #'Building '+ str(nbcase)
            start = time.time()
            GeomScripts.createBuilding(idf,building, perim = False)
            end = time.time()
            print('createBuilding time : ' + str(end - start))

            #idf.view_model(test=False)
            start = time.time()
            #control command related equipment, loads and leaks for each zones
            Load_and_occupancy.CreateZoneLoadAndCtrl(idf,building)

            #ouputs definitions
            Set_Outputs.AddOutputs(idf)
            end = time.time()
            print('Ctrl, load & outputs step time : ' + str(end - start))

            #saving files launching the simulation
            #idf.to_obj('Building'+str(nbcase)+'.obj')
            start = time.time()
            idf.saveas('Building_'+str(nbcase)+'.idf')

            with open('Building_'+str(nbcase)+'.pickle', 'wb') as handle:
                pickle.dump(building, handle, protocol=pickle.HIGHEST_PROTOCOL)
        #the current building object is removed
        del building, idf

#removong the path to the local package of eppy and geomeppy
#sys.path.remove(path2addeppy)
sys.path.remove(path2addgeom)


