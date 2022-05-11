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
import CoreFiles.LaunchSim as LaunchSim
import CoreFiles.CaseBuilder_OAT as CB_OAT
import CoreFiles.setConfig as setConfig
import CoreFiles.CalibUtilities as CalibUtil
import shutil
import multiprocessing as mp
import yaml
import copy

def giveReturnFromPool(results):
    doNothing = 0
    print(results)

if __name__ == '__main__' :
    #Main script to launch either simulation or plot of the urban area represened in the main geojson file
    #all inputs can be given inside a yml file. If not specified in a specific yml file, value from the defaultConfig.yml file will be considered
    #It can be launched by :
    #python runMUBES.py     it will load the default yml file and check if a local one is present in the same folder to adapt the default one
    #python runMUBES.py -yml MyConfig.yml   it will consider the specified yml file to adapt the default one
    #python runMUBES.py -CONFIG {xxxxxxx} json format of the yml file to adapt the default one for API application
    #python runMUBES.py -Case CaseName  it will launch the config file in the CaseName folder in the PATH_2_RESULTS main folder

    CaseChoices,config, SepThreads,Pool2Launch, MultipleFiles = setConfig.getConfig()
    if CaseChoices['MakePolygonPlots']:
        GrlFct.MakePolygonPlots(CaseChoices, Pool2Launch)
        sys.exit()
    epluspath = config['0_APP']['PATH_TO_ENERGYPLUS']
    nbcpu = max(mp.cpu_count() * CaseChoices['CPUusage'], 1)
    nbBuild = 0
    FigCenter = []
    CurrentPath = os.getcwd()
    MultipleFileidx = 0
    MultipleFileName = ''
    if MultipleFiles:
        File2Launch = {key:[] for key in range(len(MultipleFiles))}
    else:
        File2Launch = {0:[]}
    for idx,Case in enumerate(Pool2Launch):
        if len(Case['TotBld_and_Origin'])>0:
            if MultipleFiles:
                MultipleFileName = MultipleFiles[MultipleFileidx]
                MultipleFileidx += 1
            if CaseChoices['Verbose']: print('[Prep. phase] '+Case['TotBld_and_Origin'])
        keypath = Case['keypath']
        pythonpath = keypath['pythonpath']
        nbBuild = Case['BuildNum2Launch'] #this will be used in case the file has to be read again (launched through prompt cmd)
        CaseChoices['FirstRun'] = True
        #First, lets create the folder for the building and simulation processes
        SimDir = GrlFct.CreateSimDir(CurrentPath, config['0_APP']['PATH_TO_RESULTS'],CaseChoices['CaseName'],
                    SepThreads, nbBuild, idx, MultipleFile = MultipleFileName, Refresh=CaseChoices['RefreshFolder'],Verbose = CaseChoices['Verbose'])
        #a sample of parameter is generated if needed
        ParamSample,CaseChoices =  GrlFct.SetParamSample(SimDir, CaseChoices, SepThreads)
        #if a simulation is asked to be done from posterriors that does not exist, the process will skip this building
        if len(ParamSample) == 0 :
            shutil.rmtree(SimDir)
            continue
        #lest create the local yml file that will be used afterward
        if not os.path.isfile((os.path.join(SimDir,'ConfigFile.yml'))) or idx ==0:
            LocalConfigFile = copy.deepcopy(config)
            writeIds = False
            if CaseChoices['NbRuns'] >1:
                LocalConfigFile['2_CASE']['1_SimChoices']['BldID'] = CaseChoices['BldID'][idx]
            else:
                if len(CaseChoices['BldID'])>10:
                    LocalConfigFile['2_CASE']['1_SimChoices']['BldID'] = '# See ListOfBuiling_Ids.txt for list of IDs '
                    writeIds = True
                else:
                    LocalConfigFile['2_CASE']['1_SimChoices']['BldID'] = CaseChoices['BldID']
                if CaseChoices['VarName2Change']:
                    if CaseChoices['Verbose']: print('[Info] It seems that at least one parameter is to be changed but only one simulation is asked. Parameter default values will be used. ')
                CaseChoices['VarName2Change'] = []
            with open(os.path.join(SimDir,'ConfigFile.yml'), 'w') as file:
                documents = yaml.dump(LocalConfigFile, file)

        #lets check if there are several simulation for one building or not
        if CaseChoices['NbRuns'] > 1 and not CaseChoices['MakePlotsOnly']:
            if idx == 0 and CaseChoices['Verbose']: print('Idf input files under process...')
            Finished = False
            idx_offset = 0 #this offset is used forcalibration ppurposes to extend the amount of needed file to laucnh
            NbRun = CaseChoices['NbRuns']
            while not Finished:
                #if CaseChoices['Verbose']: print('Initial input file is being created...')
                # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
                if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + '_template.idf'))):
                    #there is a need to launch the first one that will also create the template for all the others
                    CB_OAT.LaunchOAT(CaseChoices,SimDir,keypath,nbBuild,ParamSample[0, :],0,pythonpath)
                # lets check whether all the files are to be run or if there's only some to run again
                NewRuns = []
                for i in range(NbRun):
                    if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v'+str(i+idx_offset)+'.idf'))):
                        NewRuns.append(i)
                #now the pool can be created changing the FirstRun key to False for all other runs
                CaseChoices['FirstRun'] = False
                pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                for i in NewRuns:
                    pool.apply_async(CB_OAT.LaunchOAT, args=(CaseChoices,SimDir,keypath,nbBuild,ParamSample[i+idx_offset, :],i+idx_offset,pythonpath))
                pool.close()
                pool.join()
                #the simulation are launched below using a pool of the earlier created idf files
                if CaseChoices['Verbose']: print('Simulation runs have begun...')
                file2run = LaunchSim.initiateprocess(SimDir)
                if not file2run and CaseChoices['Verbose'] :  print(
                        '[Info] All asked simulations are already done and results available...refreshfolder to remove those')
                nbcpu = max(mp.cpu_count()*CaseChoices['CPUusage'],1)
                pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                for i in range(len(file2run)):
                    pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath, CaseChoices['API']), callback=giveReturnFromPool)
                pool.close()
                pool.join()
                GrlFct.AppendLogFiles(SimDir,CaseChoices['BldIDKey'])
                if not CaseChoices['Calibration']:
                    Finished = True
                else:
                    Finished,idx_offset,ParamSample = CalibUtil.CompareSample(Finished,idx_offset, SimDir, CurrentPath, nbBuild, CaseChoices['VarName2Change'],
                                CaseChoices['CalibTimeBasis'], CaseChoices['MeasurePath4Calibration'],ParamSample,
                                CaseChoices['Bounds'], CaseChoices['BoundsLim'], CaseChoices['ParamMethods'],NbRun)
                    if CaseChoices['Verbose'] and not Finished: print('Calibration under process, new files are needed : Offset is :'+ str(idx_offset))
                    if CaseChoices['Verbose'] and Finished: print('Calibration has reach its end, congrats !!')

        # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
        elif not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v0.idf'))) or CaseChoices['MakePlotsOnly']:
            # if not, then the building number will be appended to alist that will be used afterward
            File2Launch[max(MultipleFileidx-1,0)].append({'nbBuild': nbBuild, 'keypath': keypath, 'SimDir': SimDir, 'BuildID': Case['BuildID']})
    # #lets write a file for the building IDs as it can be very long.
    if writeIds:
        if CaseChoices['Verbose']: print('[Prep.Info] Writing List of Building''s ID file')
        for nbfile,ListKey in enumerate(File2Launch):
            with open(os.path.join(File2Launch[ListKey][0]['SimDir'],'ListOfBuiling_Ids.txt'),'w') as f:
                msg = 'SimNum' + '\t' + 'BldID_'+str(CaseChoices['BldIDKey'])
                f.write(msg + '\n')
                for file in File2Launch[ListKey]:
                    msg = str(file['nbBuild']) + '\t' + str(file['BuildID'])
                    f.write(msg+'\n')

    if CaseChoices['MakePlotsOnly']:
        MakePlotOnly = 2 if CaseChoices['MakePlotsPerBld'] else 1
        FigCenter = []
        WindSize = 50
        totalsize = 0
        offset = 0
        cpt = '--------------------'
        cpt1 = '                    '
        for ListKey in File2Launch:
            totalsize += len(File2Launch[ListKey])
        for nbfile,ListKey in enumerate(File2Launch):
            GoodBld = 0
            for file_idx,file in enumerate(File2Launch[ListKey]):
                done = (file_idx+nbfile+1+offset)/totalsize
                lastBld = True if done==1 and nbfile+1 == len(File2Launch) else False
                BldObj,IDFObj,Check = CB_OAT.LaunchOAT(CaseChoices, file['SimDir'], file['keypath'], file['nbBuild'], [1], 0,
                                                      pythonpath,MakePlotOnly = MakePlotOnly)
                if CaseChoices['Verbose']:
                    print('Figure being completed by ' + str(round(100 * done, 1)) + ' %')
                else:
                    print('\r',end='')
                    ptcplt = '.' if file_idx%2 else ' '
                    msg = cpt[:int(20 * done)]+ptcplt+cpt1[int(20 * done):]+str(round(100 * done, 1))
                    print('Figure being completed by ' + msg + ' %',end = '',flush = True)

                if lastBld:
                    os.chdir(CurrentPath)
                    GrlFct.CleanUpLogFiles(file['SimDir'])
                    if Check == 'OK': GoodBld += 1
                    print('\nFigure completed with ' + str(GoodBld) + ' out of ' + str(
                            len(File2Launch[ListKey])) + ' buildings in total')
                if Check == 'OK':
                    GoodBld += 1
                    LastBldObj = copy.deepcopy(BldObj)
                    LastIDFObj = copy.deepcopy(IDFObj)
                    FigCenter, WindSize = GrlFct.ManageGlobalPlots(BldObj, IDFObj, FigCenter, WindSize,
                                                               CaseChoices['MakePlotsPerBld'],nbcase=[], LastBld=lastBld)
                elif lastBld:
                    FigCenter, WindSize = GrlFct.ManageGlobalPlots(LastBldObj, LastIDFObj, FigCenter, WindSize,
                                                                   CaseChoices['MakePlotsPerBld'], nbcase=[],
                                                                   LastBld=lastBld)
            offset += file_idx
            os.chdir(CurrentPath)
            GrlFct.CleanUpLogFiles(file['SimDir'])
    elif not SepThreads and not CaseChoices['CreateFMU'] and File2Launch[0]:
        CurrentSimDir = ''
        for ListKey in File2Launch:
            #lets launch the idf file creation process using the listed created above
            if MultipleFiles:
                if CurrentSimDir != File2Launch[ListKey][0]['SimDir']:
                    if CaseChoices['Verbose']: print('Idf input files under process using '+
                                                     os.path.basename(File2Launch[ListKey][0]['SimDir']))
            if not MultipleFiles and CaseChoices['Verbose']: print('Idf input files under process...')
            CurrentSimDir = File2Launch[ListKey][0]['SimDir']
            pool = mp.Pool(processes=int(nbcpu))
            for nbBuild in File2Launch[ListKey]:
                pool.apply_async(CB_OAT.LaunchOAT, args=(CaseChoices,CurrentSimDir,nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath))
            pool.close()
            pool.join()
            # now that all the files are created, we can aggregate all the log files into a single one.
            os.chdir(CurrentPath)
            GrlFct.CleanUpLogFiles(CurrentSimDir)
            # lest create the pool and launch the simulations
            if CaseChoices['Verbose']: print(
                        'Simulations under process for ' + os.path.basename(CurrentSimDir))
            file2run = LaunchSim.initiateprocess(CurrentSimDir)
            pool = mp.Pool(processes=int(nbcpu))
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], CurrentSimDir, epluspath,CaseChoices['API'],CaseChoices['Verbose']), callback=giveReturnFromPool)
            pool.close()
            pool.join()
            GrlFct.AppendLogFiles(CurrentSimDir,CaseChoices['BldIDKey'])
    elif CaseChoices['CreateFMU']:
        # now that all the files are created, we can aggregate all the log files into a single one.
        os.chdir(CurrentPath)
        GrlFct.CleanUpLogFiles(SimDir)
        #the FMU are not taking advantage of the parallel computing option yet
        for ListKey in File2Launch:
            for nbBuild in File2Launch[ListKey]:
                CB_OAT.LaunchOAT(CaseChoices,SimDir,nbBuild['keypath'],nbBuild['nbBuild'],[1],0,pythonpath)
    if not File2Launch[0] and CaseChoices['Verbose'] and CaseChoices['NbRuns']==1:  print('[Info] All asked simulations are already done and results available...refreshfolder to remove those')
    if CaseChoices['Verbose']: print('[Process Finished] runMUBES.py ended successfully')
