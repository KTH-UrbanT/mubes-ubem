# @Author  : Xavier Faure
# @Email   : xavierf@kth.se


#this program laucnhes all the simulation
import os, sys, stat, platform
import pickle
import shutil
import CoreFiles.Set_Outputs as Set_Outputs
from subprocess import check_call


def initiateprocess(MainPath):
    #return a list of file name to launch with energyplus. If some resultst are already present, the will be removed form the returned list
    listOfFiles = os.listdir(MainPath)
    file2run = []
    for file in listOfFiles:
        if '.idf' in file:
            file2run.append(file)
    return file2run

def runcase(file,filepath, epluspath):
    #this function runs a case
    ResSimpath = os.path.join(filepath,'Sim_Results')
    if not os.path.exists(ResSimpath):
        os.mkdir(ResSimpath)
    with open(os.path.join(filepath,file[:-4]+'.pickle'), 'rb') as handle:
         loadB = pickle.load(handle)

    building = loadB['BuildData'] #the building object is loaded in order to be saved afterward with the simulation results
    Runfile = os.path.join(filepath,file)
    RunDir = os.path.join(filepath,file[:-4])
    print('Launching :'+file)
    if not os.path.exists(RunDir):
        os.mkdir(RunDir)
    os.chdir(RunDir)
    CaseName = 'Run'

    ##could be run using the idf object method 'run'
    #IDF.setiddname(os.path.join(epluspath,'Energy+.idd'))
    #idf = IDF(Runfile)
    #idf.epw = os.path.join(os.path.join(epluspath ,'WeatherData'),idf.idfobjects['SITE:LOCATION'][0].Name+'.epw') #the weather path is taken from the epluspath
    # os.mkdir(caseDir)
    # os.chdir(caseDir)
    #idf.run(output_prefix=CaseName, verbose='q')
    #idf.run(readvars=True, output_prefix=CaseName, verbose='q')

    #the process is launche on external terminal window
    if platform.system() == "Windows":
        eplus_exe = os.path.join(epluspath, "energyplus.exe")
    else:
        eplus_exe = os.path.join(epluspath, "energyplus")
    weatherpath = os.path.join(epluspath,building.WeatherDataFile)
    cmd = [eplus_exe, '--weather',os.path.normcase(weatherpath),'--output-directory',RunDir, \
           '--idd',os.path.join(epluspath,'Energy+.idd'),'--expandobjects','-r','--output-prefix',CaseName,Runfile]
    check_call(cmd, stdout=open(os.devnull, "w"))
    #once the simulation has ended, the results are saved
    #savecase(CaseName, RunDir, building, ResSimpath,file,idf,filepath)
    savecase(CaseName, RunDir, building, ResSimpath, file, filepath)
    print(file[:-4] + ' is finished')

def savecase(CaseName,RunDir,building,ResSimpath,file,filepath,withFMU = False):
    #the resultst are read with html table and energyplus eso files. The html could be avoid, but then some information will have to computes in the building object (could be)
    if withFMU:
        Res = Set_Outputs.Read_Outputhtml(os.path.join(RunDir, CaseName + 'Table.htm'))
        ResEso = Set_Outputs.Read_OutputsEso(os.path.join(RunDir, CaseName + '.eso'), Res['OutdoorSurfacesNames'], ZoneOutput=False)

    else:
        Res  = Set_Outputs.Read_Outputhtml(os.path.join(RunDir,CaseName+'tbl.htm'))
        ResEso = Set_Outputs.Read_OutputsEso(os.path.join(RunDir,CaseName+'out.eso'), Res['OutdoorSurfacesNames'], ZoneOutput=False)

    Res['BuildDB'] = building
    for key1 in ResEso:
        # if not 'Environ' in key1:
        Res[key1] = {}
        for key2 in ResEso[key1]:
            Res[key1]['Data_' + key2] = ResEso[key1][key2]['GlobData']
            Res[key1]['TimeStep_' + key2] = ResEso[key1][key2]['TimeStep']
            Res[key1]['Unit_' + key2] = ResEso[key1][key2]['Unit']
    if withFMU:
        shutil.copyfile(os.path.join(RunDir,CaseName+'.err'), os.path.join(ResSimpath,file[:-4] + '.err'))
        shutil.copyfile(os.path.join(RunDir,CaseName+'Table.htm'), os.path.join(ResSimpath,file[:-4] + '.html'))
    else:
        shutil.copyfile(os.path.join(RunDir, 'Runout.err'), os.path.join(ResSimpath, file[:-4] + '.err'))
        shutil.copyfile(os.path.join(RunDir, 'Runtbl.htm'), os.path.join(ResSimpath, file[:-4] + '.html'))
    #shutil.copyfile(RunDir + '\\' + 'Runout.csv', ResSimpath + file[:-4] + '.csv')
    with open(os.path.join(ResSimpath, file[:-4]+'.pickle'), 'wb') as handle:
        pickle.dump(Res, handle, protocol=pickle.HIGHEST_PROTOCOL)
    #csv2tabdelim.convert(ResSimpath + file[:-4] + '.csv')
    #csv2tabdelim.WriteCSVFile(ResSimpath+'\\'+file[:-4] + '.csv', ResEso)

    os.chdir(filepath)
    if not building.SaveLogFiles:
        for i in os.listdir(RunDir):
           os.remove(os.path.join(RunDir,i))
        os.rmdir(RunDir)  # Now the directory is empty of files

if __name__ == '__main__' :
     print('Launch_Sim.py')


