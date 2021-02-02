import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.getcwd()),'geomeppy')
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)
# from multiprocessing import set_start_method
# set_start_method("spawn")

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
import multiprocessing as mp

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

def RunProcess(MainPath,epluspath):
    file2run = LaunchSim.initiateprocess(MainPath)
    LaunchSim.RunMultiProc(file2run, MainPath, True, 0.7,epluspath)

def LaunchProcess(nbcase,VarName2Change = [],Bounds = [],nbruns = 1):
#this main is written for validation of the global workflow. and as an example for other simulation
#the cases are build in a for loop and then all cases are launched in a multiprocess mode, the maximum %of cpu is given as input
    MainPath = os.getcwd()
    keyPath = {'epluspath' : '','Buildingsfile' : '','Shadingsfile' : ''}
    with open('Pathways.txt', 'r') as PathFile:
        Paths = PathFile.readlines()
        for line in Paths:
            for key in keyPath:
                if key in line:
                    keyPath[key] = os.path.normcase(line[line.find(':')+1:-1])

    epluspath = keyPath['epluspath']
    Buildingsfile = pygeoj.load(keyPath['Buildingsfile'])
    Shadingsfile = pygeoj.load(keyPath['Shadingsfile'])

    SimDir = os.path.join(os.getcwd(), 'CaseFiles')
    if not os.path.exists(SimDir):
        os.mkdir(SimDir)
    else:
        for i in os.listdir(SimDir):
            if os.path.isdir(os.path.join(SimDir,i)):
                for j in os.listdir(os.path.join(SimDir,i)):
                    os.remove(os.path.join(os.path.join(SimDir,i),j))
                os.rmdir(os.path.join(SimDir,i))
            else:
                os.remove(os.path.join(SimDir,i))
    # os.rmdir(RunDir)  # Now the directory is empty of files
    os.chdir(SimDir)
    Param = 1
    if len(VarName2Change)>0:
        problem = {}
        problem['names'] = VarName2Change
        problem['bounds'] = Bounds#,
        problem['num_vars'] = len(VarName2Change)
        #problem = read_param_file(MainPath+'\\liste_param.txt')
        Param = latin.sample(problem,nbruns)

    Res = {}
    #this will be the final list of studied cases : list of objects stored in a dict . idf key for idf object and building key for building database object
    #even though this approache might be not finally needed as I didnt manage to save full object in a pickle and reload it for launching.
    #see LaunchSim.runcase()
    #theretheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #choice of the building ofr which we're making probabilistic simulations

    CaseName = 'run'
    idf_ref, building_ref = appendBuildCase(StudiedCase, epluspath, nbcase, Buildingsfile, Shadingsfile, MainPath)
    # change on the building __init__ class in the simulation level should be done here
    setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here
    setBuildingLevel(idf_ref, building_ref)


    #now lets build as many case as there are value in the sampling done earlier
    for i,val in enumerate(Param):
        idf = copy.deepcopy(idf_ref)
        building = copy.deepcopy(building_ref)
        idf.idfname = 'Building_' + str(nbcase) +  'v'+str(i)
        Case={}
        Case['BuildIDF'] = idf
        Case['BuildData'] = building
        print('Building ', i, '/', len(Param), 'process starts')

        if i<round(nbruns/2):
            building.ExternalInsulation = True
        else:
            building.ExternalInsulation = False
        for varnum,var in enumerate(VarName2Change):
            if 'InternalMass' in var:
                intmass = building.InternalMass
                intmass['HeatedZoneIntMass']['WeightperZoneArea'] = Param[i, varnum]
                setattr(building, var, intmass)
            elif 'ExtMass' in var:
                exttmass = building.Materials
                exttmass['Wall Inertia']['Thickness'] = round(Param[i, varnum]*1000)/1000
                setattr(building, var, exttmass)
            else:
                setattr(building, var, Param[i,varnum])
            if 'MaxShadingDist' in var:
                building.shades = building.getshade(Buildingsfile[nbcase], Shadingsfile, Buildingsfile)

        # change on the building __init__ class in the envelope level should be done here
        setEnvelopeLevel(idf, building)
        #idf.view_model(test=False)
        #change on the building __init__ class in the zone level should be done here
        setZoneLevel(idf, building,MainPath)
        setOutputLevel(idf)
        # saving files and objects
        idf.saveas('Building_' + str(nbcase) +  'v'+str(i)+'.idf')
        with open('Building_' + str(nbcase) +  'v'+str(i)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)

    RunProcess(MainPath,epluspath)
    sys.path.remove(path2addgeom)
    os.chdir(MainPath)

if __name__ == '__main__' :
    CaseName = ['Thermal mass']
    BuildNum = [10]
    VarName2Change = ['ExtMass']
    Bounds = [[0.05,1]]
    for i in BuildNum:
        LaunchProcess(i,VarName2Change,Bounds,1000)
        os.rename(os.path.join(os.getcwd(), 'CaseFiles'), os.path.join(os.getcwd(), 'CaseFiles'+str(i)))
