# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add needed packages
import pickle
import copy
import shutil
#add scripts from the project as well
sys.path.append("..")
import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.LaunchSim as LaunchSim
from DataBase.DB_Building import BuildingList
import DataBase.DB_Data as DB_Data
import multiprocessing as mp

def LaunchProcess(DataBaseInput,LogFile,bldidx,keyPath,nbcase,CorePerim = False,VarName2Change = [],Bounds = [],nbruns = 1, SepThreads = True, CreateFMU = False,FigCenter=(0,0),PlotBuilding = False):
#this main is written for validation of the global workflow. and as an example for other simulation
#the cases are build in a for loop and then all cases are launched in a multiprocess mode, the maximum %of cpu is given as input
    Buildingsfile = DataBaseInput['Build']
    Shadingsfile = DataBaseInput['Shades']

    msg = 'Building ' + str(nbBuild) + ' is starting\n'
    print(msg[:-1])
    GrlFct.Write2LogFile(msg,LogFile)

    MainPath = os.getcwd()
    epluspath = keyPath['epluspath']

    SimDir = os.path.join(os.getcwd(), 'RunningFolder')
    if not os.path.exists(SimDir):
        os.mkdir(SimDir)
    elif SepThreads or bldidx==0:
        shutil.rmtree(SimDir)
        os.mkdir(SimDir)
    os.chdir(SimDir)

    ParamSample = GrlFct.getParamSample(VarName2Change,Bounds,nbruns)

    #this will be the final list of studied cases : list of objects stored in a dict . idf key for idf object and building key for building database object
    #even though this approache might be not finally needed as I didnt manage to save full object in a pickle and reload it for launching.
    #see LaunchSim.runcase()
    #Nevertheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath,LogFile)
    FigCenter.append(building_ref.RefCoord)
    refx = sum([center[0] for center in FigCenter]) / len(FigCenter)
    refy = sum([center[1] for center in FigCenter]) / len(FigCenter)

    Var2check = len(building_ref.BlocHeight) if building_ref.Multipolygon else building_ref.height
    if building_ref.ATemp == 0:
        Var2check = 0
    if len(building_ref.BlocHeight) > 0 and min(building_ref.BlocHeight) < 1:
        Var2check = 0
    if building_ref.EPHeatedArea < 50:
        Var2check = 0
    if 0 in building_ref.BlocNbFloor:
        Var2check = 0
    if Var2check == 0:
        msg =  '[Error] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n'
        print(msg[:-2])
        os.chdir(MainPath)
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)
        return MainPath, epluspath, building_ref.WeatherDataFile,(refx, refy)

    # change on the building __init__ class in the simulation level should be done here
    GrlFct.setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here
    GrlFct.setBuildingLevel(idf_ref, building_ref,LogFile,CorePerim)

    #now lets build as many cases as there are value in the sampling done earlier
    for i,val in enumerate(ParamSample):
        #we need to copy the reference object because there is no need to set the simulation level nor the building level
        # (except if some wanted and thus the above function will have to be in the for loop process
        idf = copy.deepcopy(idf_ref)
        building = copy.deepcopy(building_ref)

        idf.idfname = 'Building_' + str(nbcase) +  'v'+str(i)+'_FormularId:'+str(building.BuildID['FormularId'])
        Case={}
        #Case['BuildIDF'] = idf
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
                intmass['HeatedZoneIntMass']['WeightperZoneArea'] = ParamSample[i, varnum]
                setattr(building, var, intmass)
            elif 'ExtMass' in var:
                exttmass = building.Materials
                exttmass['Wall Inertia']['Thickness'] = round(ParamSample[i, varnum]*1000)/1000
                setattr(building, var, exttmass)
            else:
                setattr(building, var, ParamSample[i,varnum])     #for all other cases with simple float just change the attribute's value directly
            #here is an other example for changing the distince underwhich the surrounding building are considered for shading aspects
            #as 'MaxShadingDist' is an input for the Class building method getshade, the method shall be called again after modifying this value (see getshade methods)
            if 'MaxShadingDist' in var:
                building.shades = building.getshade(Buildingsfile[nbcase], Shadingsfile, Buildingsfile,DB_Data.GeomElement)

        ##############################################################
        ##After having made the changes we wanted in the building object, we can continue the construction of the idf (input file for EnergyPLus)
        # change on the building __init__ class in the envelope level should be done here
        GrlFct.setEnvelopeLevel(idf, building)
        #just uncomment the line below if some 3D view of the building is wanted. The figure's window will have to be manually closed for the process to continue
        #print(building.BuildID['50A_UUID'])
        if PlotBuilding:
            FigCentroid = building_ref.RefCoord
            idf_ref.view_model(test=False, FigCenter=FigCentroid)

        #change on the building __init__ class in the zone level should be done here
        GrlFct.setZoneLevel(idf, building,MainPath)

        MeanTempName = 'Mean Heated Zones Air Temperature'
        TotPowerName = 'Total Building Heating Power'
        GrlFct.setOutputLevel(idf,MainPath,MeanTempName,TotPowerName)

        if CreateFMU:
            GrlFct.CreatFMU(idf,building,nbcase,epluspath,SimDir, i,TotPowerName,LogFile)
        else:
            # saving files and objects
            idf.saveas('Building_' + str(nbcase) +  'v'+str(i)+'.idf')

        with open('Building_' + str(nbcase) +  'v'+str(i)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
        msg = 'Input IDF file ' + str(i+1)+ '/'  + str(len(ParamSample))+ ' is done\n'
        print(msg[:-1])
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)
    return MainPath, epluspath, building_ref.WeatherDataFile, (refx, refy)


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

    CaseName = 'HammarbyTest1'
    BuildNum = [i for i in range(100)]
    VarName2Change = []
    Bounds = []
    NbRuns = 1
    CPUusage = 0.8
    SepThreads = False
    logFile =True
    CreateFMU = False
    CorePerim = False
    PlotBuilding = False

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
######################################################################################################################
    keyPath = GrlFct.readPathfile('HammarbyLast.txt')
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    FigCenter = []
    if logFile:
        if os.path.exists(os.path.join(os.getcwd(), CaseName + '_Logs.log')):
            os.remove(os.path.join(os.getcwd(), CaseName + '_Logs.log'))
        LogFile = open(os.path.join(os.getcwd(), CaseName + '_Logs.log'), 'w')
    else:
        LogFile = False
    for idx,nbBuild in enumerate(BuildNum):
        if idx<len(DataBaseInput['Build']):
            MainPath , epluspath, weatherpath,NewCentroid = LaunchProcess(DataBaseInput,LogFile,idx,keyPath,nbBuild,CorePerim,
                VarName2Change,Bounds,NbRuns,SepThreads,CreateFMU,FigCenter,PlotBuilding)
            if SepThreads and not CreateFMU:
                try:
                    LogFile.close()
                except:
                    pass
                file2run = LaunchSim.initiateprocess(MainPath)
                nbcpu = max(mp.cpu_count()*CPUusage,1)
                pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                for i in range(len(file2run)):
                    pool.apply_async(LaunchSim.runcase, args=(file2run[i], MainPath, epluspath, weatherpath))
                pool.close()
                pool.join()
                GrlFct.SaveCase(MainPath,SepThreads,CaseName,nbBuild)
        else:
            print('All buildings in the input file have been treated.')
            print('###################################################')
            break
    if not SepThreads and not CreateFMU:
        try:
            LogFile.close()
        except:
            pass
        file2run = LaunchSim.initiateprocess(MainPath)
        nbcpu = max(mp.cpu_count()*CPUusage,1)
        pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
        for i in range(len(file2run)):
            pool.apply_async(LaunchSim.runcase, args=(file2run[i], MainPath, epluspath, weatherpath))
        pool.close()
        pool.join()
        GrlFct.SaveCase(MainPath, SepThreads,CaseName,nbBuild)
    #lets supress the path we needed for geomeppy
    # import matplotlib.pyplot as plt
    # plt.show()
    sys.path.remove(path2addgeom)