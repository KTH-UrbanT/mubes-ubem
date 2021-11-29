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
from CoreFiles import LaunchSim as LaunchSim
from CoreFiles import CaseBuilder_OAT as CB_OAT
from CoreFiles import setConfig as setConfig
import multiprocessing as mp
import platform

def Read_Arguments():
    #these are defaults values:
    UUID = []
    DESO = []
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
        currIdx += 1

    ListUUID = re.findall("[^,]+", UUID) if UUID else []

    return ListUUID,DESO

def ListAvailableFiles(keyPath):
    # reading the pathfiles and the geojsonfile
    GlobKey = [keyPath]
    # lets see if the input file is a dir with several geojson files
    multipleFiles = False
    BuildingFiles, WallFiles = GrlFct.ReadGeoJsonDir(GlobKey[0])
    if BuildingFiles:
        multipleFiles = True
        MainRootPath = GlobKey[0]['Buildingsfile']
        GlobKey[0]['Buildingsfile'] = os.path.join(MainRootPath, BuildingFiles[0])
        GlobKey[0]['Shadingsfile'] = os.path.join(MainRootPath, WallFiles[0])
        for nb, file in enumerate(BuildingFiles[1:]):
            GlobKey.append(GlobKey[-1].copy())
            GlobKey[-1]['Buildingsfile'] = os.path.join(MainRootPath, file)
            GlobKey[-1]['Shadingsfile'] = os.path.join(MainRootPath, WallFiles[nb + 1])
    return GlobKey, multipleFiles

def CreatePool2Launch(UUID,GlobKey):
    Pool2Launch = []
    for nbfile,keyPath in enumerate(GlobKey):
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
        #check of the building to run
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            if not UUID:
                Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum})
            else:
                try:
                    if Bld.properties['50A_UUID'] in UUID:
                        Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum})
                except: pass

    return Pool2Launch

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

    #these are default values :
    UUID,DESO = Read_Arguments()

    config = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()),'CoreFiles','DefaultConfig.yml'))
    CaseChoices = config['SIM']['CaseChoices']
    if UUID:
        CaseChoices['UUID'] = UUID
    if DESO:
        CaseChoices['DESO'] = DESO
    CaseChoices['OutputsFile'] = 'Outputs4API.txt'
    config = setConfig.check4localConfig(config,os.getcwd())
    if type(config) != dict:
        print('Something seems wrong in : ' + config)
        print('Please check if there is a local.yml with your specific path')
        sys.exit()
    epluspath = config['APP']['PATH_TO_ENERGYPLUS']
    #a first keypath dict needs to be defined to comply with the current paradigme along the code
    Buildingsfile = os.path.abspath(config['DATA']['Buildingsfile'])
    Shadingsfile = os.path.abspath(config['DATA']['Shadingsfile'])
    keyPath =  {'epluspath': epluspath, 'Buildingsfile': Buildingsfile, 'Shadingsfile': Shadingsfile,'pythonpath': '','GeojsonProperties':''}
    #this function makes the list of dictionnary with single input files if several are present inthe sample folder
    GlobKey, MultipleFiles = ListAvailableFiles(keyPath)
    #this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    Pool2Launch = CreatePool2Launch(UUID,GlobKey)

    PathInputFile = keyPath
    ######################################################################################################################
    ########     LAUNCHING MULTIPROCESS PROCESS PART  (nothing should be changed hereafter)   ############################
    ######################################################################################################################
    if CaseChoices['NbRuns']>1:
        SepThreads = True
        if CaseChoices['CreateFMU']:
            print('###  INPUT ERROR ### ' )
            print('/!\ It is asked to ceate FMUs but the number of runs for each building is above 1...')
            print('/!\ Please, check you inputs as this case is not allowed yet')
            sys.exit()
    else:
        SepThreads = False
    nbcpu = max(mp.cpu_count() * CaseChoices['CPUusage'], 1)

    nbBuild = 0
    idx = 0
    #all argument are packed in a dictionnarie, as parallel process is used, the arguments shall be strictly kept for each
    #no moving object of dictionnary values that should change between two processes.
    FigCenter = []
    CurrentPath = os.getcwd()
    MainInputs = {}
    MainInputs['CorePerim'] = CaseChoices['CorePerim']
    MainInputs['FloorZoning'] = CaseChoices['FloorZoning']
    MainInputs['CreateFMU'] = CaseChoices['CreateFMU']
    MainInputs['TotNbRun'] = CaseChoices['NbRuns']
    MainInputs['OutputsFile'] = CaseChoices['OutputsFile']
    MainInputs['VarName2Change'] = CaseChoices['VarName2Change']
    MainInputs['DataBaseInput'] = []
    File2Launch = []
    pythonpath = keyPath['pythonpath']

    for Case in Pool2Launch:
        keypath = Case['keypath']
        nbBuild = Case['BuildNum2Launch'] #this will be used in case the file has to be read again (launched through prompt cmd)

        MainInputs['FirstRun'] = True
        #First, lets create the folder for the building and simulation processes
        SimDir = GrlFct.CreateSimDir(CurrentPath, CaseChoices['CaseName'], SepThreads, nbBuild, idx, Refresh=CaseChoices['RefreshFolder'])
        #a sample of parameter is generated is needed
        ParamSample =  GrlFct.SetParamSample(SimDir, CaseChoices['NbRuns'], CaseChoices['VarName2Change'], CaseChoices['Bounds'],SepThreads)
        #lets check if there are several simulation for one building or not
        if CaseChoices['NbRuns'] > 1:
            # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
            if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + '_template.idf'))):
                #there is a need to launch the first one that will also create the template for all the others
                CB_OAT.LaunchOAT(MainInputs,SimDir,keypath,nbBuild,ParamSample[0, :],0,pythonpath)
            # lets check whether all the files are to be run or if there's only some to run again
            NewRuns = []
            for i in range(CaseChoices['NbRuns']):
                if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v'+str(i)+'.idf'))):
                    NewRuns.append(i)
            #now the pool can be created changing the FirstRun key to False for all other runs
            MainInputs['FirstRun'] = False
            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
            for i in NewRuns:
                pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,keypath,nbBuild,ParamSample[i, :],i,pythonpath))
            pool.close()
            pool.join()
        # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
        elif not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v0.idf'))):
            #if not, then the building number will be appended to alist that will be used afterward
            File2Launch.append({'nbBuild' : nbBuild,'keypath': keypath})
        #the simulation are launched below using a pool of the earlier created idf files
        if SepThreads and not CaseChoices['CreateFMU']:
            file2run = LaunchSim.initiateprocess(SimDir)
            nbcpu = max(mp.cpu_count()*CaseChoices['CPUusage'],1)
            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath, True))
            pool.close()
            pool.join()

    if not SepThreads and not CaseChoices['CreateFMU']:
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
            pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath,True))
        pool.close()
        pool.join()
    elif CaseChoices['CreateFMU']:
        # now that all the files are created, we can aggregate all the log files into a single one.
        GrlFct.CleanUpLogFiles(SimDir)
        #the FMU are not taking advantage of the parallel computing option yet
        for nbBuild in File2Launch:
            CB_OAT.LaunchOAT(MainInputs,SimDir,nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath)

