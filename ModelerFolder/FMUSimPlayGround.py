# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import fmipp
import os, sys
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
from CoreFiles import LaunchSim as LaunchSim
import pickle
import shutil
import time as timedelay

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
  Inputkey = 'TempSetPoint'
  Outputkey = 'HeatingPower'
  for file in Filelist:
    if file[-4:] == '.fmu':
      model_name = file[:-4]
      uri_to_extracted_fmu = fmipp.extractFMU(os.path.join( work_dir, file ) , work_dir )
      FMUElement[model_name] = fmipp.FMUCoSimulationV1(uri_to_extracted_fmu, model_name, logging_on, time_diff_resolution)
      status = FMUElement[model_name].instantiate(model_name, start_time, visible, interactive)
      assert status == fmipp.fmiOK
      status = FMUElement[model_name].setRealValue(Inputkey, 21)
      assert status == fmipp.fmiOK
      status = FMUElement[model_name].initialize(start_time, stop_time_defined, stop_time)
      assert status == fmipp.fmiOK

  time = 0.
  step_size = 900.
  x = [0]*len(FMUElement)
  val = [21]*len(FMUElement)
  dt = [0]*len(FMUElement)
  OnFlag = [False]*len(FMUElement)

  RedOn = 0
  setPoint = 21
  while ( ( time + step_size ) - stop_time < time_diff_resolution ):
    # Make co-simulation step.
    if (time%(3600*2)) ==0:
      setPoint = [21] * len(x)
      setPoint[int((time/(2*3600))%len(x))] = 18

    for i,key in enumerate(FMUElement.keys()):
      status = FMUElement[key].setRealValue(Inputkey, setPoint[i])
      assert status == fmipp.fmiOK
      new_step = True
      status =  FMUElement[key].doStep(time, step_size, new_step )
      assert status == fmipp.fmiOK

    # Advance time.
    time += step_size

    for i, key in enumerate(FMUElement.keys()):
      x[i] = FMUElement[key].getRealValue(Outputkey)
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

def SaveCase(work_dir,SavedDest):
  SaveDir = os.path.join(SavedDest, 'Results')
  if not os.path.exists(SaveDir):
    os.mkdir(SaveDir)
  os.rename(work_dir,
            os.path.join(SaveDir, SavedFolder))



if __name__ == '__main__' :
  MainPath = os.getcwd()
  SavedFolder = 'FMUsTest'

  SavedDest = os.path.normcase(
    'C:/Users/xav77\Documents\FAURE\prgm_python/UrbanT\Eplus4Mubes\MUBES_UBEM')

  work_dir = os.path.normcase(
    'C:/Users/xav77\Documents\FAURE\prgm_python/UrbanT\Eplus4Mubes\MUBES_UBEM\Results\MinnebergFMUwith25Wm')
  os.chdir(work_dir)

  launchFMUCoSim(work_dir)
  #CleanUpSimRes(work_dir)
  #SaveCase(work_dir,SavedDest)
