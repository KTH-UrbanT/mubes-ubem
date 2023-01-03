# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
from scipy import stats, linalg
#from SALib.sample import latin
import numpy as np
import outputs.output_utilities as Utilities
import pickle
import core.GeneralFunctions as GrlFct
import openturns as ot
ot.ResourceMap.SetAsBool("ComposedDistribution-UseGenericCovarianceAlgorithm", True)

def getYearlyError(Res,NewMeas):
    #definition of the reference for comparison
    # EPCHeatArea = Res['EPC_Heat']
    # EPCHeat = [val*Res['ATemp'][0] for val in Res['EPC_Heat']]
    EPHeat = []
    for idx in range(len(Res['EP_Heat'])):
        Heat2treat = Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate']
        HeatPower = Utilities.Average(Heat2treat, int(len(Heat2treat) / 8760))
        try:
            if 'Data_Total DHW Heating Power' in Res['Other'][idx].keys():
                Data2treat = Res['Other'][idx]['Data_Total DHW Heating Power']
            else:
                Data2treat = Res['Other'][idx]['Data_Water Use Equipment Heating Rate']
            DHWPower = Utilities.Average(Data2treat, int(len(Data2treat) / 8760))
            EPHeat.append(sum([(val + DHWPower[i]) for i, val in enumerate(HeatPower)])/1000)
        except:
            EPHeat.append(sum([(val) for i, val in enumerate(HeatPower)])/1000)

    Meas = sum(NewMeas)
    error = [( val - Meas) / Meas * 100 for val in EPHeat]
    return error,EPHeat

def getPeriodError(Res,NewMeas,idx,NbSample):
    #definition of the reference for comparison
    Heat2treat = Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate']
    HeatPower = Utilities.Average(Heat2treat, int(len(Heat2treat) / 8760))
    try:
        if 'Data_Total DHW Heating Power' in Res['Other'][idx].keys():
            Data2treat = Res['Other'][idx]['Data_Total DHW Heating Power']
        else:
            Data2treat = Res['Other'][idx]['Data_Water Use Equipment Heating Rate']
        DHWPower = Utilities.Average(Data2treat, int(len(Data2treat) / 8760))
        SimPower = [(val + DHWPower[i]) for i, val in enumerate(HeatPower)]
    except:
        SimPower = [(val) for i, val in enumerate(HeatPower)]
    MeasPower = [val * 1000 for val in
                 NewMeas]
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
    error = (sum([(SampleEnergyMeas[i]-SampleEnergySim[i])**2 /(NbSample-1) for i in range(NbSample)])**0.5/np.mean(SampleEnergyMeas))*100
    return SampleError, error


def getErrorMatches(Res,Meas,CalibrationBasis):
    Error = []
    if 'YearlyBasis' in CalibrationBasis:
        Error, EPHeat = getYearlyError(Res, Meas)

    elif 'MonthlyBasis' in CalibrationBasis:
        for idx in range(len(Res['SimNum'])):
            SampleEr,CVRMSEro = getPeriodError(Res, Meas, idx, 12)
            Error.append(CVRMSEro)

    elif 'WeeklyBasis' in CalibrationBasis:
        for idx in range(len(Res['SimNum'])):
            SampleEr, CVRMSEro = getPeriodError(Res, Meas, idx, 52)
            Error.append(CVRMSEro)

    elif 'DailyBasis' in CalibrationBasis:
        for idx in range(len(Res['SimNum'])):
            SampleEr, CVRMSEro = getPeriodError(Res, Meas, idx, 365)
            Error.append(CVRMSEro)
    return Error

def getGoodParamList(Error,CalibBasis, VarName2Change, ParamSample, REMax=5, CVRMSMax = 15):
    Matches = {}
    Criteria = CVRMSMax
    if 'YearlyBasis' in CalibBasis:
        Criteria = REMax
    for idx,key in enumerate(VarName2Change):
        Matches[key] = [ParamSample[x,idx] for x,val in enumerate(Error) if abs(val) < Criteria]
    return Matches

def getOpenTurnsCorrelated(Data, VarName2Change, nbruns, BoundLim):
    ##################NO MORE USED##########################
    # this is taken form https://se.mathworks.com/matlabcentral/fileexchange/56384-lhsgeneral-pd-correlation-n
    # and implemented in python by a proposeal in https://openturns.discourse.group/t/generate-multivariate-joint-distribution/182/3
    ParamSample = []
    pd = []
    for idx,key in enumerate(VarName2Change):
        ParamSample.append(Data[key])
        full_range = BoundLim[idx][1] - BoundLim[idx][0]
        pd.append(ot.Uniform(max(BoundLim[idx][0],Data[key].min() - 0.1*full_range),
                                min(BoundLim[idx][1],Data[key].max() + 0.1*full_range)))
    ParamSample = np.array(ParamSample)
    #pd = [ot.Normal(0.0, 20.0), ot.Triangular(0.0, 100.0, 150.0)]
    covMat = np.cov(ParamSample.transpose(), rowvar=False)
    correlation = ot.CorrelationMatrix(idx+1,[float(val) for val in list(np.reshape(covMat, ((idx+1)**2, 1)))] )
    n = nbruns
    return np.array(lhsgeneral(pd, correlation, n))

def getOpenTurnsCorrelatedFromSample(Data, VarName2Change, nbruns, BoundLim):
    ParamSample = []
    for idx, key in enumerate(VarName2Change):
        ParamSample.append(Data[key])
    ParamSample = np.array(ParamSample)
    data = ot.Sample(ParamSample.transpose())
    # Identify the associated normal copula
    copula = ot.NormalCopulaFactory().build(data)
    # Identify the marginal distributions
    pd = [ot.HistogramFactory().build(data.getMarginal(i)) for i in range(data.getDimension())]
    # Build the joint distribution
    dist = ot.ComposedDistribution(pd, copula)
    # Generate a new sample
    correlatedSamples = dist.getSample(nbruns)
    #R = correlatedSamples.computeLinearCorrelation()
    return np.array(correlatedSamples)

def lhsgeneral(pd, correlation, n):
    ##################NO MORE USED##########################
    dim = len(pd)
    RStar = correlation
    unifND = [ot.Uniform(0.0, 1.0)]*dim
    normND = [ot.Normal(0.0, 1.0)]*dim
    lhsDOE = ot.LHSExperiment(ot.ComposedDistribution(unifND), n)
    x = lhsDOE.generate()
    independent_sample = ot.MarginalTransformationEvaluation(unifND, normND)(x)
    R = independent_sample.computeLinearCorrelation()
    P = RStar.computeCholesky()
    Q = R.computeCholesky()
    M = P * Q.solveLinearSystem(ot.IdentityMatrix(dim))
    lin = ot.LinearEvaluation([0.0]*dim, [0.0]*dim, M.transpose())
    dependent_sample = lin(independent_sample)
    transformed_sample = ot.MarginalTransformationEvaluation(normND, pd)(dependent_sample)
    return transformed_sample

def getCovarCalibratedParam(Data, VarName2Change, nbruns, BoundLim):
    ##################NO MORE USED##########################
    # the method below follows the one describe in :
    # https://scipy-cookbook.readthedocs.io/items/CorrelatedRandomSamples.html
    # with the exception that as we on't have the former distribution type, the new sample are kept uniform
    # this should be enhanced further
    ParamSample = []
    for key in VarName2Change:
        ParamSample.append(Data[key])
    ParamSample = np.array(ParamSample)
    RStar = np.cov(ParamSample.transpose(), rowvar=False)
    problemnew = {
        'num_vars': len(VarName2Change),
        'names': VarName2Change,
        'bounds': [[0, 1]] * len(VarName2Change)
    }
    xx = latin.sample(problemnew, nbruns)
    z = []
    for i in range(xx.shape[1]):
        tmp = stats.norm.ppf(xx[:, i], 0, 1)
        z.append(tmp)
    xx = np.array(z)  # this is used to change dimension array from n,m to m,n
    P = linalg.cholesky(RStar, lower=True)
    x_xcorrelated = np.dot(P,xx)
    y = stats.norm.cdf(x_xcorrelated)

    if y.shape[0] != len(VarName2Change):
        y = y.transpose()

    # now we have the samples based on correlated data with provided but we need to transform them to
    # their real ranges example: temperature samples from -4 to 4 -> 19 to 22.
    y_transformed = []
    for i in range(len(y[:, 0])):
        #full_range = ParamSample[i, :].max() - ParamSample[i, :].min()
        full_range = BoundLim[i][1]-BoundLim[i][0]
        y_transformed.append(np.interp(y[i], (y[i].min(), y[i].max()), (
        max(BoundLim[i][0], ParamSample[i, :].min() - 0.1 * full_range),
        min(BoundLim[i][1], ParamSample[i, :].max() + 0.1 * full_range))))

    Param2keep =  np.array(y_transformed)
    return Param2keep.transpose()

def getBootStrapedParam(Data, VarName2Change, nbruns, BoundLim):
    ##################NO MORE USED##########################
    import openturns as ot
    ParamSample = []
    NormalizedParam = []
    for key in VarName2Change:
        ParamSample.append(Data[key])
        NormalizedParam.append((Data[key]-Data[key].min())/(Data[key].max()-Data[key].min()))
    ParamSample = np.array(ParamSample).transpose()
    NormalizedParam = np.array(NormalizedParam).transpose()
    BottObject = ot.BootstrapExperiment(NormalizedParam)
    NewSampleAsArray = []
    finished = False
    while not finished:
        NewSample = BottObject.generate()
        try:
            if not NewSampleAsArray:
                NewSampleAsArray = np.array(list(NewSample))
        except:
            NewSampleAsArray = np.append(NewSampleAsArray,np.array(list(NewSample)),axis = 0)
        if NewSampleAsArray.shape[0]>nbruns:
            finished = True
    y = np.array([NewSampleAsArray[i,:] for i in np.random.randint(0, NewSampleAsArray.shape[0], nbruns)])
    y_transformed = []
    for i in range(y.shape[1]):
        #full_range = ParamSample[i, :].max() - ParamSample[i, :].min()
        full_range = BoundLim[i][1]-BoundLim[i][0]
        y_transformed.append(np.interp(y[:,i], (y[:,i].min(), y[:,i].max()), (
        max(BoundLim[i][0], ParamSample[:, i].min() - 0.1 * full_range),
        min(BoundLim[i][1], ParamSample[:, i].max() + 0.1 * full_range))))
    Param2keep =  np.array(y_transformed)
    return Param2keep.transpose()

def getNewBounds(Bounds,BoundLim):
    newBounds = []
    for idx, bd in enumerate(Bounds):
        newBounds.append(
                [max(bd[0] - 0.1 * (bd[1] - bd[0]),BoundLim[idx][0]), min(BoundLim[idx][1], bd[1] + 0.1 * (bd[1] - bd[0]))])
    return newBounds

def getTheWinners(VarName2Change,Matches20, Matches10, Matches5):
    if len(Matches5[VarName2Change[0]]) > 20:
        Matches = Matches5
    elif len(Matches10[VarName2Change[0]]) > 20:
        Matches = Matches10
    else:
        Matches = Matches20
    return Matches, len(Matches[VarName2Change[0]])

def getTheWeightedWinners(VarName2Change,Matches20, Matches10, Matches5):
    Matches = {}
    #the number of winners taken for defning the sample size is kept as for the non weighted function
    if len(Matches5[VarName2Change[0]]) > 20:
        nbwinners = len(Matches5[VarName2Change[0]])
        for key in VarName2Change:
            Matches[key] = np.array(Matches5[key])
    elif len(Matches10[VarName2Change[0]]) > 20:
        for key in VarName2Change:
            Matches[key] = np.array(Matches10[key])
            for weigth in range(2):
                Matches[key] = np.append(Matches[key], Matches5[key])
        nbwinners = max(10,len(Matches10[VarName2Change[0]])/2)
    else:
        nbwinners = 10 #len(Matches20[CalibBasis][VarName2Change[0]]) this way, there will be half of the next sample
        for key in VarName2Change:
            Matches[key] = np.array(Matches20[key])
            # a weight of 3 is applied to 10% matches (the good ones are also in 20% so there is the need to add only 2)
            for weigth in range(2):
                Matches[key] = np.append(Matches[key], Matches10[key])
            # a weight of 5 is applied to 5% matches (the good ones are also in 20% and 10% so there is the need to add only 3)
            for weigth in range(3):
                Matches[key] = np.append(Matches[key], Matches5[key])
    return Matches, int(nbwinners)

def CompareSample(Finished,idx_offset, SimDir,CurrentPath,nbBuild,VarName2Change,CalibBasis,MeasPath,ParamSample,
                  Bounds,BoundLim,ParamMethods,NbRun,BldIDKey):
    # once every run has been computed, lets get the matche and compute the covariance depending on the number of matches
    extraVar = ['nbAppartments', 'ATempOr', 'SharedBld', 'height', 'StoreyHeigth', 'nbfloor','BlocHeight','BlocFootprintArea','BlocNbFloor',
                'HeatedArea', 'AreaBasedFlowRate','NonHeatedArea', 'Other']
    Res = Utilities.GetData(os.path.join(SimDir, 'Sim_Results'), extraVar)
    os.chdir(CurrentPath)
    MeasureFile = os.path.join(os.path.normcase(MeasPath),str(BldIDKey)+'.txt')
    #Measurement are here considered from a single raw file with at least 8670 values that has the building's Id name
    with open(MeasureFile, 'r') as file:
        Lines = file.readlines()
    Meas = [float(val) for val in Lines]

    Error = getErrorMatches(Res, Meas, CalibBasis)
    Matches20 = getGoodParamList(Error,CalibBasis, VarName2Change, ParamSample, REMax=20, CVRMSMax = 30)
    Matches10 = getGoodParamList(Error,CalibBasis, VarName2Change, ParamSample, REMax=10, CVRMSMax = 20)
    Matches5 = getGoodParamList(Error, CalibBasis, VarName2Change, ParamSample, REMax=5, CVRMSMax=15)
    print('Nb of matches at 20% is : ' + str(len(Matches20[VarName2Change[0]])))
    print('Nb of matches at 10% is : ' + str(len(Matches10[VarName2Change[0]])))
    print('Nb of matches at 5% is : ' + str(len(Matches5[VarName2Change[0]])))
    #Matches, NbWinners = getTheWinners(VarName2Change,Matches20, Matches10, Matches5)
    Matches, NbWinners = getTheWeightedWinners(VarName2Change, Matches20, Matches10, Matches5)
    try:
        if len(ParamSample[:, 0]) >= 2000 or len(Matches5[VarName2Change[0]]) > 100:
            Finished = True
        elif len(ParamSample[:, 0]) >= 1000 and len(Matches5[VarName2Change[0]]) < 5:
            Finished = True
        else:
            print('New runs loop')
            if len(Matches[VarName2Change[0]]) > 10:
                try:
                    NBskewedRuns = min(NbRun,NbWinners+90)
                    print('Nd of skewed runs : '+str(NBskewedRuns))
                    NbNewRuns = NbRun-NBskewedRuns
                    #NewSample1 = getBootStrapedParam(Matches, VarName2Change, NBskewedRuns, BoundLim)
                    #NewSample1 = getOpenTurnsCorrelated(Matches, VarName2Change, NBskewedRuns, BoundLim)
                    NewSample1 = getOpenTurnsCorrelatedFromSample(Matches, VarName2Change, NBskewedRuns, BoundLim)
                    #NewSample1 = getCovarCalibratedParam(Matches, VarName2Change, NBskewedRuns, BoundLim)
                    if NbNewRuns > 0:
                        #lets make new bounds for non correlated sample, being in the same range as for correlated ones
                        openRange = 0
                        if len(Matches5[VarName2Change[0]]) < 10:
                            openRange = 1
                        ModifiedBounds = []
                        for i in range(len(NewSample1[0,:])):
                            fullRange = (BoundLim[i][1]-BoundLim[i][0])*openRange
                            ModifiedBounds.append([max(BoundLim[i][0], NewSample1[:, i].min() - 0.1*fullRange),
                                                   min(BoundLim[i][1], NewSample1[:, i].max() + 0.1*fullRange)])
                        NewSample2 = GrlFct.getParamSample(VarName2Change, ModifiedBounds, NbNewRuns,ParamMethods)
                        NewSample = np.append(NewSample1, NewSample2, axis=0)
                    else:
                        NewSample = NewSample1
                    print('Correlated Sample worked !')
                except:
                    print('Correlated Sample did not work...')
                    Bounds = getNewBounds(Bounds, BoundLim)
                    NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun,ParamMethods)
            else:
                Bounds = getNewBounds(Bounds, BoundLim)
                NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun,ParamMethods)
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
            NewSample = GrlFct.getParamSample(VarName2Change, Bounds, NbRun,ParamMethods)
            idx_offset = len(ParamSample[:, 0])
            ParamSample = np.concatenate((ParamSample, NewSample))
            Paramfile = os.path.join(SimDir, 'ParamSample.pickle')
            with open(Paramfile, 'wb') as handle:
                pickle.dump(ParamSample, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return Finished,idx_offset,ParamSample

if __name__ == '__main__' :
    print('CalibUtilities.py')