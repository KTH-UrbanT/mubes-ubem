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
import copy
from DataBase.DB_Building import BuildingList
from SALib.sample import latin
from SALib.util import read_param_file


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
    GeomScripts.createBuilding(idf,building, perim = False)


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
    os.chdir(SimDir)

    problem = {}
    problem['names'] = 'EnvelopeLeakage'
    problem['bounds'] = [[0.4,4]]
    problem['num_vars'] = 1
    #problem = read_param_file(MainPath+'\\liste_param.txt')
    EnvelopeLeak = latin.sample(problem,100)

    Res = {}
    #this will be the final list of studied cases : list of objects stored in a dict . idf key for idf object and building key for building database object
    #even though this approache might be not finally needed as I didnt manage to save full object in a pickle and reload it for launching.
    #see LaunchSim.runcase()
    #theretheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #choice of the building ofr which we're making probabilistic simulations
    nbcase = 7
    CaseName = 'run'
    idf_ref, building_ref = appendBuildCase(StudiedCase, epluspath, nbcase, Buildingsfile, Shadingsfile, MainPath)
    # change on the building __init__ class in the simulation level should be done here
    setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here
    setBuildingLevel(idf_ref, building_ref)
    # change on the building __init__ class in the envelope level should be done here
    setEnvelopeLevel(idf_ref, building_ref)
    #now lets build as many case as there are value in the sampling done earlier

    for i,val in enumerate(EnvelopeLeak):
        idf = copy.deepcopy(idf_ref)
        building = copy.deepcopy(building_ref)
        Case={}
        Case['BuildIDF'] = idf
        Case['BuildData'] = building
        print('Building ', i, '/', len(EnvelopeLeak), 'process starts')
        building.EnvLeak = EnvelopeLeak[i][0]
        #change on the building __init__ class in the zone level should be done here
        setZoneLevel(idf, building,MainPath)
        setOutputLevel(idf)
        # saving files and objects
        idf.saveas('Building_' + str(nbcase) +  'v'+str(i)+'.idf')
        with open('Building_' + str(nbcase) +  'v'+str(i)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)


    RunProcess(MainPath)
    sys.path.remove(path2addgeom)
