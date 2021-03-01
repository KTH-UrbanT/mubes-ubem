import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add needed packages
import pygeoj
import pickle
import copy
from SALib.sample import latin
#add scripts from the project as well
sys.path.append("..")
import CoreFiles.GeomScripts as GeomScripts
import CoreFiles.Set_Outputs as Set_Outputs
import CoreFiles.Sim_param as Sim_param
import CoreFiles.Load_and_occupancy as Load_and_occupancy
import CoreFiles.LaunchSim as LaunchSim
import CoreFiles.MUBES_pygeoj as MUBES_pygeoj
from DataBase.DB_Building import BuildingList
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
    Sim_param.setSimparam(idf,building)

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

def setOutputLevel(idf,MainPath):
    #ouputs definitions
    Set_Outputs.AddOutputs(idf,MainPath)

# def RunProcess(MainPath,epluspath,CPUusage):
#     file2run = LaunchSim.initiateprocess(MainPath)
#     MultiProcInputs={'file2run' : file2run,
#                      'MainPath' : MainPath,
#                      'CPUmax' : CPUusage,
#                      'epluspath' : epluspath}
#     #we need to picke dump the input in order to have the protection of the if __name__ == '__main__' : in LaunchSim file
#     #so the argument are saved into a pickle and reloaded in the main (see if __name__ == '__main__' in LaunchSim file)
#     with open(os.path.join(MainPath, 'MultiProcInputs.pickle'), 'wb') as handle:
#         pickle.dump(MultiProcInputs, handle, protocol=pickle.HIGHEST_PROTOCOL)
#     LaunchSim.RunMultiProc(file2run, MainPath, False, CPUusage,epluspath)

def readPathfile(Pathways):
    keyPath = {'epluspath': '', 'Buildingsfile': '', 'Shadingsfile': ''}
    with open(Pathways, 'r') as PathFile:
        Paths = PathFile.readlines()
        for line in Paths:
            for key in keyPath:
                if key in line:
                    keyPath[key] = os.path.normcase(line[line.find(':') + 1:-1])

    return keyPath

def LaunchProcess(bldidx,keyPath,nbcase,VarName2Change = [],Bounds = [],nbruns = 1,CPUusage = 1, SepThreads = True):
#this main is written for validation of the global workflow. and as an example for other simulation
#the cases are build in a for loop and then all cases are launched in a multiprocess mode, the maximum %of cpu is given as input
    MainPath = os.getcwd()
    epluspath = keyPath['epluspath']
    Buildingsfile = MUBES_pygeoj.load(keyPath['Buildingsfile'])
    Shadingsfile = MUBES_pygeoj.load(keyPath['Shadingsfile'])

    SimDir = os.path.join(os.getcwd(), 'RunningFolder')
    if not os.path.exists(SimDir):
        os.mkdir(SimDir)
    elif SepThreads or bldidx==0:
        for i in os.listdir(SimDir):
            if os.path.isdir(os.path.join(SimDir,i)):
                for j in os.listdir(os.path.join(SimDir,i)):
                    os.remove(os.path.join(os.path.join(SimDir,i),j))
                os.rmdir(os.path.join(SimDir,i))
            else:
                os.remove(os.path.join(SimDir,i))
    os.chdir(SimDir)

    #Sampling process if someis define int eh function's arguments
    #It is currently using the latin hyper cube methods for the sampling generation (latin.sample)
    Param = [1]
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
    #Nevertheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = appendBuildCase(StudiedCase, epluspath, nbcase, Buildingsfile, Shadingsfile, MainPath)

    Var2check = len(building_ref.BlocHeight) if building_ref.Multipolygon else building_ref.height
    if len(building_ref.BlocHeight)>0 and min(building_ref.BlocHeight)<1:
       Var2check = 0
    if building_ref.EPHeatedArea <80:
        Var2check = 0
    if Var2check == 0:
        print('This Building does not have any height, process abort for this one')
        os.chdir(MainPath)
        return MainPath, epluspath

    # change on the building __init__ class in the simulation level should be done here
    setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here
    setBuildingLevel(idf_ref, building_ref)

    #now lets build as many cases as there are value in the sampling done earlier
    for i,val in enumerate(Param):
        #we need to copy the reference object because there is no need to set the simulation level nor the building level
        # (except if some wanted and thus the above function will have to be in the for loop process
        idf = copy.deepcopy(idf_ref)
        building = copy.deepcopy(building_ref)
        idf.idfname = 'Building_' + str(nbcase) +  'v'+str(i)+'_FormularId:'+str(building.BuildID['FormularId'])
        Case={}
        Case['BuildIDF'] = idf
        Case['BuildData'] = building

        # # example of modification with half of the runs with external insulation and half of the runs with internal insulation
        # if i < round(nbruns / 2):
        #     building.ExternalInsulation = True
        # else:
        #     building.ExternalInsulation = False

        #now lets go along the VarName2Change list and change the building object attributes
        #if these are embedded into several layer dictionnary than there is a need to make checks and change accordingly the correct element
        #here are examples for InternalMass impact using 'InternalMass' keyword in the VarName2Change list to play with the 'WeightperZoneArea' parameter
        #and for ExternalMass impact using 'ExtMass' keyword in the VarName2Change list to play with the 'Thickness' of the wall inertia layer
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
                setattr(building, var, Param[i,varnum])     #for all other cases with simple float just change the attribute's value directly
            #here is an other example for changing the distince underwhich the surrounding building are considered for shading aspects
            #as 'MaxShadingDist' is an input for the Class building method getshade, the method shall be called again after modifying this value (see getshade methods)
            if 'MaxShadingDist' in var:
                building.shades = building.getshade(Buildingsfile[nbcase], Shadingsfile, Buildingsfile)

        ##############################################################33
        ##After having made the changes we wanted in the building object, we can continue the construction of the idf (input file for EnergyPLus)

        # change on the building __init__ class in the envelope level should be done here
        setEnvelopeLevel(idf, building)

        #just uncomment the line below if some 3D view of the building is wanted. The figure's window will have to be manually closed for the process to continue
        #print(building.BuildID['50A_UUID'])
        #idf.view_model(test=True)

        #change on the building __init__ class in the zone level should be done here
        setZoneLevel(idf, building,MainPath)

        setOutputLevel(idf,MainPath)

        # saving files and objects
        idf.saveas('Building_' + str(nbcase) +  'v'+str(i)+'.idf')
        with open('Building_' + str(nbcase) +  'v'+str(i)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
        print('Input IDF file ', i+1, '/', len(Param), ' is done')
    #RunProcess(MainPath,epluspath,CPUusage)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)
    return MainPath, epluspath

def SaveCase(MainPath,SepThreads):
    SaveDir = os.path.join(os.path.dirname(MainPath), 'Results')
    if not os.path.exists(SaveDir):
        os.mkdir(SaveDir)
    if SepThreads:
        os.rename(os.path.join(MainPath, 'RunningFolder'),
                  os.path.join(SaveDir, CaseName + '_Build_' + str(nbBuild)))
    else:
        os.rename(os.path.join(os.getcwd(), 'RunningFolder'),
                  os.path.join(os.path.dirname(os.getcwd()), os.path.normcase('Results/' + CaseName)))

if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART     ##################################################################################
######################################################################################################################
#The Modeler have to fill in the following parameter to define its choices

# CaseName = 'String'                   #name of the current study (the ouput folder will be renamed using this entry)
# BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
#                                       geojsonfile)
# VarName2Change = ['String','String']  #list of strings: Variable names (same as Class Building attribute, if different
#                                       see LaunchProcess 'for' loopfor examples)
# Bounds = [[x1,y1],[x2,y2]]            #list of 2 values list :bounds in which the above variable will be allowed to change
# NbRuns = 1000                         #number of run to launch for each building (all VarName2Change will have automotaic
#                                       allocated value (see sampling in LaunchProcess)
# CPUusage = 0.7                        #factor of possible use of total CPU for multiprocessing. If only one core is available,
#                                       this value should be 1
# SepThreads = False / True             #True = multiprocessing will be run for each building and outputs will have specific
#                                       folders (CaseName string + number of the building. False = all input files for all
#                                       building will be generated first, all results will be saved in one single folder

    CaseName = '2D1zoneperfloorperim'
    BuildNum = [i for i in range(28)]
    VarName2Change = []
    Bounds = []
    NbRuns = 1
    CPUusage = 0.8
    SepThreads = False

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
######################################################################################################################
    keyPath = readPathfile('Pathways.txt')
    for idx,nbBuild in enumerate(BuildNum):
        print('Building '+str(nbBuild)+' is starting')
        MainPath , epluspath  = LaunchProcess(idx,keyPath,nbBuild,VarName2Change,Bounds,NbRuns,CPUusage,SepThreads)
        if SepThreads:
            file2run = LaunchSim.initiateprocess(MainPath)
            nbcpu = max(mp.cpu_count()*CPUusage,1)
            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], MainPath, epluspath))
            pool.close()
            pool.join()
            SaveCase(MainPath,SepThreads)
    if not SepThreads:
        file2run = LaunchSim.initiateprocess(MainPath)
        nbcpu = max(mp.cpu_count()*CPUusage,1)
        pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
        for i in range(len(file2run)):
            pool.apply_async(LaunchSim.runcase, args=(file2run[i], MainPath, epluspath))
        pool.close()
        pool.join()
        SaveCase(MainPath, SepThreads)
    #lets supress the path we needed for geomeppy
    # import matplotlib.pyplot as plt
    # plt.show()
    sys.path.remove(path2addgeom)