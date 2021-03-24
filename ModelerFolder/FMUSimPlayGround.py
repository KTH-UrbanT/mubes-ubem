# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import fmipp
import os


work_dir = os.path.normcase('C:/Users/xav77\Documents\FAURE\prgm_python/UrbanT\Eplus4Mubes\MUBES_UBEM\ModelerFolder\RunningFolder')

logging_on = False
time_diff_resolution = 1e-9
start_time = 0.
stop_time = 86400*100.
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
val = [0]*len(FMUElement)
dt = [0]*len(FMUElement)
OnFlag = [False]*len(FMUElement)


while ( ( time + step_size ) - stop_time < time_diff_resolution ):
  # Make co-simulation step.
  print(sum(x))
  for i,key in enumerate(FMUElement.keys()):
    status = FMUElement[key].setRealValue(Inputkey, 21)
    assert status == fmipp.fmiOK
    new_step = True
    status =  FMUElement[key].doStep(time, step_size, new_step )
    assert status == fmipp.fmiOK

  # Advance time.
  time += step_size

  for i, key in FMUElement.keys():
    x[i] = FMUElement[key].getRealValue(Outputkey)
    assert FMUElement[key].getLastStatus() == fmipp.fmiOK
