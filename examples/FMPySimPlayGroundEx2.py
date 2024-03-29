
""" This example uses FMpy as a environment to make FMU simulation. It deals only with
 changing the set point if the water taps goes above 70%of its maximum. It also gives the water
 taps as inputs thus giving an example of two inputs."""

import os,sys
from fmpy import *
#from fmpy.fmi1 import FMU1Slave
from fmpy.fmi1 import fmi1OK
#from fmpy.fmi2 import FMU2Slave
from fmpy.fmi2 import fmi2OK
from fmpy.simulation import instantiate_fmu
path2addgeom = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\geomeppy'
#path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
sys.path.append(os.path.dirname(os.getcwd()))
import shutil
import pickle
import time as timedelay

##Callback function required to avoid having the printed message when everything goes fine with 2.0 !
def log_message2(componentEnvironment, instanceName, status, category, message):
    if status == fmi2OK:
        pass  # do nothing
    else:
        print(message.decode('utf-8'))

##Callback function required to avoid having the printed message when everything goes fine with 1.0 !
def log_message1(componentEnvironment, instanceName, status, category, message):
    if status == fmi1OK:
        pass  # do nothing
    else:
        print(message.decode('utf-8'))

def InstAndInitiV1(filelist,VarNames,start_time,stop_time) :
    idx1 = ['_', 'v']
    fmunNb = 0
    FMUElement = {}
    for file in filelist:
        if file[-4:] == '.fmu':
            fmunNb += 1
            model_name = file[:-4]
            FMUKeyName = int(model_name[model_name.index(idx1[0]) + 1:model_name.index(idx1[1])])
            FMUElement[FMUKeyName] = {}
            model_description = read_model_description(file)
            FMUElement[FMUKeyName]['unzipdir'] = extract(file)
            vrs = {}
            for variable in model_description.modelVariables:
                vrs[variable.name] = variable.valueReference
            FMUElement[FMUKeyName]['Exch_Var'] = vrs
            FMUElement[FMUKeyName]['fmu'] = instantiate_fmu(FMUElement[FMUKeyName]['unzipdir'], model_description,
                                                            fmi_type='CoSimulation', visible=False, debug_logging=False,
                                                            logger=log_message1, fmi_call_logger=None, library_path=None)
            # old way with a bunch of messages
            # FMUElement[FMUKeyName]['fmu'] = FMU1Slave(guid=model_description.guid,
            #                 unzipDirectory=FMUElement[FMUKeyName]['unzipdir'],
            #                 modelIdentifier=model_description.coSimulation.modelIdentifier,
            #                 instanceName=model_name)
            # FMUElement[FMUKeyName]['fmu'].instantiate()
            for i,input in enumerate(VarNames['Inputs']):
                FMUElement[FMUKeyName]['fmu'].setReal([vrs[input]],[VarNames['InitialValue'][i]])
            FMUElement[FMUKeyName]['fmu'].initialize(tStart=start_time, stopTime=stop_time)
    return  FMUElement

def InstAndInitiV2(filelist,VarNames,start_time,stop_time) :
    idx1 = ['_', 'v']
    fmunNb = 0
    FMUElement = {}
    for file in filelist:
        if file[-4:] == '.fmu':
            fmunNb += 1
            model_name = file[:-4]
            FMUKeyName = int(model_name[model_name.index(idx1[0]) + 1:model_name.index(idx1[1])])
            FMUElement[FMUKeyName] = {}
            model_description = read_model_description(file)
            FMUElement[FMUKeyName]['unzipdir'] = extract(file)
            vrs = {}
            for variable in model_description.modelVariables:
                vrs[variable.name] = variable.valueReference
            FMUElement[FMUKeyName]['Exch_Var'] = vrs
            FMUElement[FMUKeyName]['fmu'] = instantiate_fmu(FMUElement[FMUKeyName]['unzipdir'], model_description,
                                                            fmi_type='CoSimulation', visible=False, debug_logging=False,
                                                            logger=log_message2,
                                                            fmi_call_logger=None, library_path=None)
            # old way with a bunch of messages
            # FMUElement[FMUKeyName]['fmu'] = FMU2Slave(guid=model_description.guid,
            #                 unzipDirectory=FMUElement[FMUKeyName]['unzipdir'],
            #                 modelIdentifier=model_description.coSimulation.modelIdentifier,
            #                 instanceName=model_name)
            # FMUElement[FMUKeyName]['fmu'].instantiate()

            FMUElement[FMUKeyName]['fmu'].setupExperiment(startTime=start_time, stopTime=stop_time)
            for i,input in enumerate(VarNames['Inputs']):
                FMUElement[FMUKeyName]['fmu'].setReal([vrs[input]],[VarNames['InitialValue'][i]])
            FMUElement[FMUKeyName]['fmu'].enterInitializationMode()
            FMUElement[FMUKeyName]['fmu'].exitInitializationMode()
    return  FMUElement

def LaunchFMU_Sim(FMUElement,VarNames, start_time,stop_time,step_size,FilePath):
    time = start_time
    day = 0
    SetPoints = {}
    MeanTemp = {}
    HeatPow = {}
    FlowRate = {}
    DHWPow = {}
    IntLoad = {}
    bld = 0
    for key in FMUElement.keys():
        HeatPow[key] = [0]
        MeanTemp[key] = [0]
        SetPoints[key] = [21]
        FlowRate[key] = [0]
        DHWPow[key] = [0]
        IntLoad[key] = [0]
    timeBuffer = [0] * len(FMUElement.keys())
    extraVar = ['nbAppartments']
    Res = Utilities.GetData(work_dir, extraVar)

    WatertapsFile = os.path.join(FilePath,'domestic_hot_water_40_apartments.txt')
    with open(WatertapsFile, 'r') as handle:
        FileLines = handle.readlines()
    Watertaps = []
    for line in FileLines:
        Watertaps.append(float(
            line) * 1e-4 / 6 / 40)  # in order to transform the l/min into m#/s and to consider an average for 1 apartment
    Waterthreshold = max(Watertaps) * 0.7  # this is a limit for which the setpoint will be changed
    # simulation loop
    while time < stop_time:
        if (time % (240 * 3600)) == 0:
            day += 10
            print(str(day) + ' simulation days done')
        watercurrenttaps = Watertaps[int(time / 3600)]
        for i, key in enumerate(FMUElement.keys()):
            if watercurrenttaps > Waterthreshold:
                SetPoints[key].append(18)
                timeBuffer[i] = 0
            else:
                if timeBuffer[i] > 3600:
                    SetPoints[key].append(21)
                else:
                    SetPoints[key].append(SetPoints[key][-1])
            timeBuffer[i] += step_size
            IntLoad[key].append(2)  # a base of 2W/m2 is considered
            if 6 <= time % (24 * 3600) / 3600 <= 10:
                IntLoad[key][-1] = 10
            if 16 <= time % (24 * 3600) / 3600 <= 22:
                IntLoad[key][-1] = 10
            FMUElement[key]['fmu'].setReal([FMUElement[key]['Exch_Var']['TempSetPoint']], [SetPoints[key][-1]])
            FMUElement[key]['fmu'].setReal([FMUElement[key]['Exch_Var']['IntLoadPow']], [IntLoad[key][-1]])
            FMUElement[key]['fmu'].setReal([FMUElement[key]['Exch_Var']['WaterTap_m3_s']],
                                         [watercurrenttaps * Res['nbAppartments']
                                         [Res['BldSimName'].index(FMUElement[key]['fmu'].instanceName)]])

            FMUElement[key]['fmu'].doStep(currentCommunicationPoint=time, communicationStepSize=step_size)
            #lets catch the outputs (even if not used in this example, it could be used to control the next inputs)
            MeanTemp[key].append(FMUElement[key]['fmu'].getReal([FMUElement[key]['Exch_Var'][VarNames['Outputs'][0]]]))
            HeatPow[key].append(FMUElement[key]['fmu'].getReal([FMUElement[key]['Exch_Var'][VarNames['Outputs'][1]]]))
            DHWPow[key].append(FMUElement[key]['fmu'].getReal([FMUElement[key]['Exch_Var'][VarNames['Outputs'][2]]]))

        time += step_size

    for i, key in enumerate(FMUElement.keys()):
        FMUElement[key]['fmu'].terminate()
        FMUElement[key]['fmu'].freeInstance()
        shutil.rmtree(FMUElement[key]['unzipdir'] , ignore_errors=True)
    return time

def CleanUpSimRes(work_dir,keepLogFolder = False):
  #now lets clean up all the folders and files
  print('################################################')
  print('Starting the cleanup process')
  timedelay.sleep(5)
  ResSimpath = os.path.join(work_dir,'Sim_Results')
  if not os.path.exists(ResSimpath):
    os.mkdir(ResSimpath)
  liste = os.listdir()
  for file in liste:
    if 'Output_EPExport_' in file:
      buildName = file[len('Output_EPExport_'):]
      buildNameidf = buildName+'.idf'
      with open(os.path.join(work_dir,buildName+'.pickle'), 'rb') as handle:
           loadB = pickle.load(handle)
      building = loadB['BuildData']
      building.SaveLogFiles = keepLogFolder
      LaunchSim.savecase(buildName,os.path.join(work_dir,file),building,ResSimpath,buildNameidf,work_dir,withFMU = True)
      #unable to erase the fmu extracted folder as the dll is still open at this stage of the code....why ? still weird to me
      #shutil.rmtree(buildName)

def Read_Arguments():
    #these are defaults values:
    Config2Launch = []
    CaseNameArg =[]
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-yml')):
            currIdx += 1
            Config2Launch = sys.argv[currIdx]
        if (currArg.startswith('-Case')):
            currIdx += 1
            CaseNameArg = sys.argv[currIdx]
        currIdx += 1
    return Config2Launch,CaseNameArg

def getPathList(config):
    CaseName = config['2_CASE']['0_GrlChoices']['CaseName'].split(',')
    path = []
    Names4Plots = []
    congifPath = os.path.abspath(os.path.join(config['0_APP']['PATH_TO_RESULTS'],CaseName[0]))
    if not os.path.exists(congifPath):
            print('Sorry, the folder '+CaseName[0]+' does not exist... use -Case or -yml option or change your localConfig.yml')
            sys.exit()
    fmufound = False
    liste = os.listdir(congifPath)
    for file in liste:
        if '.fmu' in file[-4:]:
            fmufound = True
            break
    if not fmufound:
        print('Sorry, but no .fmu were found in ' + str(CaseName[0]))
        sys.exit()
    else:
        path.append(congifPath)
        if len(CaseName)>1:
            print('Sorry, but only one CaseName is allowed from now for fmu cosimulation. '+CaseName+' were given as inputs.')
            sys.exit()
    return path[0],CaseName[0]

if __name__ == '__main__' :

    localDir = os.getcwd()
    scriptPath = os.path.realpath(__file__)
    os.chdir(os.path.dirname(scriptPath))
    sys.path.append(os.path.join(os.path.dirname(os.getcwd()), 'bin'))
    import core.LaunchSim as LaunchSim
    import core.setConfig as setConfig
    import outputs.output_utilities as Utilities
    from building_geometry.BuildingObject import Building
    filesPath = os.path.join(os.path.dirname(os.getcwd()), 'default','data')

    ConfigFromArg, CaseNameArg = Read_Arguments()
    config = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()), 'default', 'config', 'DefaultConfig.yml'))
    # lets get the environment variable and try if there is a new made one
    try:
        env = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()), 'default', 'config', 'env.yml'))
    except:
        env = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()), 'default', 'config', 'env.default.yml'))
    # make the change for the env variable
    config, msg = setConfig.ChangeConfigOption(config, env)
    if msg: print(msg)
    configUnit = setConfig.read_yaml(
        os.path.join(os.path.dirname(os.getcwd()), 'default', 'config', 'DefaultConfigKeyUnit.yml'))

    if CaseNameArg:
        # this case is if a folder Name has been given, the local yml file will be read to make the config dictionary
        CaseFolder1 = os.path.join(localDir, CaseNameArg)
        CaseFolder2 = CaseNameArg
        if not os.path.isfile(os.path.join(CaseFolder1, 'ConfigFile.yml')) and not os.path.isfile(
                os.path.join(CaseFolder2, 'ConfigFile.yml')):
            print('[Unknown Case] the following folder was not found : ' + CaseNameArg)
            sys.exit()
        else:
            try:
                localConfig = setConfig.read_yaml(os.path.join(CaseFolder1, 'ConfigFile.yml'))
            except:
                localConfig = setConfig.read_yaml(os.path.join(CaseFolder2, 'ConfigFile.yml'))
        config, msg = setConfig.ChangeConfigOption(config, localConfig)
        #
        # localConfig, filefound, msg = setConfig.check4localConfig(os.getcwd())
        # config['2_CASE']['0_GrlChoices']['CaseName'] = CaseNameArg
        work_dir, CaseName = getPathList(config)
    elif type(ConfigFromArg) == str:
        if ConfigFromArg[-4:] == '.yml':
            ymlfile1 = os.path.join(localDir, ConfigFromArg)
            ymlfile2 = ConfigFromArg
            if not os.path.isfile(ymlfile1) and not os.path.isfile(ymlfile2):
                print('[Error] yml file not found : ' + os.path.abspath(ConfigFromArg))
                sys.exit()
            try:
                config = setConfig.read_yaml(ymlfile1)
            except:
                try:
                    config = setConfig.read_yaml(ymlfile2)
                except:
                    print('[Error] The .yml file failed to be loaded, please check if the file')
                    sys.exit()
            work_dir, CaseName = getPathList(config)
        else:
            print('[Unknown Argument] Please check the available options for arguments : -yml or -Case')
            sys.exit()
    else:
        work_dir, CaseName = getPathList(config)
    print('[Studied Results Folder] ' + str(CaseName))

    os.chdir(work_dir)
    filelist = os.listdir(work_dir)
    start_time = 0*24*3600
    stop_time =  100*24*3600
    step_size = 900
    VarNames = {'Inputs': ['TempSetPoint','IntLoadPow','WaterTap_m3_s'],
                'InitialValue': [21,0,0],
                'Outputs' : ['MeanBldTemp','HeatingPower','DHWHeat']}
    #to make it work if being either version1.0 or 2.0 or FMU Standards
    try:
        FMUElement = InstAndInitiV1(filelist,VarNames,start_time,stop_time)
        print('FMU 1.0 used')
    except:
        FMUElement = InstAndInitiV2(filelist,VarNames, start_time, stop_time)
        print('FMU 2.0 used')
    LaunchFMU_Sim(FMUElement,VarNames, start_time, stop_time, step_size,filesPath)
    CleanUpSimRes(work_dir, keepLogFolder=True)

