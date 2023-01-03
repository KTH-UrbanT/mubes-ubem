# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os, sys, platform
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add scripts from the project as well
sys.path.append("..")
from subprocess import check_call
from geomeppy import IDF
import pickle#5 as pickle
#import pickle5
import core.GeneralFunctions as GrlFct
from building_geometry.BuildingObject import BuildingList
from building_geometry.Filter4BldProcess import checkBldFilter
#import BuildObject.DB_Data as DB_Data
import re
import time

def LaunchOAT(MainInputs,SimDir,keypath,nbBuild,ParamVal,currentRun,pythonpath=[],BldObj=[],
              MakePlotOnly = False):
    #this function was made to enable either to launch a process in a seperate terminal or not, given a python path to a virtualenv
    #but if kept in seperate terminal, the inputfile needs to be read for each simulation...not really efficient,
    #thus, the first option, being fully in the same environment is used with the optionnal argument 'DataBaseInput'
    if not pythonpath:
        return LaunchProcess(SimDir, MainInputs['FirstRun'], MainInputs['NbRuns'], currentRun,keypath, nbBuild,
                      MainInputs['CorePerim'], MainInputs['FloorZoning'], ParamVal,MainInputs['VarName2Change'],
                      MainInputs['CreateFMU'],MainInputs['OutputsFile'],DataBaseInput = MainInputs['DataBaseInput'],
                    DebugMode = MainInputs['DebugMode'],MakePlotOnly = MakePlotOnly,Verbose = MainInputs['Verbose'])
    # if willing to launch each run in seperate terminals, all arguments must be given in text form and the pythonpath is required
    else:
        if platform.system() == "Windows":
            virtualenvline = os.path.join(pythonpath, "python.exe")
        else:
            virtualenvline = os.path.join(pythonpath, "python")
        scriptpath =os.path.join(os.path.dirname(os.getcwd()),'CoreFiles')
        cmdline = [virtualenvline, os.path.join(scriptpath, 'CaseBuilder_OAT.py')]
        for key in MainInputs.keys():
            cmdline.append('-'+key)
            if type(MainInputs[key]) == str:
                cmdline.append(MainInputs[key])
            else:
                cmdline.append(str(MainInputs[key]))

        for key in keypath.keys():
            cmdline.append('-'+key)
            if type(keypath[key]) == str:
                cmdline.append(keypath[key])
            else:
                cmdline.append(str(keypath[key]))

        cmdline.append('-SimDir')
        cmdline.append(str(SimDir))
        cmdline.append('-nbBuild')
        cmdline.append(str(nbBuild))
        cmdline.append('-ParamVal')
        cmdline.append(str(ParamVal))
        cmdline.append('-currentRun')
        cmdline.append(str(currentRun))
        check_call(cmdline,stdout=open(os.devnull, "w"))

def LaunchProcess(SimDir,FirstRun,TotNbRun,currentRun,keyPath,nbcase,CorePerim,FloorZoning,ParamVal,VarName2Change,
                  CreateFMU,OutputsFile,DataBaseInput = [], DebugMode = False,MakePlotOnly = False,Verbose = False):
    #This function builds the idf file, a log file is generated if the buildiung is run for the first time,
    #the idf file will be saved as well as the building object as a pickle. the latter could be commented as not required
    MainPath = os.getcwd()

    if not DataBaseInput:
        # Buildingobjects from reading the geojson file as input for further functions if not given as arguments
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    epluspath = keyPath['epluspath']
    os.chdir(SimDir)
    start = time.time()
    #Creating the log file for this building if it's his frist run
    if FirstRun:
        LogFile = open(os.path.join(SimDir, 'Build_'+str(nbcase)+'_Logs.log'), 'w')
        msg = 'Building ' + str(nbcase) + ' is starting\n'
        if Verbose: print(msg[:-1])
        GrlFct.Write2LogFile(msg,LogFile)
    else:
        LogFile = False

    #if its the first run of a pool for the same building, than only the simulation parameters and the building geometry will run.
    #a 'tewmplate file will be created and openned by the following runs to save the geometry construction process (as it is the longest one)
    if FirstRun:
        StudiedCase = BuildingList()
        #lets build the two main object we'll be playing with in the following : the idf and the building
        try:
            if DebugMode: startIniti = time.time()
            idf, building = GrlFct.appendBuildCase(StudiedCase, keyPath, nbcase, DataBaseInput, MainPath,LogFile,
                                               DebugMode = DebugMode,PlotOnly=MakePlotOnly)
        except:
            msg = '[Error] The Building Object Initialisation has failed...\n'
            if Verbose: print(msg[:-1])
            os.chdir(MainPath)
            if FirstRun:
                GrlFct.Write2LogFile(msg, LogFile)
                GrlFct.Write2LogFile('##############################################################\n', LogFile)
                return [], [], 'NOK'


        #Rounds of check if we continue with this building or not, see DB_Filter4Simulation.py if other filter are to add
        CaseOK,msg = checkBldFilter(building,LogFile,DebugMode = DebugMode)
        if not CaseOK:
            if Verbose: print(msg[:-1])
            os.chdir(MainPath)
            if FirstRun:
                GrlFct.Write2LogFile('##############################################################\n', LogFile)
                return building,idf, 'NOK'
        if DebugMode: GrlFct.Write2LogFile('[Time report] Building Initialisation phase : '+
                                           str(round(time.time()-startIniti,2))+' sec\n', LogFile)
        # The simulation parameters are assigned here
        if not MakePlotOnly:
            try: GrlFct.setSimLevel(idf, building)
            except:
                msg = '[Error] The SimLevel has failed...\n'
                if Verbose: print(msg[:-1])
                os.chdir(MainPath)
                if FirstRun:
                    GrlFct.Write2LogFile(msg, LogFile)
                    GrlFct.Write2LogFile('##############################################################\n', LogFile)

        # The geometry is assigned here
        try:
            if DebugMode: startIniti = time.time()
            GrlFct.setBuildingLevel(idf, building,LogFile,CorePerim,FloorZoning,DebugMode = DebugMode,ForPlots=MakePlotOnly)
            # end = time.time()
            # print('[Time Report] : The setBuildingLevel took : ',round(end-start,2),' sec')
        except:
            msg = '[Error] The setBuildingLevel failed...\n'
            if Verbose: print(msg[:-1])
            os.chdir(MainPath)
            if FirstRun:
                GrlFct.Write2LogFile(msg, LogFile)
                GrlFct.Write2LogFile('##############################################################\n', LogFile)
                return building,idf, 'NOK'
        if DebugMode: GrlFct.Write2LogFile('[Time report] Building level (geometry) phase : ' +
                                           str(round(time.time() - startIniti, 2)) + ' sec\n', LogFile)
        # if the number of run for one building is greater than 1 it means parametric simulation, a template file will be saved
        if TotNbRun>1 and not MakePlotOnly:
            Case = {}
            Case['BuildData'] = building
            idf.saveas('Building_' + str(nbcase) + '_template.idf')
            with open('Building_' + str(nbcase) + '_template.pickle', 'wb') as handle:
                pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        #for all but the first run, the template file and the building object are loaded (geometry is already done)
        IDF.setiddname(os.path.join(epluspath, "Energy+.idd"))
        idf = IDF(os.path.normcase(os.path.join(SimDir, 'Building_' + str(nbcase) +  '_template.idf')))
        try:
            with open(os.path.join(SimDir,'Building_' + str(nbcase) +  '_template.pickle'), 'rb') as handle:
                LoadBld = pickle.load(handle)
        except:
            with open(os.path.join(SimDir,'Building_' + str(nbcase) +  '_template.pickle'), 'rb') as handle:
                LoadBld = pickle5.load(handle)
        building = LoadBld['BuildData']

    Case = {}
    #Case['BuildIDF'] = idf
    Case['BuildData'] = building
    # assignement of the building name for the simulation
    building.name = 'Building_' + str(nbcase) +  'v'+str(currentRun)

    if DebugMode: startIniti = time.time()
    if not MakePlotOnly: #in order to make parametric simulation, lets go along the VarName2Change list and change the building object attributes accordingly
        GrlFct.setChangedParam(building, ParamVal, VarName2Change, MainPath, DataBaseInput, nbcase)

    # lets assign the material and finalize the envelope definition
    try:
        # start = time.time()
        GrlFct.setEnvelopeLevel(idf, building)
        #it's time to catch all the surface name facing outside
        allSurf = idf.getsurfaces()+idf.getsubsurfaces()
        for surf in allSurf:
            if surf.Surface_Type == 'Window':
                if (surf.azimuth > 60 and surf.azimuth < 300):
                    building.surfOutName.append(surf.Name.upper())
            elif surf.Outside_Boundary_Condition == 'outdoors':
                if surf.Surface_Type == 'roof': building.surfOutName.append(surf.Name.upper())
                elif surf.azimuth > 60 and surf.azimuth < 300: building.surfOutName.append(surf.Name.upper())
                # end = time.time()
        # print('[Time Report] : The setEnvelopeLevel took : ', round(end - start, 2), ' sec')
    except:
        msg = '[Error] The setEnvelopeLevel failed...\n'
        if Verbose: print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return building,idf, 'NOK'
    #the following is only to make building plots, so no need to go  feeding the indoor building inputs
    if DebugMode: GrlFct.Write2LogFile('[Time report] Building level (Envelope) phase : ' +
                                       str(round(time.time() - startIniti, 2)) + ' sec\n', LogFile)

    if MakePlotOnly:
        idf.idfname += ' / ' +building.BuildID['BldIDKey']+' : '+ str(building.BuildID[building.BuildID['BldIDKey']])
        return building,idf, 'OK'

    # lets define the zone level now
    if DebugMode: startIniti = time.time()
    try:
        # start = time.time()
        GrlFct.setZoneLevel(idf, building,FloorZoning)
        # end = time.time()
        # print('[Time Report] : The setZoneLevel took : ', round(end - start, 2), ' sec')
    except:
        msg = '[Error] The setZoneLevel failed...\n'
        if Verbose: print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return

    if DebugMode: GrlFct.Write2LogFile('[Time report] Zone level phase : ' +
                                       str(round(time.time() - startIniti, 2)) + ' sec\n', LogFile)

    try:
        # add some extra energy loads like domestic Hot water
        # start = time.time()
        GrlFct.setExtraEnergyLoad(idf,building)
    except:
        msg = '[Error] The setExtraEnergyLoad definition failed...\n'
        if Verbose: print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return
    if DebugMode: startIniti = time.time()
    try:
        #lets add the main gloval variable : Mean temperautre over the heated areas and the total building power consumption
        #and if present, the heating needs for DHW production as heated by direct heating
        #these are added using EMS option of EnergyPlus, and used for the FMU option
        # but if the building has more than 50 zones, than these are not computed as is will wrtie function in the idf file
        #could work with more than 50 zone though
        EMSOutputs = []
        if len(idf.idfobjects["ZONE"])<50:
            EMSOutputs.append('Mean Heated Zones Air Temperature')
            EMSOutputs.append('Total Building Heating Power')
            if building.DHWInfos:
                EMSOutputs.append('Total DHW Heating Power')

        # the outputs are set using the Output file
        GrlFct.setOutputLevel(idf,building,MainPath,EMSOutputs,OutputsFile)
        # end = time.time()
        # print('[Time Report] : The setOutputLevel took : ', round(end - start, 2), ' sec')
        #special ending process if FMU is wanted
    except:
        msg = '[Error] The Output definition failed...\n'
        if Verbose: print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return
    if DebugMode: GrlFct.Write2LogFile('[Time report] Output level phase : ' +
                                       str(round(time.time() - startIniti, 2)) + ' sec\n', LogFile)

    if CreateFMU:
        if DebugMode: startIniti = time.time()
        GrlFct.CreateFMU(idf,building,nbcase,epluspath,keyPath['FMUScriptPath'], SimDir, currentRun,EMSOutputs,LogFile,DebugMode)
        if DebugMode: GrlFct.Write2LogFile('[Time report] Creating FMU phase : ' +
                                           str(round(time.time() - startIniti, 2)) + ' sec\n', LogFile)
        if DebugMode: startIniti = time.time()
    else:
        # saving files and objects
        if DebugMode: startIniti = time.time()
        idf.saveas('Building_' + str(nbcase) +  'v'+str(currentRun)+'.idf')

        #the data object is saved as needed afterward aside the Eplus results (might be not needed, to be checked)
    with open('Building_' + str(nbcase) +  'v'+str(currentRun)+ '.pickle', 'wb') as handle:
        pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
    if DebugMode: GrlFct.Write2LogFile('[Time report] Writing file and data phase : ' +
                                           str(round(time.time() - startIniti, 2)) + ' sec\n', LogFile)
    msg = 'Building_' + str(nbcase)+' IDF file ' + str(currentRun+1)+ '/'  + str(TotNbRun)+ ' is done\n'
    if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    if Verbose: print(msg[:-1])
    end = time.time()
    GrlFct.Write2LogFile('[Reported Time] Input File : '+str(round(end-start,2))+' seconds\n',LogFile)
    GrlFct.Write2LogFile('##############################################################\n', LogFile)
    if FirstRun:
        LogFile.close()
        # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)

if __name__ == '__main__' :

    FirstRun = False
    CorePerim = False
    FloorZoning = False
    ParamVal = []
    VarName2Change = []
    CreateFMU = False
    TotNbRun = 1
    currentRun = 0
    OutputsFile = 'Outputs.txt'

    #to be mandatory defined in the command line :
    SimDir = None
    PathInputFiles = None
    nbcase = None

    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-SimDir')):
            currIdx += 1
            SimDir = sys.argv[currIdx]
        elif (currArg.startswith('-epluspath')):
            currIdx += 1
            PathInputFiles = sys.argv[currIdx]
        elif (currArg.startswith('-BuildingsFile')):
            currIdx += 1
            BuildingsFile = sys.argv[currIdx]
        elif (currArg.startswith('-ShadingsFile')):
            currIdx += 1
            ShadingsFile = sys.argv[currIdx]
        elif (currArg.startswith('-nbBuild')):
            currIdx += 1
            nbcase = int(sys.argv[currIdx])
        elif (currArg.startswith('-FirstRun')):
            currIdx += 1
            FirstRun = eval(sys.argv[currIdx])
        elif (currArg.startswith('-CorePerim')):
            currIdx += 1
            CorePerim = eval(sys.argv[currIdx])
        elif (currArg.startswith('-FloorZoning')):
            currIdx += 1
            FloorZoning = eval(sys.argv[currIdx])
        elif (currArg.startswith('-ParamVal')):
            currIdx += 1
            ParamVal = sys.argv[currIdx]
        elif (currArg.startswith('-VarName2Change')):
            currIdx += 1
            VarName2Change = sys.argv[currIdx]
        elif (currArg.startswith('-CreateFMU')):
            currIdx += 1
            CreateFMU = eval(sys.argv[currIdx])
        elif (currArg.startswith('-NbRuns')):
            currIdx += 1
            TotNbRun = int(sys.argv[currIdx])
        elif (currArg.startswith('-OutputsFile')):
            currIdx += 1
            OutputsFile = sys.argv[currIdx]
        elif (currArg.startswith('-currentRun')):
            currIdx += 1
            currentRun = int(sys.argv[currIdx])
        currIdx += 1
    if TotNbRun == 1:
        ParamVal = []
        VarName2Change = []
    else:
        ParamVal = re.findall("[0-9.Ee\-+]+", ParamVal)
        ParamVal = [float(val) for val in ParamVal]
        VarName2Change = re.split(r'\W+', VarName2Change)[1:-1]

    keypath = {'epluspath':epluspath, 'BuildingsFile':BuildingsFile, 'ShadingsFile':ShadingsFile}
    LaunchProcess(SimDir, FirstRun, TotNbRun, currentRun,keypath, nbcase, CorePerim, FloorZoning, ParamVal,VarName2Change,
                  CreateFMU, OutputsFile)