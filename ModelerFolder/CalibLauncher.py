# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
# #add the required path for geomeppy special branch
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add the reauired path for all the above folder
sys.path.append('..')

import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.LaunchSim as LaunchSim
import CoreFiles.CaseBuilder_OAT as CB_OAT
import multiprocessing as mp
from ReadResults import Utilities
import CoreFiles.CalibUtilities as CalibUtil
import pickle
import numpy as np

if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART  (choices from the modeler)   ########################################################
######################################################################################################################
#The Modeler have to fill in the following parameter to define his choices

# CaseName = 'String'                   #name of the current study (the ouput folder will be renamed using this entry)
# BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
#                                       geojsonfile), if empty, all building in the geojson file will be considered
# VarName2Change = ['String','String']  #list of strings: Variable names (same as Class Building attribute, if different
#                                       see LaunchProcess 'for' loop for examples)
# Bounds = [[x1,y1],[x2,y2]]            #list of list of 2 values  :bounds in which the above variable will be allowed to change
# BoundLim                              #same as bound. as the process enlarge to boudnaries in order to enalrge chances to catches
                                        #combitions, some other limits or to be defined in order to avoid unrealistics parameters.
# NbRuns = 1000                         #number of run to launch for each building (all VarName2Change will have automotaic
#                                       allocated value (see sampling in LaunchProcess)
# CPUusage = 0.7                        #factor of possible use of total CPU for multiprocessing. If only one core is available,
#                                       this value should be 1
# CreateFMU = False / True             #True = FMU are created for each building selected to be computed in BuildNum
#                                       #no simulation will be run but the folder CaseName will be available for the FMUSimPlayground.py
# CorePerim = False / True             #True = create automatic core and perimeter zonning of each building. This options increases in a quite
#                                       large amount both building process and simulation process.
#                                       It can used with either one zone per floor or one zone per heated or none heated zone
#                                       building will be generated first, all results will be saved in one single folder
# FloorZoning = False / True            True = thermal zoning will be realized for each floor of the building, if false, there will be 1 zone
#                                       for the heated volume and, if present, one zone for the basement (non heated volume
# PathInputFile = 'String'              #Name of the PathFile containing the paths to the data and to energyplus application (see ReadMe)
# OutputsFile = 'String'               #Name of the Outfile with the selected outputs wanted and the associated frequency (see file's template)
# ZoneOfInterest = 'String'             #Text file with Building's ID that are to be considered withoin the BuildNum list, if '' than all building in BuildNum will be considered

    with open('Ham2Simu4Calib_Last.txt') as f: #'Ham2Simu4Calib_Last2complete.txt') as f: #
        FileLines = f.readlines()
    Bld2Sim = []
    for line in FileLines:
        Bld2Sim.append(int(line))

    CaseName = 'monthlybasisnewbis'
    BuildNum = Bld2Sim
    VarName2Change = ['AirRecovEff','IntLoadCurveShape','wwr','EnvLeak','setTempLoL','AreaBasedFlowRate','WindowUval','WallInsuThick','RoofInsuThick']
    Bounds = [[0.5,0.9],[1,5],[0.2,0.4],[0.5,1.6],[18,22],[0.35,1],[0.7,2],[0.1,0.3],[0.2,0.4]]
    BoundLim = [[0,1],[0.9,9],[0.05,0.7],[0.2,4],[15,25],[0.2,2],[0.5,4],[0.05,0.9],[0.05,0.9]]
    NbRuns = 200    #this is the number of runs for the frist step, it will be repeated so should not be to large, neither too small
    CPUusage = 0.8
    CreateFMU = False
    CorePerim = False
    FloorZoning = True
    PathInputFile = 'HammarbyLast.txt'
    OutputsFile = 'Outputs.txt'
    ZoneOfInterest = ''
    CalibBasis = 'MonthlyBasis'#'WeeklyBasis'#'YearlyBasis' #'WeeklyBasis'#
    REMax = 20

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART  (nothing should be changed hereafter)   ############################
######################################################################################################################
    if NbRuns>1:
        SepThreads = True
        if CreateFMU:
            print('###  INPUT ERROR ### ' )
            print('/!\ It is asked to ceate FMUs but the number of runs for each building is above 1...')
            print('/!\ Please, check you inputs as this case is not allowed yet')
            sys.exit()
    else:
        SepThreads = False
    nbcpu = max(mp.cpu_count() * CPUusage, 1)
    # reading the pathfiles and the geojsonfile
    keyPath = GrlFct.readPathfile(PathInputFile)
    epluspath = keyPath['epluspath']
    pythonpath = keyPath['pythonpath'] #this is needed only if processes are launch in terminal as it could be an options instead of staying in python environnement
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)

    #check of the building to run
    BuildNum2Launch = [i for i in range(len(DataBaseInput['Build']))]
    if BuildNum:
        BuildNum2Launch = BuildNum
    if os.path.isfile(os.path.join(os.getcwd(), ZoneOfInterest)):
        NewBuildNum2Launch = []
        Bld2Keep = GrlFct.ReadZoneOfInterest(os.path.join(os.getcwd(), ZoneOfInterest), keyWord='50A Uuid')
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            if Bld.properties['50A_UUID'] in Bld2Keep and bldNum in BuildNum2Launch:
                NewBuildNum2Launch.append(bldNum)
        BuildNum2Launch = NewBuildNum2Launch
    if not BuildNum2Launch:
        print('Sorry, but no building matches with the requirements....Please, check your ZoneOfInterest')
    else:
        #all argument are packed in a dictionnarie, as parallel process is used, the arguments shall be strictly kept for each
        #no moving object of dictionnary values that should change between two processes.
        FigCenter = []
        CurrentPath = os.getcwd()
        MainInputs = {}
        MainInputs['CorePerim'] = CorePerim
        MainInputs['FloorZoning'] = FloorZoning
        MainInputs['CreateFMU'] = CreateFMU
        MainInputs['TotNbRun'] = NbRuns
        MainInputs['OutputsFile'] = OutputsFile
        MainInputs['VarName2Change'] = VarName2Change
        MainInputs['PathInputFiles'] = PathInputFile
        MainInputs['DataBaseInput'] = DataBaseInput
        File2Launch = {'nbBuild' : []}
        for idx,nbBuild in enumerate(BuildNum2Launch):
            NbRun = NbRuns
            #First, lets create the folder for the building and simulation processes
            SimDir = GrlFct.CreateSimDir(CurrentPath,CaseName,SepThreads,nbBuild,idx,Refresh=False)
            #a sample of parameter is generated is needed
            ParamSample =  GrlFct.SetParamSample(SimDir, NbRun, VarName2Change, Bounds,SepThreads)
            if idx<len(DataBaseInput['Build']):
                Finished = False
                idx_offset = 0
                while not Finished:
                    # lets check if this building is already present in the folder (means Refresh = False in CreateSimDir() above)
                    if not os.path.isfile(os.path.join(SimDir, ('Building_' + str(nbBuild) + '_template.idf'))):
                        # there is a need to launch the first one that will also create the template for all the others
                        MainInputs['FirstRun'] = True
                        CB_OAT.LaunchOAT(MainInputs, SimDir, nbBuild, ParamSample[0, :], 0, pythonpath)
                    # lets check whether all the files are to be run or if there's only some to run again
                    NewRuns = []
                    for i in range(NbRun):
                        if not os.path.isfile(
                                os.path.join(SimDir, ('Building_' + str(nbBuild) + 'v' + str(i+idx_offset) + '.idf'))):
                            NewRuns.append(i)
                    MainInputs['FirstRun'] = False
                    pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                    for i in NewRuns:#range(1,NbRun):
                        pool.apply_async(CB_OAT.LaunchOAT, args=(MainInputs,SimDir,nbBuild,ParamSample[i+idx_offset, :],i+idx_offset,pythonpath))
                    pool.close()
                    pool.join()

                    file2run = LaunchSim.initiateprocess(SimDir)
                    pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                    for i in range(len(file2run)):
                        pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath))
                    pool.close()
                    pool.join()
                    # once every run has been computed, lets get the matche and compute the covariance depending on the number of matches
                    extraVar = ['nbAppartments', 'ATempOr', 'SharedBld', 'height', 'StoreyHeigth', 'nbfloor',
                                'BlocHeight',
                                'BlocFootprintArea', 'BlocNbFloor',
                                'HeatedArea', 'AreaBasedFlowRate',
                                'NonHeatedArea', 'Other']
                    Res = Utilities.GetData(os.path.join(SimDir, 'Sim_Results'), extraVar)
                    os.chdir(CurrentPath)
                    ComputfFilePath = os.path.normcase(
                        'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration')
                    with open(os.path.join(ComputfFilePath, 'Building_' + str(nbBuild) + '_Meas.pickle'),
                              'rb') as handle:
                        Meas = pickle.load(handle)
                    Matches20 = CalibUtil.getMatches(Res, Meas, VarName2Change, CalibBasis,ParamSample,REMax = 20)
                    Matches10 = CalibUtil.getMatches(Res, Meas, VarName2Change, CalibBasis, ParamSample, REMax=10)
                    Matches5 = CalibUtil.getMatches(Res, Meas, VarName2Change, CalibBasis, ParamSample, REMax=5)
                    if len(Matches5[CalibBasis][VarName2Change[0]]) > 30:
                        Matches = Matches5
                    elif len(Matches10[CalibBasis][VarName2Change[0]]) > 30:
                        Matches = Matches10
                    else:
                        Matches = Matches20
                    try:
                        print(len(Matches5[CalibBasis][VarName2Change[0]]), REMax)
                        if len(ParamSample[:, 0]) >= 2000 or len(Matches5[CalibBasis][VarName2Change[0]]) > 100:
                            Finished = True
                        else:
                            print('New runs loop')
                            if len(Matches[CalibBasis][VarName2Change[0]]) > 10:
                                NbRun = 100
                                try:
                                    NewSample = CalibUtil.getCovarCalibratedParam(Matches[CalibBasis], VarName2Change, NbRun,
                                                                        BoundLim)
                                    print('Covariance worked !')
                                except:
                                    Bounds = CalibUtil.getNewBounds(Bounds, BoundLim)
                                    NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun)
                            else:
                                Bounds = CalibUtil.getNewBounds(Bounds, BoundLim)
                                NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun)
                            idx_offset = len(ParamSample[:, 0])
                            ParamSample = np.concatenate((ParamSample, NewSample))
                            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
                            with open(Paramfile, 'wb') as handle:
                                pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)
                    except:
                        print('No matches at all from now...')
                        if len(ParamSample[:, 0]) >= 2000:
                            Finished = True
                        else:
                            Bounds = CalibUtil.getNewBounds(Bounds, BoundLim)
                            NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun)
                            idx_offset = len(ParamSample[:, 0])
                            ParamSample = np.concatenate((ParamSample, NewSample))
                            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
                            with open(Paramfile, 'wb') as handle:
                                pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)

        Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
        with open(Paramfile, 'wb') as handle:
            pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)



