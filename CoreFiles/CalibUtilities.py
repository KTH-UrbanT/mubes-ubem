# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
from scipy import stats, linalg
from SALib.sample import latin
import numpy as np
from ReadResults import Utilities
import pickle
import CoreFiles.GeneralFunctions as GrlFct

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
    error = (sum([(SampleEnergyMeas[i]-SampleEnergySim[i])**2 /(NbSample-1) for i in range(NbSample)])**0.5/np.mean(SampleEnergyMeas))*100
    return SampleError, error
    # if error<Relerror:
    #     return Res['SimNum'][idx]

def getMatches(Res,Meas,VarName2Change,CalibrationBasis,ParamSample,REMax = 5, CVRMSMax = 15):
    YearlyMatchSimIdx = []
    MonthlyMatchSimIdx = []
    WeeklyMatchSimIdx = []
    DailyMatchSimIdx = []
    if 'YearlyBasis' in CalibrationBasis:
        YearleError, EPHeat = getYearlyError(Res, Meas)
        YearlyMatchSimIdx = [idx for idx in range(len(Res['SimNum'])) if
                           YearleError[idx] < REMax]  # number of simulation that gave matched results
        YearMatcherror = [val for val in YearleError if val < REMax]

    elif 'MonthlyBasis' in CalibrationBasis:
        MonthlyMatcherror = []
        getmonthEr = []
        for idx in range(len(Res['SimNum'])):
            SampleEr,CVRMSEro = getPeriodError(Res, Meas, idx, 12)
            getmonthEr.append(SampleEr)
            if CVRMSEro <CVRMSMax:
                MonthlyMatchSimIdx.append(idx) #number of simulation that gave matched results
                MonthlyMatcherror.append(CVRMSEro)

    elif 'WeeklyBasis' in CalibrationBasis:
        WeeklyMatcherror = []
        getweekEr = []
        for idx in range(len(Res['SimNum'])):
            SampleEr, CVRMSEro = getPeriodError(Res, Meas, idx, 52)
            getweekEr.append(SampleEr)
            if CVRMSEro < CVRMSMax:
                WeeklyMatchSimIdx.append(idx)  # number of simulation that gave matched results
                WeeklyMatcherror.append(CVRMSEro)

    elif 'DailyBasis' in CalibrationBasis:
        DailyMatcherror = []
        getdayEr = []
        for idx in range(len(Res['SimNum'])):
            SampleEr, CVRMSEro = getPeriodError(Res, Meas, idx, 365)
            getdayEr.append(SampleEr)
            if CVRMSEro < CVRMSMax:
                DailyMatchSimIdx.append(idx) #number of simulation that gave matched results
                DailyMatcherror.append(CVRMSEro)

    YearlyMatchedParam = {}
    MonthlyMatchedParam = {}
    DailyMatchedParam = {}
    WeeklyMatchedParam= {}
    for idx, par in enumerate(VarName2Change):
        YearlyMatchedParam[par] = []
        if YearlyMatchSimIdx:
            YearlyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in YearlyMatchSimIdx], idx]
        MonthlyMatchedParam[par] = []
        if MonthlyMatchSimIdx:
            MonthlyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in MonthlyMatchSimIdx], idx]
        WeeklyMatchedParam[par] = []
        if WeeklyMatchSimIdx:
            WeeklyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in WeeklyMatchSimIdx], idx]
        DailyMatchedParam[par] = []
        if DailyMatchSimIdx:
            DailyMatchedParam[par] = ParamSample[[Res['SimNum'][i] for i in DailyMatchSimIdx], idx]

    return {'YearlyBasis' : YearlyMatchedParam,'MonthlyBasis' : MonthlyMatchedParam,'WeeklyBasis' : WeeklyMatchedParam,
            'DailyBasis' : DailyMatchedParam}

def getCovarCalibratedParam(Data, VarName2Change, nbruns, BoundLim):
    # if len(Data[VarName2Change[0]]) > 10:
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

    try:  # cholesky:
        # Compute the Cholesky decomposition.
        c = linalg.cholesky(covariance_matrix, lower=True)
        print('cholesky worked!!')
    # else:
    except:
        # Compute the eigenvalues and eigenvectors.
        evals, evecs = linalg.eigh(covariance_matrix)
        evals = [val if val > 0 else 0 for val in evals]
        # Construct c, so c*c^T = r.
        c = np.dot(evecs, np.diag(np.sqrt(evals)))

    # Convert the data to correlated random variables
    y = np.dot(c, xx.transpose())
    # y = xx

    if y.shape[0] != len(VarName2Change):
        y = y.transpose()

    # now we have the samples based on correlated data with provided but we need to transform them to
    # their real ranges example: temperature samples from -4 to 4 -> 19 to 22.
    y_transformed = []
    for i in range(len(y[:, 0])):
        full_range = ParamSample[i, :].max() - ParamSample[i, :].min()
        y_transformed.append(np.interp(y[i], (y[i].min(), y[i].max()), (
        max(BoundLim[i][0], ParamSample[i, :].min() - 0.1 * full_range),
        min(BoundLim[i][1], ParamSample[i, :].max() + 0.1 * full_range))))
    Param2keep = list(np.array(y_transformed).transpose())

    return np.array(Param2keep)

def getNewBounds(Bounds,BoundLim):
    newBounds = []
    for idx, bd in enumerate(Bounds):
        newBounds.append(
                [max(bd[0] - 0.1 * (bd[1] - bd[0]),BoundLim[idx][0]), min(BoundLim[idx][1], bd[1] + 0.1 * (bd[1] - bd[0]))])
    return newBounds

def CompareSample(Finished,idx_offset, SimDir,CurrentPath,nbBuild,VarName2Change,CalibBasis,MeasPath,ParamSample,Bounds,BoundLim,NbRun):
    # once every run has been computed, lets get the matche and compute the covariance depending on the number of matches
    extraVar = ['nbAppartments', 'ATempOr', 'SharedBld', 'height', 'StoreyHeigth', 'nbfloor','BlocHeight','BlocFootprintArea','BlocNbFloor',
                'HeatedArea', 'AreaBasedFlowRate','NonHeatedArea', 'Other']
    Res = Utilities.GetData(os.path.join(SimDir, 'Sim_Results'), extraVar)
    os.chdir(CurrentPath)
    ComputfFilePath = os.path.normcase(MeasPath)
    #'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration')
    with open(os.path.join(ComputfFilePath, 'Building_' + str(nbBuild) + '_Meas.pickle'),
              'rb') as handle:
        Meas = pickle.load(handle)
    Matches20 = getMatches(Res, Meas, VarName2Change, CalibBasis, ParamSample, REMax=20)
    Matches10 = getMatches(Res, Meas, VarName2Change, CalibBasis, ParamSample, REMax=10)
    Matches5 = getMatches(Res, Meas, VarName2Change, CalibBasis, ParamSample, REMax=5)
    if len(Matches5[CalibBasis][VarName2Change[0]]) > 20:
        Matches = Matches5
        print('We are in the 5% range')
        print('Nb of matches at 5% is : ' + str(len(Matches5[CalibBasis][VarName2Change[0]])))
    elif len(Matches10[CalibBasis][VarName2Change[0]]) > 20:
        Matches = Matches10
        print('We are in the 10% range')
        print('Nb of matches at 10% is : ' + str(len(Matches10[CalibBasis][VarName2Change[0]])))
        print('Nb of matches at 5% is : ' + str(len(Matches5[CalibBasis][VarName2Change[0]])))
    else:
        Matches = Matches20
        print('We are in the 20% range')
        print('Nb of matches at 20% is : '+str(len(Matches20[CalibBasis][VarName2Change[0]])))
        print('Nb of matches at 10% is : ' + str(len(Matches10[CalibBasis][VarName2Change[0]])))
        print('Nb of matches at 5% is : ' + str(len(Matches5[CalibBasis][VarName2Change[0]])))
    try:
        if len(ParamSample[:, 0]) >= 2000 or len(Matches5[CalibBasis][VarName2Change[0]]) > 100:
            Finished = True
        elif len(ParamSample[:, 0]) >= 1000 and len(Matches5[CalibBasis][VarName2Change[0]]) < 10:
            Finished = True
        else:
            print('New runs loop')
            if len(Matches[CalibBasis][VarName2Change[0]]) > 10:
                try:
                    NewSample = getCovarCalibratedParam(Matches[CalibBasis], VarName2Change, NbRun,
                                                                  BoundLim)
                    print('Covariance worked !')
                except:
                    print('Covariance did not work...')
                    Bounds = getNewBounds(Bounds, BoundLim)
                    NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun)
            else:
                Bounds = getNewBounds(Bounds, BoundLim)
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
            Bounds = getNewBounds(Bounds, BoundLim)
            NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun)
            idx_offset = len(ParamSample[:, 0])
            ParamSample = np.concatenate((ParamSample, NewSample))
            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
            with open(Paramfile, 'wb') as handle:
                pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return Finished,idx_offset,ParamSample

if __name__ == '__main__' :
    print('CalibUtilities.py')