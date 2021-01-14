import os, sys
path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
sys.path.append(path2addgeom)
import pygeoj
from DataBase.DB_Building import BuildingList
import CaseBuilder
import pickle


#this main is written for validation of the global workflow. and as an example for other simulation
#the cases are build in a for loop and then all cases are launched in a multiprocess mode, the maximum %of cpu is given as input
MainPath = os.getcwd()
epluspath = 'C:\\EnergyPlusV9-1-0\\'
loadedfile = 'C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\Minneberg_Sweref99TM\\Buildings.geojson'
Buildingsfile = pygeoj.load(loadedfile)
loadedfile = 'C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\Minneberg_Sweref99TM\\Walls.geojson'
Shadingsfile = pygeoj.load(loadedfile)

SimDir = os.path.join(os.getcwd(),'CaseFiles')
if not os.path.exists(SimDir):
    os.mkdir(SimDir)
os.chdir(SimDir)

Res = {}
#this will be the final list of studied cases : list of objects stored in a dict . idf key for idf object and building key for building database object
#even though this approache might be not finally needed as I didnt manage to save full object in a pickle and reload it for launching.
#see LaunchSim.runcase()
#theretheless this organization still enable to order things !
StudiedCase = BuildingList()
for nbcase in range(len(Buildingsfile)):
    print(nbcase)
    if nbcase==7:
        print('Building ', nbcase, '/', len(Buildingsfile), 'process starts')
        CaseName = 'run'
        # erasing all older file from previous simulation if present
        for file in os.listdir():
            if CaseName in file[0:len(CaseName)]:
                #print('Removing', file, ' from folder')
                os.remove(file)
        idf, building = CaseBuilder.appendBuildCase(StudiedCase,epluspath,nbcase,Buildingsfile,Shadingsfile,MainPath)
        #if the building does not have any hieght given by the databse, we skip it
        if not building.height:
            print('Building ',nbcase,' stop, Not enough data to proceed')
        else:
            #change on the building __init__ class in the simulation level should be done here
            CaseBuilder.setSimLevel(idf, building)
            # change on the building __init__ class in the building level should be done here
            CaseBuilder.setBuildingLevel(idf, building)
            #change on the building __init__ class in the envelope level should be done here
            CaseBuilder.setEnvelopeLevel(idf, building)
            #to have a matplotlib pop up windows of each instance : uncomment the line below
            #idf.view_model(test=False)
            #change on the building __init__ class in the zone level should be done here
            CaseBuilder.setZoneLevel(idf, building,MainPath)

            CaseBuilder.setOutputLevel(idf)

            # saving files and objects
            idf.saveas('Building_' + str(nbcase) + '.idf')
            with open('Building_' + str(nbcase) + '.pickle', 'wb') as handle:
                pickle.dump(StudiedCase.building[-1], handle, protocol=pickle.HIGHEST_PROTOCOL)


CaseBuilder.RunProcess(MainPath)
sys.path.remove(path2addgeom)