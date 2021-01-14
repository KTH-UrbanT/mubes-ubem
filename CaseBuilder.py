import os
import sys
#add the required path
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
import LaunchSim
import time
from DataBase.DB_Building import BuildingList


def appendBuildCase(StudiedCase,epluspath,nbcase,Buildingsfile,Shadingsfile,MainPath):
    StudiedCase.addBuilding('Building'+str(nbcase),Buildingsfile,Shadingsfile,nbcase,MainPath,epluspath)
    idf = StudiedCase.building[-1]['BuildIDF']
    building = StudiedCase.building[-1]['BuildData']
    return idf, building

def setSimLevel(idf,building):
    ####################################################################
    #Simulation Level
    #####################################################################
    Sim_param.Location_and_weather(idf,building)
    Sim_param.setSimparam(idf)

def setBuildingLevel(idf,building):
    ######################################################################################
    #Building Level
    ######################################################################################
    #this is the function that requires the most time
    GeomScripts.createBuilding(idf,building, perim = True)


def setEnvelopeLevel(idf,building):
    ######################################################################################
    #Envelope Level (within the building level)
    ######################################################################################
    #the other geometric element are thus here
    GeomScripts.createRapidGeomElem(idf, building)

def setZoneLevel(idf,building,MainPath):
    ######################################################################################
    #Zone level
    ######################################################################################
    #control command related equipment, loads and leaks for each zones
    Load_and_occupancy.CreateZoneLoadAndCtrl(idf,building,MainPath)

def setOutputLevel(idf):
    #ouputs definitions
    Set_Outputs.AddOutputs(idf)

def RunProcess(MainPath):
    file2run = LaunchSim.initiateprocess(MainPath)
    LaunchSim.RunMultiProc(file2run, MainPath, multi=True, maxcpu=0.8)

if __name__ == '__main__' :
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
    else:
        for i in os.listdir(SimDir):
            if os.path.isdir(SimDir+'\\'+i):
                for j in os.listdir(SimDir+'\\'+i):
                    os.remove(SimDir+'\\'+i+'\\'+j)
                os.rmdir(SimDir+'\\'+i)
            else:
                os.remove(SimDir+'\\'+i)
    #os.rmdir(RunDir)  # Now the directory is empty of files
    os.chdir(SimDir)

    Res = {}
    #this will be the final list of studied cases : list of objects stored in a dict . idf key for idf object and building key for building database object
    #even though this approache might be not finally needed as I didnt manage to save full object in a pickle and reload it for launching.
    #see LaunchSim.runcase()
    #theretheless this organization still enable to order things !
    StudiedCase = BuildingList()
    for nbcase in range(len(Buildingsfile)):
        #if nbcase==7:
            print('Building ', nbcase, '/', len(Buildingsfile), 'process starts')
            CaseName = 'run'
            # erasing all older file from previous simulation if present
            for file in os.listdir():
                if CaseName in file[0:len(CaseName)]:
                    #print('Removing', file, ' from folder')
                    os.remove(file)
            idf, building = appendBuildCase(StudiedCase,epluspath,nbcase,Buildingsfile,Shadingsfile,MainPath)
            #if the building does not have any hieght given by the databse, we skip it
            if not building.height:
                print('Building ',nbcase,' stop, Not enough data to proceed')
            else:
                #change on the building __init__ class in the simulation level should be done here
                setSimLevel(idf, building)
                # change on the building __init__ class in the building level should be done here
                setBuildingLevel(idf, building)
                #change on the building __init__ class in the envelope level should be done here
                setEnvelopeLevel(idf, building)
                #to have a matplotlib pop up windows of each instance : uncomment the line below
                #idf.view_model(test=False)
                #change on the building __init__ class in the zone level should be done here
                setZoneLevel(idf, building,MainPath)

                setOutputLevel(idf)

                # saving files and objects
                idf.saveas('Building_' + str(nbcase) + '.idf')
                with open('Building_' + str(nbcase) + '.pickle', 'wb') as handle:
                    pickle.dump(StudiedCase.building[-1], handle, protocol=pickle.HIGHEST_PROTOCOL)


    RunProcess(MainPath)
    sys.path.remove(path2addgeom)
