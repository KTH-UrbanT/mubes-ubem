# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
import re

# #add the required path for geomeppy special branch
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add the reauired path for all the above folder
sys.path.append('..')
MUBES_Paths = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'MUBES_UBEM'))
sys.path.append(MUBES_Paths)

import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.LaunchSim as LaunchSim
import CoreFiles.CaseBuilder_OAT as CB_OAT
import CoreFiles.setConfig as setConfig
import CoreFiles.CalibUtilities as CalibUtil
import shutil
import multiprocessing as mp
import platform
import json
import yaml
import copy

def giveReturnFromPool(results):
    donothing = 0
    print(results)

def Read_Arguments_Old():
    #these are defaults values:
    UUID = []
    DESO = []
    CaseName = []
    DataPath = []
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-UUID')):
            currIdx += 1
            UUID = sys.argv[currIdx]
        elif (currArg.startswith('-DESO')):
            currIdx += 1
            DESO = int(sys.argv[currIdx])
        elif (currArg.startswith('-CaseName')):
            currIdx += 1
            CaseName = sys.argv[currIdx]
        elif (currArg.startswith('-DataPath')):
            currIdx += 1
            DataPath = sys.argv[currIdx]
        currIdx += 1

    ListUUID = re.findall("[^,]+", UUID) if UUID else []

    return ListUUID,DESO,CaseName,DataPath

def Read_Arguments():
    #these are defaults values:
    Config2Launch = []
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-CONFIG')):
            currIdx += 1
            Config2Launch = json.loads(sys.argv[currIdx])
        if (currArg.startswith('-yml')):
            currIdx += 1
            Config2Launch = sys.argv[currIdx]
            return Config2Launch
        currIdx += 1
    return Config2Launch

def CreatePool2Launch(UUID,GlobKey):
    Pool2Launch = []
    NewUUIDList = []
    for nbfile,keyPath in enumerate(GlobKey):
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
        #check of the building to run
        idx = len(Pool2Launch)
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            if not UUID:
                Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum,'NbBldandOr':'' })
                try: NewUUIDList.append(Bld.properties['50A_UUID'])
                except: NewUUIDList.append('BuildingIndexInFile:'+str(bldNum))
            else:
                try:
                    if Bld.properties['50A_UUID'] in UUID:
                        Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum,'NbBldandOr':'' })
                        NewUUIDList.append(Bld.properties['50A_UUID'])
                except: pass
        if not Pool2Launch:
            print('###  INPUT ERROR ### ')
            print('/!\ None of the building UUID were found in the input GeoJson file...')
            print('/!\ Please, check you inputs.')
            sys.exit()
        Pool2Launch[idx]['NbBldandOr'] = str(len(Pool2Launch)-idx) +' buildings will be considered from '+os.path.basename(keyPath['Buildingsfile'])
    return Pool2Launch,NewUUIDList

if __name__ == '__main__' :
    #Main script to launch either simulation or plot of the urban area represened in the main geojson file
    #all inputs can be given inside a yml file. If not specified in a specific yml file, value form the defaultConfig.yml file will be considered
    #It can be launchedby :
    #python runMUBES.py     it will load the default yml file and check if a local one is present in same folder to adapt the default one
    #python runMUBES.py -yml MyConfig.yml   it will consider the specified yml file.
    #python runMUBES.py -CONFIG {xxxxxxx} json format of the yml file


    ConfigFromArg = Read_Arguments()
    config = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()),'CoreFiles','DefaultConfig.yml'))
    CaseChoices = config['2_SIM']['0_CaseChoices']
    if type(ConfigFromArg) == str and ConfigFromArg[-4:] == '.yml':
        localConfig = setConfig.read_yaml(ConfigFromArg)
        config = setConfig.ChangeConfigOption(config, localConfig)
    elif ConfigFromArg:
        config = setConfig.ChangeConfigOption(config, ConfigFromArg)
        CaseChoices['OutputFile'] = 'Outputs4API.txt'
    else:
        config = setConfig.check4localConfig(config, os.getcwd())
    config = setConfig.checkGlobalConfig(config)
    if type(config) != dict:
        print('[Config Error] Something seems wrong in : ' + config)
        sys.exit()
    if CaseChoices['Verbose']: print('[OK] Input config. info checked and valid.')
    epluspath = config['0_APP']['PATH_TO_ENERGYPLUS']
    #a first keypath dict needs to be defined to comply with the current paradigme along the code
    Buildingsfile = os.path.abspath(config['1_DATA']['Buildingsfile'])
    keyPath = {'epluspath': epluspath, 'Buildingsfile': Buildingsfile, 'pythonpath': '','GeojsonProperties': ''}
    #this function makes the list of dictionnary with single input files if several are present inthe sample folder
    GlobKey, MultipleFiles = GrlFct.ListAvailableFiles(keyPath)
    #this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    Pool2Launch,CaseChoices['UUID'] = CreatePool2Launch(CaseChoices['UUID'],GlobKey)
    ######################################################################################################################
    ########     LAUNCHING MULTIPROCESS PROCESS PART  (nothing should be changed hereafter)   ############################
    ######################################################################################################################
    if CaseChoices['NbRuns']>1:
        SepThreads = True
        if CaseChoices['CreateFMU'] :
            print('###  INPUT ERROR ### ' )
            print('/!\ It is asked to ceate FMUs but the number of runs for each building is above 1...')
            print('/!\ Please, check you inputs as this case is not allowed yet')
            sys.exit()
        if not CaseChoices['VarName2Change'] or not CaseChoices['Bounds']:
            if not CaseChoices['FromPosteriors']:
                print('###  INPUT ERROR ### ')
                print('/!\ It is asked to make several runs but no variable is specified or bound of variation...')
                print('/!\ Please, check you inputs VarName2Change and Bounds')
                sys.exit()
    else:
        SepThreads = False
        CaseChoices['VarName2Change'] = []
        CaseChoices['Bounds'] = []

    nbcpu = max(mp.cpu_count() * CaseChoices['CPUusage'], 1)

    nbBuild = 0
    #all argument are packed in a dictionnaru, as parallel process is used, the arguments shall be strictly kept for each
    #no moving object of dictionnary values that should change between two processes.
    FigCenter = []
    CurrentPath = os.getcwd()
    MainInputs = {}
    MainInputs['CorePerim'] = CaseChoices['CorePerim']
    MainInputs['FloorZoning'] = CaseChoices['FloorZoning']
    MainInputs['CreateFMU'] = CaseChoices['CreateFMU']
    MainInputs['TotNbRun'] = CaseChoices['NbRuns']
    MainInputs['OutputsFile'] = CaseChoices['OutputFile']
    MainInputs['VarName2Change'] = CaseChoices['VarName2Change']
    MainInputs['DebugMode'] = CaseChoices['DebugMode']
    MainInputs['DataBaseInput'] = []
    MainInputs['Verbose'] =CaseChoices['Verbose']
    pythonpath = keyPath['pythonpath']
    MultipleFileidx = 0
    MultipleFileName = ''
    if MultipleFiles:
        File2Launch = {key:[] for key in range(len(MultipleFiles))}
    else:
        File2Launch = {0:[]}
    for idx,Case in enumerate(Pool2Launch):
        if len(Case['NbBldandOr'])>0:
            if MultipleFiles:
                MultipleFileName = MultipleFiles[MultipleFileidx]
                MultipleFileidx += 1
            if CaseChoices['Verbose']: print('[Prep. phase] '+Case['NbBldandOr'])
        keypath = Case['keypath']
        nbBuild = Case['BuildNum2Launch'] #this will be used in case the file has to be read again (launched through prompt cmd)
        MainInputs['FirstRun'] = True
        #First, lets create the folder for the building and simulation processes
        SimDir = GrlFct.CreateSimDir(CurrentPath, config['0_APP']['PATH_TO_RESULTS'],CaseChoices['CaseName'],
                    SepThreads, nbBuild, idx, MultipleFile = MultipleFileName, Refresh=CaseChoices['RefreshFolder'],Verbose = CaseChoices['Verbose'])

        #a sample of parameter is generated if needed
        ParamSample,CaseChoices =  GrlFct.SetParamSample(SimDir, CaseChoices, SepThreads)
        #if a simulation is asked to be done from posterriors that does not exist, the process will skip this building
        if len(ParamSample) == 0 :
            shutil.rmtree(SimDir)
            continue
        MainInputs['TotNbRun'] = CaseChoices['NbRuns']
        MainInputs['VarName2Change'] = CaseChoices['VarName2Change']
        #lest create the local yml file that will be used afterward
        if not os.path.isfile((os.path.join(SimDir,'ConfigFile.yml'))) or idx ==0:
            LocalConfigFile = copy.deepcopy(config)
            if MainInputs['TotNbRun'] >1:
                LocalConfigFile['2_SIM']['0_CaseChoices']['UUID'] = LocalConfigFile['2_SIM']['0_CaseChoices']['UUID']
            else:
                LocalConfigFile['2_SIM']['0_CaseChoices']['UUID'][idx]
            with open(os.path.join(SimDir,'ConfigFile.yml'), 'w') as file:
                documents = yaml.dump(LocalConfigFile, file)

        #lets check if there are several simulation for one building or not
        if CaseChoices['NbRuns'] > 1 and not CaseChoices['MakePlotsOnly']:
            if idx == 0 and CaseChoices['Verbose']: print('Idf input files under process...')
            Finished = False
            idx_offset = 0 #this offset is used forcalibration ppurposes to extend the amount of needed file to laucnh
            NbRun = CaseChoices['NbRuns']
            while not Finished:
                #if CaseChoices['Verbose']: print('Initial input file is being created...')
                # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
                if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + '_template.idf'))):
                    #there is a need to launch the first one that will also create the template for all the others
                    CB_OAT.LaunchOAT(MainInputs,SimDir,keypath,nbBuild,ParamSample[0, :],0,pythonpath)
                # lets check whether all the files are to be run or if there's only some to run again
                NewRuns = []
                for i in range(NbRun):
                    if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v'+str(i+idx_offset)+'.idf'))):
                        NewRuns.append(i)
                #now the pool can be created changing the FirstRun key to False for all other runs
                MainInputs['FirstRun'] = False
                pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                for i in NewRuns:
                    pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,keypath,nbBuild,ParamSample[i+idx_offset, :],i+idx_offset,pythonpath))
                pool.close()
                pool.join()
                #the simulation are launched below using a pool of the earlier created idf files
                if not CaseChoices['CreateFMU']:
                    if CaseChoices['Verbose']: print('Simulation runs have begun...')
                    file2run = LaunchSim.initiateprocess(SimDir)
                    nbcpu = max(mp.cpu_count()*CaseChoices['CPUusage'],1)
                    pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                    for i in range(len(file2run)):
                        pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath, CaseChoices['API']), callback=giveReturnFromPool)
                    pool.close()
                    pool.join()
                    GrlFct.AppendLogFiles(SimDir)
                if not CaseChoices['Calibration']:
                    Finished = True
                else:
                    Finished,idx_offset,ParamSample = CalibUtil.CompareSample(Finished,idx_offset, SimDir, CurrentPath, nbBuild, CaseChoices['VarName2Change'],
                                CaseChoices['CalibTimeBasis'], CaseChoices['MeasurePath4Calibration'],ParamSample,
                                CaseChoices['Bounds'], CaseChoices['BoundsLim'], CaseChoices['ParamMethods'],NbRun)
                    if CaseChoices['Verbose'] and not Finished: print('Calibration under process, new files are needed : Offset is :'+ str(idx_offset))
                    if CaseChoices['Verbose'] and Finished: print('Calibration has reach its end, congrats !!')

        # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
        elif not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v0.idf'))) or CaseChoices['MakePlotsOnly']:
            # if not, then the building number will be appended to alist that will be used afterward
            File2Launch[max(MultipleFileidx-1,0)].append({'nbBuild': nbBuild, 'keypath': keypath, 'SimDir': SimDir})
    if CaseChoices['MakePlotsOnly']:
        FigCenter = []
        WindSize = 50
        totalsize = 0
        offset = 0
        for ListKey in File2Launch:
            totalsize += len(File2Launch[ListKey])
        for nbfile,ListKey in enumerate(File2Launch):
            for file_idx,file in enumerate(File2Launch[ListKey]):
                if CaseChoices['Verbose'] : print('process completed by '+str(round(100*(file_idx+nbfile+1+offset)/totalsize,1))+ ' %')
                done = (file_idx+nbfile+1+offset)/totalsize
                lastBld = True if done==1 and nbfile+1 == len(File2Launch) else False
                BldObj,IDFObj,Check = CB_OAT.LaunchOAT(MainInputs, file['SimDir'], file['keypath'], file['nbBuild'], [1], 0,
                                                      pythonpath,MakePlotOnly = CaseChoices['MakePlotsOnly'])
                if Check == 'OK':
                    FigCenter, WindSize = GrlFct.ManageGlobalPlots(BldObj, IDFObj, FigCenter, WindSize,
                                                               CaseChoices['MakePlotsPerBld'],nbcase=[], LastBld=lastBld)
            offset += file_idx
            GrlFct.CleanUpLogFiles(file['SimDir'])
    elif not SepThreads and not CaseChoices['CreateFMU']:
        CurrentSimDir = ''
        for ListKey in File2Launch:
            #lets launch the idf file creation process using the listed created above
            if MultipleFiles:
                if CurrentSimDir != File2Launch[ListKey][0]['SimDir']:
                    if CaseChoices['Verbose']: print('Idf input files under process using '+
                                                     os.path.basename(File2Launch[ListKey][0]['SimDir']))
            if not MultipleFiles and CaseChoices['Verbose']: print('Idf input files under process...')
            CurrentSimDir = File2Launch[ListKey][0]['SimDir']
            pool = mp.Pool(processes=int(nbcpu))
            for nbBuild in File2Launch[ListKey]:
                pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,nbBuild['SimDir'],nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath))
            pool.close()
            pool.join()
            # now that all the files are created, we can aggregate all the log files into a single one.
            GrlFct.CleanUpLogFiles(CurrentSimDir)
            # lest create the pool and launch the simulations
            if CaseChoices['Verbose']: print(
                        'Simulations under process for ' + os.path.basename(CurrentSimDir))
            file2run = LaunchSim.initiateprocess(nbBuild['SimDir'])
            pool = mp.Pool(processes=int(nbcpu))
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], nbBuild['SimDir'], epluspath,CaseChoices['API']), callback=giveReturnFromPool)
            pool.close()
            pool.join()
            GrlFct.AppendLogFiles(nbBuild['SimDir'])
    elif CaseChoices['CreateFMU']:
        # now that all the files are created, we can aggregate all the log files into a single one.
        GrlFct.CleanUpLogFiles(SimDir)
        #the FMU are not taking advantage of the parallel computing option yet
        for ListKey in File2Launch:
            for nbBuild in File2Launch[ListKey]:
                CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath)
    if CaseChoices['Verbose']: print('[Process Finished] runMUBES.py ended successfully')
