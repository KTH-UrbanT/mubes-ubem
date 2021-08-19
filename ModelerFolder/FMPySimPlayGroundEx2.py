
""" This example uses FMpy as a environment to make FMU simulation. It deals only with
 changing the set point if the water taps goes above 70%of its maximum. It also gives the water
 taps as inputs thus giving an eaxmple of two inputs."""

import os,sys
from fmpy import read_model_description, extract
from fmpy.fmi1 import FMU1Slave
from fmpy.fmi2 import FMU2Slave
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
import shutil
import pickle
import time as timedelay
from CoreFiles import LaunchSim as LaunchSim
from ReadResults import Utilities

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
            FMUElement[FMUKeyName]['fmu'] = FMU1Slave(guid=model_description.guid,
                            unzipDirectory=FMUElement[FMUKeyName]['unzipdir'],
                            modelIdentifier=model_description.coSimulation.modelIdentifier,
                            instanceName=model_name)
            FMUElement[FMUKeyName]['fmu'].instantiate()
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
            FMUElement[FMUKeyName]['fmu'] = FMU2Slave(guid=model_description.guid,
                            unzipDirectory=FMUElement[FMUKeyName]['unzipdir'],
                            modelIdentifier=model_description.coSimulation.modelIdentifier,
                            instanceName=model_name)

            FMUElement[FMUKeyName]['fmu'].instantiate()
            FMUElement[FMUKeyName]['fmu'].setupExperiment(startTime=start_time, stopTime=stop_time)
            for i,input in enumerate(VarNames['Inputs']):
                FMUElement[FMUKeyName]['fmu'].setReal([vrs[input]],[VarNames['InitialValue'][i]])
            FMUElement[FMUKeyName]['fmu'].enterInitializationMode()
            FMUElement[FMUKeyName]['fmu'].exitInitializationMode()
    return  FMUElement

def LaunchFMU_Sim(FMUElement,VarNames, start_time,stop_time,step_size):
    time = start_time
    day = 0
    SetPoints = {}
    MeanTemp = {}
    HeatPow = {}
    FlowRate = {}
    DHWPow = {}
    bld = 0
    for key in FMUElement.keys():
        HeatPow[key] = [0]
        MeanTemp[key] = [0]
        SetPoints[key] = [21]
        FlowRate[key] = [0]
        DHWPow[key] = [0]
    timeBuffer = [0] * len(FMUElement.keys())
    extraVar = ['nbAppartments']
    Res = Utilities.GetData(work_dir, extraVar)

    WatertapsFile = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),
                                 'MUBES_UBEM\ExternalFiles\mDHW_Sum_over_40.txt')
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
            FMUElement[key]['fmu'].setReal([FMUElement[key]['Exch_Var']['TempSetPoint']], [SetPoints[key][-1]])
            FMUElement[key]['fmu'].setReal([FMUElement[key]['Exch_Var']['WaterTap_m3_s']],
                                         [watercurrenttaps * Res['nbAppartments'][Res['SimNum'].index(key)]])

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
  #now lets clean up al lthe folder and files
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

if __name__ == '__main__':
    MainPath = os.getcwd()
    SavedFolder = 'MUBES_SimResults/ForTest'
    work_dir = os.path.normcase(
        os.path.join(os.path.dirname(os.path.dirname(MainPath)), SavedFolder))
    os.chdir(work_dir)
    filelist = os.listdir(work_dir)
    start_time = 0*24*3600
    stop_time =  365*24*3600
    step_size = 900
    VarNames = {'Inputs': ['TempSetPoint','WaterTap_m3_s'],
                'InitialValue': [21,0],
                'Outputs' : ['MeanBldTemp','HeatingPower','DHWHeat']}
    #to make it work if being either version1.0 or 2.0 or FMU Standards
    try:
        FMUElement = InstAndInitiV1(filelist,VarNames,start_time,stop_time)
    except:
        FMUElement = InstAndInitiV2(filelist,VarNames, start_time, stop_time)
    LaunchFMU_Sim(FMUElement,VarNames, start_time, stop_time, step_size)
    CleanUpSimRes(work_dir, keepLogFolder=True)

