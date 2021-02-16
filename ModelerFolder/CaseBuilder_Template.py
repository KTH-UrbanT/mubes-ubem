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
#     #LaunchSim()
#     LaunchSim.RunMultiProc(file2run, MainPath, True, CPUusage,epluspath)

def LaunchProcess(nbcase,VarName2Change = [],Bounds = [],nbruns = 1,CPUusage = 1):
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

    #Sampling process if someis define int eh function's arguments
    #It is currently using the latin hyper cube methods for the sampling generation (latin.sample)
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
    #Nevertheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = appendBuildCase(StudiedCase, epluspath, nbcase, Buildingsfile, Shadingsfile, MainPath)

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
        idf.idfname = 'Building_' + str(nbcase) +  'v'+str(i)
        Case={}
        Case['BuildIDF'] = idf
        Case['BuildData'] = building
        print('Building ', i, '/', len(Param), 'process starts')

        #example of modification with half of the runs with external insulation and half of the runs with internal insulation
        if i<round(nbruns/2):
            building.ExternalInsulation = True
        else:
            building.ExternalInsulation = False
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
        #idf.view_model(test=False)

        #change on the building __init__ class in the zone level should be done here
        setZoneLevel(idf, building,MainPath)

        setOutputLevel(idf,MainPath)

        # saving files and objects
        idf.saveas('Building_' + str(nbcase) +  'v'+str(i)+'.idf')
        with open('Building_' + str(nbcase) +  'v'+str(i)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return MainPath, epluspath

if __name__ == '__main__' :

    CaseName = 'Leak'                   #name of the current study (the ouput folder will be using this entry
    BuildNum = [7,5]                    #list of numbers : number of the buildings to be simulated works only for two building for the moment ...(threading issue with multiprocessing)
    VarName2Change = ['EnvLeak']        #list of strings: Variable names (same as Class Building attribute, if different see LaunchProcess 'for' loop)
    Bounds = [[0.4,3]]                  #list of 2 value list :bounds in which the above variable will be allowed to change
    NbRuns = 2                         #number of run to launch for each building (all VarName2Change will have automotaic allocated value (see sampling in LaunchProcess)
    CPUusage = 0.7                      #factor of possible use of total CPU for multiprocessing. If only one core is available, this value should be 1
    for nbBuild in BuildNum:
        MainPath, epluspath = LaunchProcess(nbBuild,VarName2Change,Bounds,NbRuns,CPUusage)
        # Now that all the input files have been generated, we can launch the computing phase using multiprocessing package
        file2run = LaunchSim.initiateprocess(MainPath)
        nbcpu = mp.cpu_count()*CPUusage
        pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
        for i in range(len(file2run)):
            # runcase(file2run[i], filepath)
            pool.apply_async(LaunchSim.runcase, args=(file2run[i], MainPath, epluspath))
        pool.close()
        pool.join()
        # lets supress the path we needed for geomeppy
        sys.path.remove(path2addgeom)
        # lets get back to the Main Folder we were at the very beginning
        os.chdir(MainPath)
        os.rename(os.path.join(os.getcwd(), 'CaseFiles'), os.path.join(os.getcwd(), CaseName+'_Build_'+str(nbBuild)))
