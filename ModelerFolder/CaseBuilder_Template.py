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
from BuildObject.DB_Building import BuildingList
import BuildObject.DB_Data as DB_Data
import multiprocessing as mp

def LaunchProcess(SimDir,DataBaseInput,LogFile,bldidx,keyPath,nbcase,CorePerim = False,FloorZoning = False,VarName2Change = [],Bounds = [],
                  nbruns = 1, SepThreads = True, CreateFMU = False,FigCenter=(0,0),PlotBuilding = False):

    #Building and Shading objects fronm reading the geojson file as input for further functions
    Buildingsfile = DataBaseInput['Build']
    Shadingsfile = DataBaseInput['Shades']

    #process is launched for the considered building
    msg = 'Building ' + str(nbBuild) + ' is starting\n'
    print(msg[:-1])
    GrlFct.Write2LogFile(msg,LogFile)

    MainPath = os.getcwd()
    epluspath = keyPath['epluspath']
    #
    # #the current folder is created depending on the options
    # if not CreateFMU:
    #     SimDir = os.path.normcase(os.path.join(MainPath, 'RunningFolder'))
    # else:

    os.chdir(SimDir)

    #the parameter are constructed. the oupute gives a matrix ofn parameter to change with nbruns values to simulate
    ParamSample = GrlFct.getParamSample(VarName2Change,Bounds,nbruns)

    #All buildings are organized and append in a list (list of building object. But the process finally is not used as it have been thought to.
    #each building is laucnhed afterward using the idf file and not the object directly (see LaunchSim.runcase() function
    #Nevertheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath,LogFile)

    #Rounds of check if we continue with this building or not
    Var2check = len(building_ref.BlocHeight) if building_ref.Multipolygon else building_ref.height
    #if the building have bloc with no Height or if the hiegh is below 1m (shouldn't be as corrected in the Building class now)
    if len(building_ref.BlocHeight) > 0 and min(building_ref.BlocHeight) < 1:
        Var2check = 0
    #is heated area is below 50m2, we just drop the building
    if building_ref.EPHeatedArea < 50:
        Var2check = 0
    #is no floor is present...(shouldn't be as corrected in the Building class now)
    if 0 in building_ref.BlocNbFloor:
        Var2check = 0

    if Var2check == 0:
        msg =  '[Error] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n'
        print(msg[:-1])
        os.chdir(MainPath)
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)
        return epluspath, building_ref.WeatherDataFile,building_ref.RefCoord

    # change on the building __init__ class in the simulation level should be done here as the function below defines the related objects
    GrlFct.setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here as the function below defines the related objects
    GrlFct.setBuildingLevel(idf_ref, building_ref,LogFile,CorePerim,FloorZoning)

    #now lets build as many cases as there are value in the sampling done earlier
    for i,val in enumerate(ParamSample):
        #we need to copy the reference object because there is no need to set for each the simulation level nor the building level
        # (except if some wanted to do so and thus the above function will have to be in the for loop process
        idf = copy.deepcopy(idf_ref)
        building = copy.deepcopy(building_ref)

        idf.idfname = 'Building_' + str(nbcase) +  'v'+str(i)
        Case={}
        #Case['BuildIDF'] = idf
        Case['BuildData'] = building

        # # example of modification with half of the runs with external insulation and half of the runs with internal insulation
        # if i < round(nbruns / 2):
        #     building.ExternalInsulation = True
        # else:
        #     building.ExternalInsulation = False

        #now lets go along the VarName2Change list and change the building object attributes
        #if these are embedded into several layer of dictionnaries than there is a need to make checks and change accordingly the correct element
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
                setattr(building, var, ParamSample[i,varnum])     #for all other cases with simple float, this line just change the attribute's value directly

            #here is an other example for changing the distance underwhich the surrounding building are considered for shading aspects
            #as 'MaxShadingDist' is an input for the Class building method getshade, the method shall be called again after modifying this value (see getshade methods)
            if 'MaxShadingDist' in var:
                building.shades = building.getshade(Buildingsfile[nbcase], Shadingsfile, Buildingsfile,DB_Data.GeomElement,LogFile)

        #here is an other example of simplemodification we want as forcing the building to have recovery on its ventilation system
        #or the change the U value of the Window.
        #for changes done this way, there are no modification in each runs. all the runs will have forced values for the considered attributes
        #lets put all ventilation with heat recovery to True
        # building.VentSyst['BalX'] = True
        # building.VentSyst['ExhX'] = True
        #lets change the windos U value
        # building.Materials['Window']['UFactor'] = 0.78

        ##############################################################
        ##After having made the changes we wanted in the building object, we can continue the construction of the idf (input file for EnergyPLus)
        # change on the building __init__ class in the envelope level should be done here
        GrlFct.setEnvelopeLevel(idf, building)

        #this is forthe ploting option
        if PlotBuilding:
            FigCentroid = building_ref.RefCoord
            idf.idfname = 'Building_' + str(nbcase) + 'v' + str(i) + '_FormularId:' + str(
                building.BuildID['FormularId'])
            idf.view_model(test=True, FigCenter=FigCentroid)

        #change on the building __init__ class in the zone level should be done here
        GrlFct.setZoneLevel(idf, building,FloorZoning)

        #add some extra energy loads like domestic Hot water
        GrlFct.setExtraEnergyLoad(idf,building)

        #lets add the main gloval variable : Mean temperautre over the heated areas and the total building power consumption
        #and if present, the heating needs for DHW production as heated by direct heating
        #these are added thourgh EMS option of EnergyPlus
        EMSOutputs = []
        EMSOutputs.append('Mean Heated Zones Air Temperature')
        EMSOutputs.append('Total Building Heating Power')
        if idf.getobject('WATERUSE:EQUIPMENT', building.DHWInfos['Name']):
            EMSOutputs.append('Total DHW Heating Power')

        GrlFct.setOutputLevel(idf,building,MainPath,EMSOutputs)

        if CreateFMU:
            GrlFct.CreatFMU(idf,building,nbcase,epluspath,SimDir, i,EMSOutputs,LogFile)
        else:
            # saving files and objects
            idf.saveas('Building_' + str(nbcase) +  'v'+str(i)+'.idf')

        #the data object is saved as needed afterward aside the Eplus results
        with open('Building_' + str(nbcase) +  'v'+str(i)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
        msg = 'Input IDF file ' + str(i+1)+ '/'  + str(len(ParamSample))+ ' is done\n'
        print(msg[:-1])
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)
    return epluspath, building_ref.WeatherDataFile, building_ref.RefCoord


if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART     ##################################################################################
######################################################################################################################
#The Modeler have to fill in the following parameter to define his choices

# CaseName = 'String'                   #name of the current study (the ouput folder will be renamed using this entry)
# BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
#                                       geojsonfile), if empty, all building in the geojson file will be considered
# VarName2Change = ['String','String']  #list of strings: Variable names (same as Class Building attribute, if different
#                                       see LaunchProcess 'for' loop for examples)
# Bounds = [[x1,y1],[x2,y2]]            #list of list of 2 values  :bounds in which the above variable will be allowed to change
# NbRuns = 1000                         #number of run to launch for each building (all VarName2Change will have automotaic
#                                       allocated value (see sampling in LaunchProcess)
# CPUusage = 0.7                        #factor of possible use of total CPU for multiprocessing. If only one core is available,
#                                       this value should be 1
# SepThreads = False / True             #True = multiprocessing will be run for each building and outputs will have specific
#                                       folders (CaseName string + number of the building. False = all input files for all
#                                       building will be generated first, all results will be saved in one single folder
#                                       This options is to be set to True only for several simulation over one building
# CreateFMU = False / True             #True = FMU are created for each building selected to be computed in BuildNum
#                                       #no simulation will be run but the folder CaseName will be available for the FMUSimPlayground.py
# CorePerim = False / True             #True = create automatic core and perimeter zonning of each building. This options increases in a quite
#                                       large amount both building process and simulation process.
#                                       It can used with either one zone per floor or one zone per heated or none heated zone
#                                       building will be generated first, all results will be saved in one single folder
# FloorZoning = False / True            True = thermal zoning will be realized for each floor of the building, if false, there will be 1 zone
#                                       for the heated volume and, if present, one zone for the basement (non heated volume
## PlotBuilding = False / True          #True = after each building (and before the zoning details (setZoneLevel) the building will
#                                       be plotted for viisuaal check of geometrie and thermal zoning. It include the shadings
# PathInputFile = 'String'              #Name of the PathFile containing the paths to the data and to energyplus application (see ReadMe)
#
    CaseName = 'ForTest'
    BuildNum = []
    VarName2Change = []
    Bounds = []
    NbRuns = 3
    CPUusage = 0.8
    SepThreads = False
    CreateFMU = False
    CorePerim = False
    FloorZoning = True
    PlotBuilding = True
    PathInputFile = 'Pathways_Template.txt'

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
######################################################################################################################
    #reading the pathfiles and the geojsonfile
    keyPath = GrlFct.readPathfile(PathInputFile)
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    FigCenter = []
    LogFile=[]
    CurrentPath = os.getcwd()
    BuildNum2Launch = [i for i in range(len(DataBaseInput['Build']))]
    if BuildNum:
        BuildNum2Launch = BuildNum
    for idx,nbBuild in enumerate(BuildNum2Launch):
        #First, lets create the folder for the building and simulation processes
        SimDir,LogFile = GrlFct.CreateSimDir(CurrentPath,CaseName,SepThreads,nbBuild,idx,LogFile)

        if idx<len(DataBaseInput['Build']):
            #getting through the mainfunction above :LaunchProcess() each building sees its idf done in a row within this function
            try:
                epluspath, weatherpath,NewCentroid = LaunchProcess(SimDir,DataBaseInput,LogFile,idx,keyPath,nbBuild,CorePerim,FloorZoning,
                        VarName2Change,Bounds,NbRuns,SepThreads,CreateFMU,FigCenter,PlotBuilding)
            except:
                msg = '[ERROR] There was an error on this building, process aborted\n'
                print(msg[:-1])
                GrlFct.Write2LogFile(msg, LogFile)
                GrlFct.Write2LogFile('##############################################################\n', LogFile)
                os.chdir(CurrentPath)
            #if choicies is done, once the building is finished parallel computing is launched for this one
            if SepThreads and not CreateFMU:
                try:
                    LogFile.close()
                except:
                    pass
                file2run = LaunchSim.initiateprocess(SimDir)
                nbcpu = max(mp.cpu_count()*CPUusage,1)
                pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                for i in range(len(file2run)):
                    pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath, weatherpath))
                pool.close()
                pool.join()
                #GrlFct.SaveCase(SimDir,SepThreads,CaseName,nbBuild)
        else:
            print('All buildings in the input file have been treated.')
            print('###################################################')
            break
    # if choicies is done, once the building is finished parallel computing is launched for all files
    if not SepThreads and not CreateFMU:
        try:
            LogFile.close()
        except:
            pass
        file2run = LaunchSim.initiateprocess(SimDir)
        nbcpu = max(mp.cpu_count()*CPUusage,1)
        pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
        for i in range(len(file2run)):
            pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath, weatherpath))
        pool.close()
        pool.join()
        #GrlFct.SaveCase(SimDir, SepThreads,CaseName,nbBuild)
    #lets supress the path we needed for geomeppy
    # import matplotlib.pyplot as plt
    # plt.show()
    sys.path.remove(path2addgeom)