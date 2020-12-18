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
import time
from DataBase.DB_Building import BuildingList


def appendBuildCase(StudiedCase,epluspath,nbcase):
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
    GeomScripts.createBuilding(idf,building, perim = False)


def setEnvelopeLevel(idf,building):
    ######################################################################################
    #Envelope Level (within the building level)
    ######################################################################################
    #the other geometric element are thus here
    GeomScripts.createRapidGeomElem(idf, building)

def setZoneLevel(idf,building):
    ######################################################################################
    #Zone level
    ######################################################################################
    #control command related equipment, loads and leaks for each zones
    Load_and_occupancy.CreateZoneLoadAndCtrl(idf,building,MainPath)

def setOutputLevel(idf):
    #ouputs definitions
    Set_Outputs.AddOutputs(idf)


if __name__ == '__main__' :

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
            idf, building = appendBuildCase(StudiedCase,epluspath,nbcase)
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
                setZoneLevel(idf, building)

                setOutputLevel(idf)

                # saving files and objects
                idf.saveas('Building_' + str(nbcase) + '.idf')
                with open('Building_' + str(nbcase) + '.pickle', 'wb') as handle:
                    pickle.dump(StudiedCase.building[-1], handle, protocol=pickle.HIGHEST_PROTOCOL)

    sys.path.remove(path2addgeom)
