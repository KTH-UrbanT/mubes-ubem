# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
sys.path.append(os.path.dirname(os.getcwd()))
#add needed packages
import pickle#5 as pickle
import copy
import shutil
#add scripts from the project as well
sys.path.append("..")
import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.LaunchSim as LaunchSim
from BuildObject.DB_Building import BuildingList
import BuildObject.DB_Data as DB_Data
import multiprocessing as mp
from subprocess import check_call
from ReadResults import Utilities
from scipy import stats, linalg
from SALib.sample import latin
import numpy as np

def SetParamSample(SimDir,nbruns,VarName2Change,Bounds):

    #the parameter are constructed. the oupute gives a matrix ofn parameter to change with nbruns values to simulate
    Paramfile = os.path.join(SimDir,'ParamSample.pickle')
    if SepThreads:
        Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
        if os.path.isfile(Paramfile):
            with open(Paramfile, 'rb') as handle:
                ParamSample = pickle.load(handle)
        else:
            ParamSample = GrlFct.getParamSample(VarName2Change,Bounds,nbruns)
            if nbruns>1:
                with open(Paramfile, 'wb') as handle:
                    pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        Paramfile = os.path.join(SimDir,'ParamSample.pickle')
        if os.path.isfile(Paramfile):
            with open(Paramfile, 'rb') as handle:
                ParamSample = pickle.load(handle)
        else:
            ParamSample = GrlFct.getParamSample(VarName2Change, Bounds, nbruns)
            if nbruns > 1:
                with open(Paramfile, 'wb') as handle:
                    pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return ParamSample

def LaunchOAT(MainInputs,ParamVal,currentRun):
    print('Launched')
    # lets prepare the commande lines
    virtualenvline = os.path.normcase('C:\\Users\\xav77\Envs\\UBEMGitTest\Scripts\\python.exe')
    # virtualenvline = virtualenvline+'\n'

    scriptpath = os.path.normcase('C:\\Users\\xav77\Documents\FAURE\prgm_python\\UrbanT\Eplus4Mubes\MUBES_UBEM\CoreFiles')
    cmdline = [virtualenvline, os.path.join(scriptpath, 'CaseBuilder_OAT.py')]
    for key in MainInputs.keys():
        cmdline.append('-'+key)
        if type(MainInputs[key]) == str:
            cmdline.append(MainInputs[key])
        else:
            cmdline.append(str(MainInputs[key]))
    cmdline.append('-ParamVal')
    cmdline.append(str(ParamVal))
    cmdline.append('-currentRun')
    cmdline.append(str(currentRun))
    # cmdline = [virtualenvline, os.path.join(scriptpath, 'CaseBuilder_OAT.py'), '-FirstRun', '-SimDir', SimDir,
    #            '-PathInputFiles', PathInputFile, '-nbcase', str(nbBuild),'-VarName2Change',VarName2Change,'-ParamVal',ParamVal]
    check_call(cmdline)#,stdout=open(os.devnull, "w"))

def getYearlyError(Res,NewMeas):
    #definition of the reference for comparison
    EPCHeatArea = Res['EPC_Heat']
    EPCHeat = [val*Res['ATemp'][0] for val in Res['EPC_Heat']]
    EPHeat = []
    for idx in range(len(Res['EP_Heat'])):
        Heat2treat = Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate']
        HeatPower = Utilities.Average(Heat2treat, int(len(Heat2treat) / 8760))
        try:
            Data2treat = Res['Other'][idx]['Data_Water Use Equipment Heating Rate']
            DHWPower = Utilities.Average(Data2treat, int(len(Data2treat) / 8760))
            EPHeat.append(sum([(val + DHWPower[i]) for i, val in enumerate(HeatPower)])/1000)
        except:
            EPHeat.append(sum([(val) for i, val in enumerate(HeatPower)])/1000)
    EPHeatArea = [val/Res['EP_Area'][0] for val in EPHeat]

    varx = [i for i in range(len(Res['SimNum']))]
    MeasArea = sum(NewMeas['EnergySurfRatio']) / NewMeas['Atemp.DHSurfRatio']
    Meas = sum(NewMeas['EnergySurfRatio'])
    error = [abs( val - Meas) / Meas * 100 for val in EPHeat]
    #Matche = [val for idx,val in enumerate(Res['SimNum']) if (abs(EPHeat[idx]-Meas)/Meas*100)<Relerror]
    return error,EPHeat

def getPeriodError(Res,NewMeas,idx,NbSample):
    #definition of the reference for comparison
    Heat2treat = Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate']
    HeatPower = Utilities.Average(Heat2treat, int(len(Heat2treat) / 8760))
    try:
        Data2treat = Res['Other'][idx]['Data_Water Use Equipment Heating Rate']
        DHWPower = Utilities.Average(Data2treat, int(len(Data2treat) / 8760))
        SimPower = [(val + DHWPower[i]) / Res['EP_Area'][idx] for i, val in enumerate(HeatPower)]
        SimPower = [(val + DHWPower[i]) for i, val in enumerate(HeatPower)]
    except:
        SimPower = [(val) / Res['EP_Area'][idx] for i, val in enumerate(HeatPower)]
        SimPower = [(val) for i, val in enumerate(HeatPower)]
    # MeasPower = [val * 1000 / NewMeas[Res['SimNum'][idx]]['Atemp.DHSurfRatio'] for val in
    #              NewMeas[Res['SimNum'][idx]]['EnergySurfRatio']]
    MeasPower = [val * 1000 for val in
                 NewMeas['EnergySurfRatio']]
    MeasPower = MeasPower[1:-23]
    #compute month csum
    nbHrperSample = int(8760/NbSample)
    SampleEnergySim = []
    SampleEnergyMeas = []
    SampleError = []
    SampleVal = []
    for i in range(NbSample):
        SampleEnergySim.append(sum(SimPower[i*nbHrperSample:nbHrperSample+i*nbHrperSample]))
        SampleEnergyMeas.append(sum(MeasPower[i * nbHrperSample:nbHrperSample + i * nbHrperSample]))
        SampleError.append(abs(SampleEnergySim[-1]-SampleEnergyMeas[-1])/SampleEnergyMeas[-1]*100)
        SampleVal.append(i+1)
    error = max(SampleError)
    error = (sum([(SampleEnergyMeas[i]-SampleEnergySim[i])**2 /NbSample for i in range(NbSample)])**0.5/np.mean(SampleEnergyMeas))*100
    return SampleError, error
    # if error<Relerror:
    #     return Res['SimNum'][idx]

def getMatches(Res,Meas,VarName2Change,CalibrationBasis):
    YearlyMatchSimIdx = []
    MonthlyMatchSimIdx = []
    WeeklyMatchSimIdx = []
    DailyMatchSimIdx = []
    if 'YearlyBasis' in CalibrationBasis:
        YearleError, EPHeat = getYearlyError(Res, Meas)
        YearlyMatchSimIdx = [idx for idx in range(len(Res['SimNum'])) if
                           YearleError[idx] < 5]  # number of simulation that gave matched results
        YearMatcherror = [val for val in YearleError if val < 5]

    elif 'MonthlyBasis' in CalibrationBasis:
        MonthlyMatcherror = []
        getmonthEr = []
        for idx in range(len(Res['SimNum'])):
            SampleEr,CVRMSEro = getPeriodError(Res, Meas, idx, 12)
            getmonthEr.append(SampleEr)
            if CVRMSEro <15:
                MonthlyMatchSimIdx.append(idx) #number of simulation that gave matched results
                MonthlyMatcherror.append(CVRMSEro)

    elif 'WeeklyBasis' in CalibrationBasis:
        WeeklyMatcherror = []
        getweekEr = []
        for idx in range(len(Res['SimNum'])):
            SampleEr, CVRMSEro = getPeriodError(Res, Meas, idx, 52)
            getweekEr.append(SampleEr)
            if CVRMSEro < 15:
                WeeklyMatchSimIdx.append(idx)  # number of simulation that gave matched results
                WeeklyMatcherror.append(CVRMSEro)

    elif 'DailyBasis' in CalibrationBasis:
        DailyMatcherror = []
        getdayEr = []
        for idx in range(len(Res['SimNum'])):
            SampleEr, CVRMSEro = getPeriodError(Res, Meas, idx, 365)
            getdayEr.append(SampleEr)
            if CVRMSEro < 15:
                DailyMatchSimIdx.append(idx) #number of simulation that gave matched results
                DailyMatcherror.append(CVRMSEro)

    YearlyMatchedParam = {}
    MonthlyMatchedParam = {}
    DailyMatchedParam = {}
    WeeklyMatchedParam= {}
    for idx, par in enumerate(VarName2Change):
        if YearlyMatchSimIdx:
            YearlyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in YearlyMatchSimIdx], idx]
        if MonthlyMatchSimIdx:
            MonthlyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in MonthlyMatchSimIdx], idx]
        if WeeklyMatchSimIdx:
            WeeklyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in WeeklyMatchSimIdx], idx]
        if DailyMatchSimIdx:
            DailyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in DailyMatchSimIdx], idx]

    return {'YearlyBasis' : YearlyMatchedParam,'MonthlyBasis' : MonthlyMatchedParam,'WeeklyBasis' : WeeklyMatchedParam,
            'DailyBasis' : DailyMatchedParam}

def getCovarCalibratedParam(Data,VarName2Change,nbruns,BoundLim):
        #if len(Data[VarName2Change[0]]) > 10:
            ParamSample = []
            for key in VarName2Change:
                ParamSample.append(Data[key])
            ParamSample = np.array(ParamSample)
            covariance_matrix = np.cov(ParamSample.transpose(), rowvar=False)
            problemnew = {
                'num_vars': len(VarName2Change),
                'names': VarName2Change,
                'bounds': [[0, 1]] * len(VarName2Change)
            }
            xx = latin.sample(problemnew, nbruns)
            # z = []
            # for i in range(xx.shape[1]):
            #     # but it is possible to transform xx values to a normal distribution by percent point function
            #     # eric.univ-lyon2.fr/~ricco/tanagra/fichiers/en_Tanagra_Calcul_P_Value.pdf
            #     xx[:, i] = stats.norm.ppf(xx[:, i], 0, 1)
            #     tmp = xx[:, i]
            #     z.append(tmp)
            # xx = np.array(z)  # this is used to change dimension array from n,m to m,n
            cholesky = False

            try: #cholesky:
                # Compute the Cholesky decomposition.
                c = linalg.cholesky(covariance_matrix, lower=True)
                print('cholesky worked!!')
            #else:
            except:
                # Compute the eigenvalues and eigenvectors.
                evals, evecs = linalg.eigh(covariance_matrix)
                evals = [val if val >0 else 0 for val in evals]
                # Construct c, so c*c^T = r.
                c = np.dot(evecs, np.diag(np.sqrt(evals)))

            # Convert the data to correlated random variables
            y = np.dot(c, xx.transpose())
            #y = xx

            if y.shape[0] != len(VarName2Change):
                y = y.transpose()

            # now we have the samples based on correlated data with provided but we need to transform them to
            # their real ranges example: temperature samples from -4 to 4 -> 19 to 22.
            y_transformed = []
            for i in range(len(y[:,0])):
                full_range = ParamSample[i, :].max()-ParamSample[i, :].min()
                y_transformed.append(np.interp(y[i], (y[i].min(), y[i].max()), (max(BoundLim[i][0],ParamSample[i, :].min()-0.1*full_range), min(BoundLim[i][1],ParamSample[i, :].max()+0.1*full_range))))
            Param2keep = list(np.array(y_transformed).transpose())

            return np.array(Param2keep)

def getNewBounds(Bounds,BoundLim):
    newBounds = []
    for idx, bd in enumerate(Bounds):
        newBounds.append(
                [max(bd[0] - 0.1 * (bd[1] - bd[0]),BoundLim[idx][0]), min(BoundLim[idx][1], bd[1] + 0.1 * (bd[1] - bd[0]))])
    return newBounds


if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART     ##################################################################################
######################################################################################################################
#The Modeler have to fill in the following parameter to define his choices

# CaseName = 'String'                   #name of the current study (the ouput folder will be renamed using this entry)
# BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
#                                       geojsonfile), if empty, all building in the geojson file will be considered
# VarName2Change = ['String','String']  #list of strings: Variable names (same as Class Building attribute, if different
#                                       see LaunchProcess 'for' loop for examples)
# Bounds = [[x1,y1],[x2,y2]]            #list of list of 2 values  :bounds in which the above variable will be allowed to change
# NbRuns = 1000                         #number of run to launch for each building (all VarName2Change will have automotaic
#                                       allocated value (see sampling in LaunchProcess)
# CPUusage = 0.7                        #factor of possible use of total CPU for multiprocessing. If only one core is available,
#                                       this value should be 1
# SepThreads = False / True             #True = multiprocessing will be run for each building and outputs will have specific
#                                       folders (CaseName string + number of the building. False = all input files for all
#                                       building will be generated first, all results will be saved in one single folder
#                                       This options is to be set to True only for several simulation over one building
# CreateFMU = False / True             #True = FMU are created for each building selected to be computed in BuildNum
#                                       #no simulation will be run but the folder CaseName will be available for the FMUSimPlayground.py
# CorePerim = False / True             #True = create automatic core and perimeter zonning of each building. This options increases in a quite
#                                       large amount both building process and simulation process.
#                                       It can used with either one zone per floor or one zone per heated or none heated zone
#                                       building will be generated first, all results will be saved in one single folder
# FloorZoning = False / True            True = thermal zoning will be realized for each floor of the building, if false, there will be 1 zone
#                                       for the heated volume and, if present, one zone for the basement (non heated volume
## PlotBuilding = False / True          #True = after each building (and before the zoning details (setZoneLevel) the building will
#                                       be plotted for viisuaal check of geometrie and thermal zoning. It include the shadings
# PathInputFile = 'String'              #Name of the PathFile containing the paths to the data and to energyplus application (see ReadMe)
# OutputsFile = 'String'               #Name of the Outfile with the selected outputs wanted and the associated frequency (see file's template)
# ZoneOfInterest = 'String'             #Text file with Building's ID that are to be considered withoin the BuildNum list, if '' than all building in BuildNum will be considered

    with open('Ham2Simu4Calib_Last2complete.txt') as f: #'Ham2Simu4Calib_Last.txt') as f:
        FileLines = f.readlines()
    Bld2Sim = []
    for line in FileLines:
        Bld2Sim.append(int(line))

    CaseName = 'CalibMonthly'
    BuildNum = Bld2Sim[12:]
    VarName2Change = ['AirRecovEff','IntLoadCurveShape','wwr','EnvLeak','setTempLoL','AreaBasedFlowRate','WindowUval','WallInsuThick','RoofInsuThick']
    Bounds = [[0.5,0.9],[1,5],[0.2,0.4],[0.5,1.6],[18,22],[0.35,1],[0.7,2],[0.1,0.3],[0.2,0.4]]
    BoundLim = [[0,1],[0,9],[0.05,0.7],[0.2,4],[15,27],[0.2,2],[0.5,4],[0.05,0.9],[0.05,0.9]]
    NbRuns = 200
    CPUusage = 0.8
    SepThreads = True
    CreateFMU = False
    CorePerim = False
    FloorZoning = True
    PlotBuilding = False
    PathInputFile = 'HammarbyLast.txt'#'Pathways_Template.txt'
    OutputsFile = 'Outputs.txt'
    ZoneOfInterest = ''
    CalibBasis = 'MonthlyBasis' #'YearlyBasis' #'MonthlyBasis' # 'WeeklyBasis' # 'DailyBasis'

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
######################################################################################################################

    # reading the pathfiles and the geojsonfile
    keyPath = GrlFct.readPathfile(PathInputFile)
    epluspath = keyPath['epluspath']
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
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

        FigCenter = []
        LogFile=[]
        CurrentPath = os.getcwd()



        done = False #artefcat for continuing a simulation tat has stoped
        for idx,nbBuild in enumerate(BuildNum2Launch):
            if nbBuild==12:
                done = True
                idx = 1
            #First, lets create the folder for the building and simulation processes
            SimDir,LogFile1 = GrlFct.CreateSimDir(CurrentPath,CaseName,SepThreads,nbBuild,idx,LogFile,Refresh=False)
            LogFile1.close() #this file was define by the olde way of doing things
            os.remove(os.path.join(SimDir, 'Build_' + str(nbBuild) + '_Logs.log'))
            Paramfile = os.path.join(os.path.dirname(SimDir), 'ParamSample.pickle')
            newpath = 'C:\\Users\\xav77\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration'
            ParamSample = SetParamSample(SimDir, NbRuns, VarName2Change, Bounds)
            if idx < len(DataBaseInput['Build']):
                Finished = False
                idx_offset = 0
                while not Finished:
                    if not done:
                        print(len(ParamSample[:, 0]))
                        #idx_offset=200
                        os.chdir(CurrentPath)
                        MainInputs = {}
                        MainInputs['FirstRun'] = True if idx_offset==0 else False
                        MainInputs['CorePerim'] = CorePerim
                        MainInputs['FloorZoning'] = FloorZoning
                        MainInputs['CreateFMU'] = CreateFMU
                        MainInputs['TotNbRun'] = NbRuns
                        MainInputs['OutputsFile'] = OutputsFile
                        MainInputs['SimDir'] = SimDir
                        MainInputs['PathInputFiles'] = PathInputFile
                        MainInputs['nbBuild'] = nbBuild
                        #MainInputs['ParamVal'] = ParamSample[0, :]
                        MainInputs['VarName2Change'] = VarName2Change
                        LaunchOAT(MainInputs,ParamSample[idx_offset, :],idx_offset)
                        MainInputs['FirstRun'] = False
                        TestObj = False
                        if TestObj:
                            for i in range(1,NbRuns):
                                LaunchOAT(MainInputs, ParamSample[i + idx_offset, :], i + idx_offset)
                        else:
                            nbcpu = max(mp.cpu_count() * CPUusage, 1)
                            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                            for i in range(1,NbRuns):
                                pool.apply_async(LaunchOAT, args=(MainInputs,ParamSample[i+idx_offset, :],i+idx_offset))
                            pool.close()
                            pool.join()

                        if SepThreads and not CreateFMU:
                            try:
                                LogFile.close()
                            except:
                                pass
                            file2run = LaunchSim.initiateprocess(SimDir)
                            newlist2run = []
                            for file in file2run:
                                if not os.path.isfile(os.path.join(SimDir, 'Sim_Results', file[:-4] + '.pickle')):
                                    newlist2run.append(file)
                            file2run = newlist2run
                            nbcpu = max(mp.cpu_count()*CPUusage,1)
                            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
                            for i in range(len(file2run)):
                                pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath))
                            pool.close()
                            pool.join()
                        #GrlFct.SaveCase(SimDir,SepThreads,CaseName,nbBuild)
                    # once every run has been comåputed, lets get the mateche and compute the covariance depending on the number of matches
                    extraVar = ['nbAppartments', 'ATempOr', 'SharedBld', 'height', 'StoreyHeigth', 'nbfloor',
                                'BlocHeight',
                                'BlocFootprintArea', 'BlocNbFloor',
                                'HeatedArea', 'AreaBasedFlowRate',
                                'NonHeatedArea', 'Other']
                    Res = Utilities.GetData(os.path.join(SimDir,'Sim_Results'), extraVar)
                    ComputfFilePath = os.path.normcase(
                        'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration')
                    with open(os.path.join(ComputfFilePath, 'Building_' + str(nbBuild) + '_Meas.pickle'),
                              'rb') as handle:
                        Meas = pickle.load(handle)
                    Matches = getMatches(Res, Meas, VarName2Change,CalibBasis)
                    try:
                        print(len(Matches[CalibBasis][VarName2Change[0]]))
                        if len(Matches[CalibBasis][VarName2Change[0]]) > 100 or len(ParamSample[:,0])>=1000:
                            Finished = True
                        else:
                            print('New runs loop')
                            if len(Matches[CalibBasis][VarName2Change[0]]) > 10:
                                try:
                                    NewSample = getCovarCalibratedParam(Matches[CalibBasis], VarName2Change, NbRuns,BoundLim)
                                    print('Covariance worked !')
                                except:
                                    Bounds = getNewBounds(Bounds,BoundLim)
                                    NewSample = GrlFct.getParamSample(VarName2Change,Bounds,NbRuns)
                            else:
                                Bounds = getNewBounds(Bounds,BoundLim)
                                NewSample = GrlFct.getParamSample(VarName2Change,Bounds,NbRuns)
                            idx_offset = len(ParamSample[:, 0])
                            ParamSample = np.concatenate((ParamSample, NewSample))
                            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
                            with open(Paramfile, 'wb') as handle:
                                pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)
                    except:
                        print('No matches at all from now...')
                        if len(ParamSample[:,0])>=1000:
                            Finished = True
                        else:
                            Bounds = getNewBounds(Bounds,BoundLim)
                            NewSample = GrlFct.getParamSample(VarName2Change,Bounds,NbRuns)
                            idx_offset = len(ParamSample[:, 0])
                            ParamSample = np.concatenate((ParamSample, NewSample))
                            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
                            with open(Paramfile, 'wb') as handle:
                                pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)


                    done = False
                Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
                with open(Paramfile, 'wb') as handle:
                    pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                print('All buildings in the input file have been treated.')
                print('###################################################')
                break
        # if choicies is done, once the building is finished parallel computing is launched for all files
        if not SepThreads and not CreateFMU:
            try:
                LogFile.close()
            except:
                pass
            file2run = LaunchSim.initiateprocess(SimDir)
            nbcpu = max(mp.cpu_count()*CPUusage,1)
            pool = mp.Pool(processes=int(nbcpu))  # let us allow 80% of CPU usage
            for i in range(len(file2run)):
                pool.apply_async(LaunchSim.runcase, args=(file2run[i], SimDir, epluspath))
            pool.close()
            pool.join()
            #GrlFct.SaveCase(SimDir, SepThreads,CaseName,nbBuild)
        #lets supress the path we needed for geomeppy
        # import matplotlib.pyplot as plt
        # plt.show()
        sys.path.remove(path2addgeom)