#this program laucnhes all the simulation
import os, sys, stat
import time
import multiprocessing as mp
import pickle
from subprocess import check_call

path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
sys.path.append(path2addgeom)
from geomeppy import IDF


def initiateprocess(filepath):
    listOfFiles = os.listdir(filepath)
    file2run = []
    for file in listOfFiles:
        if '.idf' in file:
            file2run.append(file)
    return file2run

def runcase(file,filepath):
    start = time.time()
    Runfile = filepath + file
    RunDir = filepath + file[:-4]
    print(RunDir)
    if not os.path.exists(RunDir):
        os.mkdir(RunDir)
    os.chdir(RunDir)
    #with open(i, 'rb') as handle:
    #    file = pickle.load(handle)
    # e+ parameters
    epluspath = 'C:\\EnergyPlusV9-1-0\\'
    # selecting the E+ version and .idd file
    IDF.setiddname(epluspath + "Energy+.idd")
    idf = IDF(Runfile)
    idf.epw = epluspath + 'WeatherData\\'+ idf.idfobjects['SITE:LOCATION'][0].Name+'.epw' #the weather path is taken from the epluspath
    # os.mkdir(caseDir)
    # os.chdir(caseDir)
    idf.run(output_prefix='Run', verbose='q')

    # cmd = [epluspath, '--weather', idf.epw, '--output-directory', OutputDir, '--idd', epluspath + "Energy+.idd", '--expandobjects', '--output-prefix', 'Run'+str(nb), file]
    # check_call(cmd, stdout=open(os.devnull, "w"))


    #here we should save the results and introduce some calibration
    #maybe using the building object...i don't really know yet
    #it means several runs
    #let us delete the remainning files
    end = time.time()
    print(file[:-4] + ' ended in ' + str(round((end-start)*10)/10) + ' sec')
    #os.chdir(SimDir)
    #for i in os.listdir(caseDir):
    #    os.remove(caseDir+'\\'+i)
    #os.rmdir(caseDir)  # Now the directory is empty of files


if __name__ == '__main__' :
    #weneed to position in the casesfile folder
    #os.chdir(MainPath)
        #os.rmdir(SimDir)
    MainPath =os.getcwd()
    # SimDir = os.path.join(MainPath,'OngoingSim')
    # if not os.path.exists(SimDir):
    #     os.mkdir(SimDir)
    filepath = MainPath + '\\CasesFile\\'
    file2run = initiateprocess(filepath)

    processes = [mp.Process(target=runcase, args=(file2run[i],filepath)) for i in range(len(file2run))]
    for p in processes:
        p.start()
    for p in processes:
        p.join()


# #then I need to dress a process that for each idf file poresent in the liste subprocess should be launched.
# #than for each we will be able to organize some calibratiomn process
# EplusPath = 'C:\\EnergyPlusV9-1-0\\energyplus.exe'
# WeatherPath = 'C:\\EnergyPlusV9-1-0\\WeatherData\\SWE_Stockholm.Arlanda.024600_IWEC.epw'
# OutputDir = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\Sim_Results'
# EPiddPath = 'C:\\EnergyPlusV9-1-0\\Energy+.idd'
# OutputPrefix = 'run'
# IDFPath = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\Sim_Results\\in.idf'
# cmd = [EplusPath, '--weather', WeatherPath, '--output-directory', OutputDir, '--idd', EPiddPath, '--expandobjects', '--output-prefix', OutputPrefix, IDFPath]
# check_call(cmd, stdout=open(os.devnull, "w"))