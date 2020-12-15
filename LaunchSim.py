#this program laucnhes all the simulation
import os
import sys
from subprocess import check_call


epluspath = 'C:\\EnergyPlusV9-1-0\\'
path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
sys.path.append(path2addgeom)

#a specific folder is created in a Temp folder for computation and seperate the different threads
SimDir = os.path.join(os.getcwd(),'OngoingdSim')
if not os.path.exists(SimDir):
    os.mkdir(SimDir)
os.chdir(os.getcwd() + '\\CasesFile\\')
listOfFiles = os.listdir('.')

#then I need to dress a process that for each idf file poresent in the liste subprocess should be launched.
#than for each we will be able to organize some calibratiomn process

EplusPath = 'C:\\EnergyPlusV9-1-0\\energyplus.exe'
WeatherPath = 'C:\\EnergyPlusV9-1-0\\WeatherData\\SWE_Stockholm.Arlanda.024600_IWEC.epw'
OutputDir = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\Sim_Results'
EPiddPath = 'C:\\EnergyPlusV9-1-0\\Energy+.idd'
OutputPrefix = 'run'
IDFPath = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\Sim_Results\\in.idf'




cmd = [EplusPath, '--weather', WeatherPath, '--output-directory', OutputDir, '--idd', EPiddPath, '--expandobjects', '--output-prefix', OutputPrefix, IDFPath]
check_call(cmd, stdout=open(os.devnull, "w"))