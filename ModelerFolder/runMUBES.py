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
    print('This is given by the pool : ', results)

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
        currIdx += 1
    return Config2Launch

def CreatePool2Launch(UUID,GlobKey):
    Pool2Launch = []
    NewUUIDList = []
    for nbfile,keyPath in enumerate(GlobKey):
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
        #check of the building to run
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            if not UUID:
                Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum})
                try: NewUUIDList.append(Bld.properties['50A_UUID'])
                except: NewUUIDList.append('BuildingIndexInFile:'+str(bldNum))
            else:
                try:
                    if Bld.properties['50A_UUID'] in UUID:
                        Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum})
                        NewUUIDList.append(Bld.properties['50A_UUID'])
                except: pass

    return Pool2Launch,NewUUIDList

if __name__ == '__main__' :

    
    ConfigFromAPI = Read_Arguments()
    config = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()),'CoreFiles','DefaultConfig.yml'))
    CaseChoices = config['SIM']['CaseChoices']

    if ConfigFromAPI:
        config = setConfig.ChangeConfigOption(config, ConfigFromAPI)
        CaseChoices['OutputFile'] = 'Outputs4API.txt'
    else:
        config = setConfig.check4localConfig(config, os.getcwd())
    config = setConfig.checkGlobalConfig(config)
    if type(config) != dict:
        print('Something seems wrong in : ' + config)
        sys.exit()
    epluspath = config['APP']['PATH_TO_ENERGYPLUS']
    #a first keypath dict needs to be defined to comply with the current paradigme along the code
    Buildingsfile = os.path.abspath(config['DATA']['Buildingsfile'])
    Shadingsfile = os.path.abspath(config['DATA']['Shadingsfile'])
    keyPath =  {'epluspath': epluspath, 'Buildingsfile': Buildingsfile, 'Shadingsfile': Shadingsfile,'pythonpath': '','GeojsonProperties':''}
    #this function makes the list of dictionnary with single input files if several are present inthe sample folder
    GlobKey, MultipleFiles = GrlFct.ListAvailableFiles(keyPath)
    #this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    Pool2Launch,CaseChoices['UUID'] = CreatePool2Launch(CaseChoices['UUID'],GlobKey)

    PathInputFile = keyPath
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
    File2Launch = []
    pythonpath = keyPath['pythonpath']

    for idx,Case in enumerate(Pool2Launch):
        keypath = Case['keypath']
        nbBuild = Case['BuildNum2Launch'] #this will be used in case the file has to be read again (launched through prompt cmd)
        MainInputs['FirstRun'] = True
        #First, lets create the folder for the building and simulation processes
        SimDir = GrlFct.CreateSimDir(CurrentPath, config['APP']['PATH_TO_RESULTS'],CaseChoices['CaseName'], SepThreads, nbBuild, idx, Refresh=CaseChoices['RefreshFolder'])
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
                LocalConfigFile['SIM']['CaseChoices']['UUID'] = LocalConfigFile['SIM']['CaseChoices']['UUID']
            else:
                LocalConfigFile['SIM']['CaseChoices']['UUID'][idx]
            with open(os.path.join(SimDir,'ConfigFile.yml'), 'w') as file:
                documents = yaml.dump(LocalConfigFile, file)

        #lets check if there are several simulation for one building or not
        if CaseChoices['NbRuns'] > 1:
            Finished = False
            idx_offset = 0
            NbRun = CaseChoices['NbRuns']
            while not Finished:
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
                print('Input files are being written...')
                pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                for i in NewRuns:
                    pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,keypath,nbBuild,ParamSample[i+idx_offset, :],i+idx_offset,pythonpath))
                pool.close()
                pool.join()
                #the simulation are launched below using a pool of the earlier created idf files
                if not CaseChoices['CreateFMU']:
                    print('Simulation runs have begun...')
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
                    print('Offset is :'+ str(idx_offset))

        # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
        elif not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v0.idf'))):
            # if not, then the building number will be appended to alist that will be used afterward
            File2Launch.append({'nbBuild': nbBuild, 'keypath': keypath})
    if CaseChoices['MakePlotsOnly']:
        FigCenter = []
        WindSize = 50
        for file_idx,file in enumerate(File2Launch):
            lastBld = True if (file_idx+1)/len(File2Launch)==1 else False
            BldObj,IDFObj,Check = CB_OAT.LaunchOAT(MainInputs, SimDir, file['keypath'], file['nbBuild'], [1], 0,
                                                  pythonpath,MakePlotOnly = CaseChoices['MakePlotsOnly'])
            if Check == 'OK':
                FigCenter, WindSize = GrlFct.ManageGlobalPlots(BldObj, IDFObj, FigCenter, WindSize,
                                                           CaseChoices['MakePlotsPerBld'],nbcase=[], LastBld=lastBld)
    elif not SepThreads and not CaseChoices['CreateFMU']:
        #lets launch the idf file creation process using the listed created above
        pool = mp.Pool(processes=int(nbcpu))
        for nbBuild in File2Launch:
            pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath))
        pool.close()
        pool.join()
        # now that all the files are created, we can aggregate all the log files into a single one.
        GrlFct.CleanUpLogFiles(SimDir)
        # lest create the pool and launch the simulations
        file2run = LaunchSim.initiateprocess(SimDir)
        pool = mp.Pool(processes=int(nbcpu))
        for i in range(len(file2run)):
            pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath,CaseChoices['API']), callback=giveReturnFromPool)
        pool.close()
        pool.join()
        GrlFct.AppendLogFiles(SimDir)
    elif CaseChoices['CreateFMU']:
        # now that all the files are created, we can aggregate all the log files into a single one.
        GrlFct.CleanUpLogFiles(SimDir)
        #the FMU are not taking advantage of the parallel computing option yet
        for nbBuild in File2Launch:
            CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath)

