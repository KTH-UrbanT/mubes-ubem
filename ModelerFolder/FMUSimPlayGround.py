# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import fmipp
import os, sys
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
sys.path.append(os.path.dirname(os.getcwd()))
from CoreFiles import LaunchSim as LaunchSim
import pickle
import shutil
import time as timedelay
from ReadResults import Utilities

def launchFMUCoSim(work_dir):

  logging_on = False
  time_diff_resolution = 1e-9
  start_time = 0.
  stop_time = 86400*365.
  visible = False
  interactive = False
  stop_time_defined = True

  Filelist = os.listdir(work_dir)
  FMUElement = {}
  Inputkey = ['TempSetPoint','WaterTap_m3_s']
  InitialValue = [21,0]
  Outputkey = ['MeanBldTemp','HeatingPower','DHWHeat']
  idx1 = ['_', 'v']
  for file in Filelist:
    if file[-4:] == '.fmu':
      model_name = file[:-4]
      FMUKeyName = int(model_name[model_name.index(idx1[0]) + 1:model_name.index(idx1[1])])
      uri_to_extracted_fmu = fmipp.extractFMU(os.path.join( work_dir, file ) , work_dir )
      FMUElement[FMUKeyName] = fmipp.FMUCoSimulationV1(uri_to_extracted_fmu, model_name, logging_on, time_diff_resolution)
      status = FMUElement[FMUKeyName].instantiate(model_name, start_time, visible, interactive)
      assert status == fmipp.fmiOK
      for i,input in enumerate(Inputkey):
        status = FMUElement[FMUKeyName].setRealValue(input, InitialValue[i])
        assert status == fmipp.fmiOK
      status = FMUElement[FMUKeyName].initialize(start_time, stop_time_defined, stop_time)
      assert status == fmipp.fmiOK

  time = 0.
  step_size = 900.
  HeatPow = {}
  FlowRate = {}
  DHWPow = {}
  MeanTemp = {}
  SetPoints = {}
  for key in FMUElement.keys():
    HeatPow[key] = [0]
    FlowRate[key] = [0]
    DHWPow[key] = [0]
    MeanTemp[key] = [0]
    SetPoints[key] = [21]

  timeBuffer = [0]*len(FMUElement.keys())
  extraVar = ['nbAppartments']
  Res = Utilities.GetData(work_dir, extraVar)

  WatertapsFile= os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'MUBES_UBEM\ExternalFiles\mDHW_Sum_over_40.txt')
  with open(WatertapsFile, 'r') as handle:
    FileLines = handle.readlines()
  Watertaps = []
  for line in FileLines:
    Watertaps.append(float(line)*1e-4 / 6 / 40) #in order to transform the l/min into m#/s and to consider an average for 1 apartment
  Waterthreshold = max(Watertaps)*0.7       #this is a limit for which the setpoint will be changed

  while ( ( time + step_size ) - stop_time < time_diff_resolution ):
    watercurrenttaps = Watertaps[int(time/3600)]

    for i,key in enumerate(FMUElement.keys()):
      if watercurrenttaps > Waterthreshold:
        SetPoints[key].append(18)
        timeBuffer[i] = 0
      else:
        if timeBuffer[i]>3600:
          SetPoints[key].append(21)
        else:
          SetPoints[key].append(SetPoints[key][-1])

      status = FMUElement[key].setRealValue('WaterTap_m3_s', watercurrenttaps*Res['nbAppartments'][Res['SimNum'].index(key)])
      assert status == fmipp.fmiOK
      status = FMUElement[key].setRealValue('TempSetPoint', SetPoints[key][-1])
      assert status == fmipp.fmiOK
      new_step = True
      status =  FMUElement[key].doStep(time, step_size, new_step )
      assert status == fmipp.fmiOK
      timeBuffer[i] += step_size
    # Advance time.
    time += step_size
    for i,key in enumerate(FMUElement.keys()):
      MeanTemp[key].append(FMUElement[key].getRealValue(Outputkey[0]))
      assert FMUElement[key].getLastStatus() == fmipp.fmiOK
      HeatPow[key].append(FMUElement[key].getRealValue(Outputkey[1]))
      assert FMUElement[key].getLastStatus() == fmipp.fmiOK
      DHWPow[key].append(FMUElement[key].getRealValue(Outputkey[2]))
      assert FMUElement[key].getLastStatus() == fmipp.fmiOK


def CleanUpSimRes(work_dir):
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
      LaunchSim.savecase(buildName,os.path.join(work_dir,file),building,ResSimpath,buildNameidf,work_dir,withFMU = True)
      #unable to erase the fmu extracted folder as the dll is still open at this stage of the code....why ? still weird to me
      #shutil.rmtree(buildName)


if __name__ == '__main__' :
  MainPath = os.getcwd()
  SavedFolder = 'MUBES_SimResults/fortestFMU'

  work_dir = os.path.normcase(
    os.path.join(os.path.dirname(os.path.dirname(MainPath)),SavedFolder))
  os.chdir(work_dir)

  launchFMUCoSim(work_dir)
  CleanUpSimRes(work_dir)
