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

    CaseName = 'ecmscalibmonthlynew2'
    BuildNum = []
    VarName2Change = ['AirRecovEff','IntLoadCurveShape','wwr','EnvLeak','setTempLoL','AreaBasedFlowRate','WindowUval','WallInsuThick','RoofInsuThick']
    Bounds = [[0.5,0.9],[1,5],[0.2,0.4],[0.5,1.6],[18,22],[0.35,1],[0.7,2],[0.1,0.3],[0.2,0.4]]
    NbRuns = 100
    CPUusage = 0.8
    CreateFMU = False
    CorePerim = False
    FloorZoning = True
    PathInputFile = 'HammarbyLast.txt'#'Pathways_Template.txt'
    OutputsFile = 'Outputs.txt' #'Outputs_Template.txt'
    ZoneOfInterest = ''

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART  (nothing should be changed hereafter)   ############################
######################################################################################################################
    if NbRuns>1:
        SepThreads = True
        if CreateFMU:
            print('###  INPUT ERROR ### ' )
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

    #check of the building to run
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
        #all argument are packed in a dictionnarie, as parallel process is used, the arguments shall be strictly kept for each
        #no moving object of dictionnary values that should change between two processes.
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
        MainInputs['DataBaseInput'] = DataBaseInput
        File2Launch = {'nbBuild' : []}
        #to get to matched joint distribution'
        import pickle5
        import numpy as np
        with open(os.path.join(os.path.dirname(os.path.dirname(CurrentPath)),'MUBES_SimResults','calibmonthly', 'GlobalMatchedParam.pickle'), 'rb') as handle:
            GlobalMatch = pickle5.load(handle)
        #lets simulation the building only if we have a complete joint distribution of 100 matches
        for idx,nbBuild in enumerate(BuildNum2Launch):
            if nbBuild not in GlobalMatch['MonthlyBasis'].keys():
                continue
            MainInputs['FirstRun'] = True
            #First, lets create the folder for the building and simulation processes
            SimDir = GrlFct.CreateSimDir(CurrentPath,CaseName,SepThreads,nbBuild,idx,Refresh=True)
            # here I am applying the renovation action
            GlobalMatch['MonthlyBasis'][nbBuild]['WindowUval'] = [val / 2 for val in
                                                                 GlobalMatch['MonthlyBasis'][nbBuild]['WindowUval']]

            ParamSample = []
            for line in range(len(GlobalMatch['MonthlyBasis'][nbBuild]['AirRecovEff'])):
                ParamSample.append([GlobalMatch['MonthlyBasis'][nbBuild][name][line] for name in VarName2Change])

            FilteredSample = []
            for i in ParamSample:
                FilteredSample.append([round(val, 3) for val in i])
            ParamSample = np.array(FilteredSample)
            NbRuns2run = [i for i in range(min(100, len(ParamSample[:, 0])))]
            NbRuns = len(NbRuns2run)
            import random

            random.shuffle(NbRuns2run)
            ParamSample = ParamSample[NbRuns2run, :]
            Finished = False
            idx_offset = 0
            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
            with open(Paramfile, 'wb') as handle:
                pickle5.dump(ParamSample, handle, protocol=pickle5.HIGHEST_PROTOCOL)


            if idx<len(DataBaseInput['Build']):
                #lets check if there are several simulation for one building or not
                if NbRuns > 1:
                    # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
                    if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + '_template.idf'))):
                        #there is a need to launch the first one that will also create the template for all the others
                        CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild,ParamSample[0, :],0,pythonpath)
                    # lets check whether all the files are to be run or if there's only some to run again
                    NewRuns = []
                    for i in range(1,NbRuns):
                        if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v'+str(i)+'.idf'))):
                            NewRuns.append(i)
                    #now the pool can be created changing the FirstRun key to False for all other runs
                    MainInputs['FirstRun'] = False
                    pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                    for i in NewRuns:
                        pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,nbBuild,ParamSample[i, :],i,pythonpath))
                    pool.close()
                    pool.join()
                # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
                elif not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v0.idf'))):
                #if not, then the building number will be appended to alist that will be used afterward
                    File2Launch['nbBuild'].append(nbBuild)
                #the simulation atre launched below using a pool of the earlier created idf files
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
        if not SepThreads and not CreateFMU:
            #lets launch the idf file creation process using the listed created above
            pool = mp.Pool(processes=int(nbcpu))
            for nbBuild in File2Launch['nbBuild']:
                pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,nbBuild,[1],0,pythonpath))
            pool.close()
            pool.join()
            # now that all the files are created, we can aggregate all the log files into a single one.
            GrlFct.CleanUpLogFiles(SimDir)
            # lest create the pool and launch the simulations
            file2run = LaunchSim.initiateprocess(SimDir)
            pool = mp.Pool(processes=int(nbcpu))
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath))
            pool.close()
            pool.join()
        elif CreateFMU:
            # now that all the files are created, we can aggregate all the log files into a single one.
            GrlFct.CleanUpLogFiles(SimDir)
            #the FMU are not taking advantage of the parallel computing option yet
            for nbBuild in File2Launch['nbBuild']:
                CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild,[1],0,pythonpath)
