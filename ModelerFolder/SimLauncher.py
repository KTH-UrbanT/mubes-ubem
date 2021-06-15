# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
# #add the required path for geomeppy special branch
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add the reauired path for all the above folder
sys.path.append('..')

import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.LaunchSim as LaunchSim
import CoreFiles.CaseBuilder_OAT as CB_OAT
import multiprocessing as mp

if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART  (choices from the modeler)   ########################################################
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
# CreateFMU = False / True             #True = FMU are created for each building selected to be computed in BuildNum
#                                       #no simulation will be run but the folder CaseName will be available for the FMUSimPlayground.py
# CorePerim = False / True             #True = create automatic core and perimeter zonning of each building. This options increases in a quite
#                                       large amount both building process and simulation process.
#                                       It can used with either one zone per floor or one zone per heated or none heated zone
#                                       building will be generated first, all results will be saved in one single folder
# FloorZoning = False / True            True = thermal zoning will be realized for each floor of the building, if false, there will be 1 zone
#                                       for the heated volume and, if present, one zone for the basement (non heated volume
# PathInputFile = 'String'              #Name of the PathFile containing the paths to the data and to energyplus application (see ReadMe)
# OutputsFile = 'String'               #Name of the Outfile with the selected outputs wanted and the associated frequency (see file's template)
# ZoneOfInterest = 'String'             #Text file with Building's ID that are to be considered withoin the BuildNum list, if '' than all building in BuildNum will be considered

    CaseName = 'ForTest'
    BuildNum = [0,1,2]
    VarName2Change = ['MaxShadingDist']
    Bounds = [[0,300]]
    NbRuns = 1
    CPUusage = 0.8
    CreateFMU = False
    CorePerim = False
    FloorZoning = True
    PathInputFile = 'Pathways_Template.txt'
    OutputsFile = 'Outputs_Template.txt'
    ZoneOfInterest = ''

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART  (nothing should be changed hereafter)   ############################
######################################################################################################################
    if NbRuns>1:
        SepThreads = True
        if CreateFMU:
            print('/!\ /!\ ###  INPUT ERROR ### /!\/!\ ' )
            print('/!\ It is asked to ceate FMUs but the number of runs for each building is above 1...')
            print('/!\ Please, check you inputs as this case is not allowed yet')
            sys.exit()
    else:
        SepThreads = False
    nbcpu = max(mp.cpu_count() * CPUusage, 1)
    # reading the pathfiles and the geojsonfile
    keyPath = GrlFct.readPathfile(PathInputFile)
    epluspath = keyPath['epluspath']
    pythonpath = keyPath['pythonpath'] #this is needed only if processes are launch in terminal as it could be an options instead of staying in python environnement
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    BuildNum2Launch = [i for i in range(len(DataBaseInput['Build']))]
    if BuildNum:
        BuildNum2Launch = BuildNum
    if os.path.isfile(os.path.join(os.getcwd(), ZoneOfInterest)):
        NewBuildNum2Launch = []
        Bld2Keep = GrlFct.ReadZoneOfInterest(os.path.join(os.getcwd(), ZoneOfInterest), keyWord='50A Uuid')
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            if Bld.properties['50A_UUID'] in Bld2Keep and bldNum in BuildNum2Launch:
                NewBuildNum2Launch.append(bldNum)
        BuildNum2Launch = NewBuildNum2Launch
    if not BuildNum2Launch:
        print('Sorry, but no building matches with the requirements....Please, check your ZoneOfInterest')
    else:

        FigCenter = []
        CurrentPath = os.getcwd()
        MainInputs = {}
        MainInputs['CorePerim'] = CorePerim
        MainInputs['FloorZoning'] = FloorZoning
        MainInputs['CreateFMU'] = CreateFMU
        MainInputs['TotNbRun'] = NbRuns
        MainInputs['OutputsFile'] = OutputsFile
        MainInputs['VarName2Change'] = VarName2Change
        MainInputs['PathInputFiles'] = PathInputFile
        File2Launch = {'nbBuild' : []}
        for idx,nbBuild in enumerate(BuildNum2Launch):
            MainInputs['FirstRun'] = True
            #First, lets create the folder for the building and simulation processes
            SimDir = GrlFct.CreateSimDir(CurrentPath,CaseName,SepThreads,nbBuild,idx,Refresh=True)
            ParamSample =  GrlFct.SetParamSample(SimDir, NbRuns, VarName2Change, Bounds,SepThreads)
            if idx<len(DataBaseInput['Build']):
                #lets check if there are several simulation for one building or not
                if NbRuns > 1:
                    CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild,ParamSample[0, :],0,pythonpath)
                    MainInputs['FirstRun'] = False
                    pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                    for i in range(1,len(ParamSample)):
                        pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,nbBuild,ParamSample[i, :],i,pythonpath))
                    pool.close()
                    pool.join()
                else:
                    File2Launch['nbBuild'].append(nbBuild)

                if SepThreads and not CreateFMU:
                    file2run = LaunchSim.initiateprocess(SimDir)
                    nbcpu = max(mp.cpu_count()*CPUusage,1)
                    pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                    for i in range(len(file2run)):
                        pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath))
                    pool.close()
                    pool.join()

            else:
                print('All buildings in the input file have been treated.')
                print('###################################################')
                break
        # if choicies is done, once the building is finished parallel computing is launched for all files
        if not SepThreads and not CreateFMU:
            #lets launche the idf file creation process
            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
            for nbBuild in File2Launch['nbBuild']:
                pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,nbBuild,[1],0,pythonpath))
            pool.close()
            pool.join()
            # now that all the files are created, we can aggregate all the log files into a single one.
            GrlFct.CleanUpLogFiles(SimDir)
            file2run = LaunchSim.initiateprocess(SimDir)
            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath))
            pool.close()
            pool.join()
        elif CreateFMU:
            # now that all the files are created, we can aggregate all the log files into a single one.
            GrlFct.CleanUpLogFiles(SimDir)
            for nbBuild in File2Launch['nbBuild']:
                CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild,[1],0,pythonpath)

