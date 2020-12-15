import sys
import os

path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)

#add needed packages
import pygeoj
import GeomScripts
import Set_Outputs
import Sim_param
import Load_and_occupancy
import csv2tabdelim
import shutil
import pickle
import time
from DB_Building import DB_Build
from geomeppy import IDF
import os

start = time.time()

#e+ parameters
epluspath = 'C:\\EnergyPlusV9-1-0\\'
#selecting the E+ version and .idd file
IDF.setiddname(epluspath+"Energy+.idd")

#district / building input files (from main database)
loadedfile = 'C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\Minneberg_Sweref99TM\\Buildings.geojson'
Buildingsfile = pygeoj.load(loadedfile)
loadedfile = 'C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\Minneberg_Sweref99TM\\Walls.geojson'
Shadingsfile = pygeoj.load(loadedfile)

SimDir = os.path.join(os.getcwd(),'Sim_Results')
if not os.path.exists(SimDir):
    os.mkdir(SimDir)
os.chdir('Sim_Results')

Res = {}
for nbcase in range(len(Buildingsfile)):
    if nbcase<10:
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
        building = DB_Build('Building'+str(nbcase),Buildingsfile,Shadingsfile,nbcase)
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
            idf.saveas('Building'+str(nbcase)+'.idf')

            #the readvars option enable to create a csv file with all the specified ouputs
            #but as for many zones, this can lead to heavy files, worakourand are proposed in the Set_Outputs file. see below
            #idf.run(readvars=True, output_prefix=CaseName)
            idf.run(output_prefix=CaseName, verbose='q')
            end = time.time()
            print('Run step time : ' + str(end - start))

            #ouputs readings
            #if ZoneOutputs=True, results are aggregated at storey level, if False, results are aggregated into heated and non heated zones
            start = time.time()
            ResEso = Set_Outputs.Read_OutputsEso(CaseName,ZoneOutput=False)
            end = time.time()
            print('Read ESO step time : ' + str(end - start))

            #plots option, for debug purposes
            letsplot = False
            if letsplot:
                Set_Outputs.Plot_Outputs(ResEso, idf)

            #read the html file. this options might be cancelled because resultats can be computed form ResEso file
            #it is currently sued for debuging to check, integral of time series and computed velues by EP engin
            #like energy consumptions, electric loads, heated and non heated areas.
            #the Endinfo file could be reads and plot elsewhere. it reports number of warning and errors
            start = time.time()
            Res[nbcase], Endinfo = Set_Outputs.Read_Outputhtml(idf,CaseName,Buildingsfile[nbcase])
            #aggregation of specific outputs for printing resume files
            Res[nbcase]['Year'] = building.year
            Res[nbcase]['Residential'] = building.OccupType['Residential']
            Res[nbcase]['EPCMeters'] = building.EPCMeters
            Res[nbcase]['EPHeatArea'] = building.EPHeatedArea
            #avoiding the two stage dictionnary for csv wrinting purposes. could be ignore if different csv are neede
            for key1 in ResEso:
                #if not 'Environ' in key1:
                    Res[nbcase][key1]= {}
                    for key2 in ResEso[key1]:
                        Res[nbcase][key1]['Data_'+key2] = ResEso[key1][key2]['GlobData']
                        Res[nbcase][key1]['TimeStep_'+key2] = ResEso[key1][key2]['TimeStep']
                        Res[nbcase][key1]['Unit_'+key2] = ResEso[key1][key2]['Unit']

            end = time.time()
            print('Read HTML and organize Res dict step time : ' + str(end - start))
            print(Endinfo)

            #copy for savings the errors file for each run, the html results file and compute a csv file.
            shutil.copyfile(CaseName+'out.err', 'Building'+str(nbcase)+'.err')
            shutil.copyfile(CaseName + 'tbl.htm', 'Building' + str(nbcase) + '.html')
            csv2tabdelim.WriteCSVFile('Building' + str(nbcase) + '.csv', ResEso)
            #this was used when using the automatic csv file from EP engine. no more needed
            #shutil.copyfile(CaseName + 'out.csv', 'Building' + str(nbcase) + '.csv')
            #csv2tabdelim.convert('Building' + str(nbcase) + '.csv')

        #the current building object is removed
        del building


#resum all global resultats into one simple ASCII file
ObjectName = open('GlobOutputs.txt','w')
for key in Res:
    towrite = {}
    for keys in Res[key]:
        if not 'Heated' in keys and not 'OutdoorSite' in keys:
            towrite[keys] = Res[key][keys]
    ObjectName.write(str(towrite)+'\n')
ObjectName.close()

#save the time series and globa resultats into one pickle
with open('GlobPickle.pickle', 'wb') as handle:
    pickle.dump(Res, handle, protocol=pickle.HIGHEST_PROTOCOL)

#removing the temp files with CaseName ref
for file in os.listdir():
    if CaseName in file[0:len(CaseName)]:
        # print('Removing', file, ' from folder')
        os.remove(file)

#removong the path to the local package of eppy and geomeppy
#sys.path.remove(path2addeppy)
sys.path.remove(path2addgeom)


