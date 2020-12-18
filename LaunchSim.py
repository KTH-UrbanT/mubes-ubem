#this program laucnhes all the simulation
import os, sys, stat
import time
import multiprocessing as mp
import pickle
import shutil
import CoreFiles.Set_Outputs as Set_Outputs
import CoreFiles.csv2tabdelim as csv2tabdelim
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
    ResSimpath = os.getcwd()+'\\Sim_Results\\'
    start = time.time()
    with open(filepath+file[:-4]+'.pickle', 'rb') as handle:
         loadB = pickle.load(handle)
    #idf = loadB['BuildIDF'] #currently the idf object losses some required information...don't know why (inheritances of class and classmtehod... to be investigate
    #the work around is to read the idf.file
    building = loadB['BuildData']
    Runfile = filepath + file
    RunDir = filepath + file[:-4]
    print(RunDir)
    if not os.path.exists(RunDir):
        os.mkdir(RunDir)
    os.chdir(RunDir)
    CaseName = 'Run'
     #e+ parameters
    epluspath = 'C:\\EnergyPlusV9-1-0\\'
    # selecting the E+ version and .idd file
    IDF.setiddname(epluspath + "Energy+.idd")
    idf = IDF(Runfile)
    idf.epw = epluspath + 'WeatherData\\'+ idf.idfobjects['SITE:LOCATION'][0].Name+'.epw' #the weather path is taken from the epluspath
    # os.mkdir(caseDir)
    # os.chdir(caseDir)
    idf.run(output_prefix=CaseName, verbose='q')

    # cmd = [epluspath, '--weather', idf.epw, '--output-directory', OutputDir, '--idd', epluspath + "Energy+.idd", '--expandobjects', '--output-prefix', 'Run'+str(nb), file]
    # check_call(cmd, stdout=open(os.devnull, "w"))
    ResEso = Set_Outputs.Read_OutputsEso(RunDir + '\\' + CaseName, ZoneOutput=False)
    Res, Endinfo = Set_Outputs.Read_Outputhtml(RunDir + '\\' + CaseName)
    Res['DataBaseArea'] = building.surface
    Res['NbFloors'] = building.nbfloor
    Res['NbZones'] = len(idf.idfobjects['ZONE'])
    Res['Year'] = building.year
    Res['Residential'] = building.OccupType['Residential']
    Res['EPCMeters'] = building.EPCMeters
    Res['EPHeatArea'] = building.EPHeatedArea
    for key1 in ResEso:
        # if not 'Environ' in key1:
        Res[key1] = {}
        for key2 in ResEso[key1]:
            Res[key1]['Data_' + key2] = ResEso[key1][key2]['GlobData']
            Res[key1]['TimeStep_' + key2] = ResEso[key1][key2]['TimeStep']
            Res[key1]['Unit_' + key2] = ResEso[key1][key2]['Unit']
    shutil.copyfile(RunDir + '\\' + 'Runout.err', ResSimpath + '\\' + file[:-4] + '.err')
    shutil.copyfile(RunDir + '\\' + 'Runtbl.htm', ResSimpath + '\\' + file[:-4] + '.html')
    with open(ResSimpath + '\\' + file[:-4]+'.pickle', 'wb') as handle:
        pickle.dump(Res, handle, protocol=pickle.HIGHEST_PROTOCOL)
    csv2tabdelim.WriteCSVFile(ResSimpath+'\\'+file[:-4] + '.csv', ResEso)
    #here we should save the results and introduce some calibration
    #maybe using the building object...i don't really know yet
    #it means several runs
    #let us delete the remainning files

    os.chdir(filepath)
    for i in os.listdir(RunDir):
       os.remove(RunDir+'\\'+i)
    os.rmdir(RunDir)  # Now the directory is empty of files

    end = time.time()
    print(file[:-4] + ' ended in ' + str(round((end-start)*10)/10) + ' sec')


def RunMultiProc(file2run,filepath):
    method1 = True #this is just to maje tries as the method1 seem to block the file saving process after the first shot on each core
    #thoe other methods works fine BUT it laucnhe all the case so CPU saturation is not the solutions neither
    if method1:
        nbcpu = mp.cpu_count()
        pool = mp.Pool(processes = int(nbcpu)) #let us allow 80% of CPU usage
        for i in range(len(file2run)):
             #runcase(file2run[i], filepath)
             pool.apply_async(runcase, args=(file2run[i], filepath))
        pool.close()
        pool.join()
    else:
        processes = [mp.Process(target=runcase, args=(file2run[i], filepath)) for i in range(len(file2run))]
        for p in processes:
            p.start()
        for p in processes:
            p.join()

if __name__ == '__main__' :

    MainPath =os.getcwd()
    filepath = MainPath + '\\CaseFiles\\'
    file2run = initiateprocess(filepath)
    RunMultiProc(file2run,filepath)
