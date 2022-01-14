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
import CoreFiles.GeneralFunctions as GrlFct
from BuildObject.DB_Building import BuildingList
from BuildObject.DB_Filter4Simulations import checkBldFilter
import BuildObject.DB_Data as DB_Data
import re
import time

def LaunchOAT(MainInputs,SimDir,keypath,nbBuild,ParamVal,currentRun,pythonpath=[],BldObj=[]):

    #this function was made to enable either to launch a process in a seperate terminal or not, given a python path to a virtualenv
    #but if kept in seperate terminal, the inputfile needs to be read for each simulation...not really efficient,
    #thus, the first option, being fully in the same envirnment is used with the optionnal argument 'DataBaseInput'
    if not pythonpath:
        LaunchProcess(SimDir, MainInputs['FirstRun'], MainInputs['TotNbRun'], currentRun,
                                  keypath, nbBuild, MainInputs['CorePerim'],
                                  MainInputs['FloorZoning'], ParamVal,MainInputs['VarName2Change'],MainInputs['CreateFMU'],
                                    MainInputs['OutputsFile'],DataBaseInput = MainInputs['DataBaseInput'], DebugMode = MainInputs['DebugMode'])
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
                  CreateFMU,OutputsFile,DataBaseInput = [], DebugMode = False):
    #This function builds the idf file, a log file is generated if the buildiung is run for the first time,
    #the idf file will be saved as well as the building object as a pickle. the latter could be commented as not required
    MainPath = os.getcwd()

    # try:
    #     keyPath = GrlFct.readPathfile(PathInputFiles)
    # except:
    #     #this is in case the PathInput file is already the dictionnary (it is the case when launched through the API
    #     keyPath = PathInputFiles
    if not DataBaseInput:
        # Building and Shading objects from reading the geojson file as input for further functionsif not given as arguments
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    Buildingsfile = DataBaseInput['Build']
    Shadingsfile = DataBaseInput['Shades']
    epluspath = keyPath['epluspath']
    os.chdir(SimDir)
    #Creating the log file for this building if it's his frist run
    if FirstRun:
        LogFile = open(os.path.join(SimDir, 'Build_'+str(nbcase)+'_Logs.log'), 'w')
        msg = 'Building ' + str(nbcase) + ' is starting\n'
        print(msg[:-1])
        GrlFct.Write2LogFile(msg,LogFile)
    else:
        LogFile = False

    #if its the first run of a pool for the same building, than only the simulation parameters and the building geometry will run.
    #a 'tewmplate file will be created and openned by the following runs to save the geometry construction process (as it is the longest one)
    if FirstRun:
        StudiedCase = BuildingList()
        #lets build the two main object we'll be playing with in the following : the idf and the building
        idf, building = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath,LogFile, DebugMode = DebugMode)
        #Rounds of check if we continue with this building or not, see DB_Filter4Simulation.py if other filter are to add
        CaseOK = checkBldFilter(building,LogFile,DebugMode = DebugMode)
        if not CaseOK:
            msg =  '[Error] This Building/bloc is not valid to continue, please check DB_Filter4Simulation.py to see what is of concerned or turn on DebugMode\n'
            print(msg[:-1])
            os.chdir(MainPath)
            if FirstRun:
                GrlFct.Write2LogFile(msg, LogFile)
                GrlFct.Write2LogFile('##############################################################\n', LogFile)
                return

        # The simulation parameters are assigned here
        GrlFct.setSimLevel(idf, building)
        # The geometry is assigned here
        try:
            # start = time.time()
            GrlFct.setBuildingLevel(idf, building,LogFile,CorePerim,FloorZoning,DebugMode = DebugMode)
            # end = time.time()
            # print('[Time Report] : The setBuildingLevel took : ',round(end-start,2),' sec')
        except:
            msg = '[Error] The setBuildingLevel failed...\n'
            print(msg[:-1])
            os.chdir(MainPath)
            if FirstRun:
                GrlFct.Write2LogFile(msg, LogFile)
                GrlFct.Write2LogFile('##############################################################\n', LogFile)
                return
        # if the number of run for one building is greater than 1 it means parametric simulation, a template file will be saved
        if TotNbRun>1:
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

    #in order to make parametric simulation, lets go along the VarName2Change list and change the building object attributes accordingly
    GrlFct.setChangedParam(building,ParamVal,VarName2Change,MainPath,Buildingsfile,Shadingsfile,nbcase,DB_Data)

    # lets assign the material and finalize the envelope definition
    try:
        # start = time.time()
        GrlFct.setEnvelopeLevel(idf, building)
        # end = time.time()
        # print('[Time Report] : The setEnvelopeLevel took : ', round(end - start, 2), ' sec')
    except:
        msg = '[Error] The setEnvelopeLevel failed...\n'
        print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return
    #uncomment only to have a look at the splitting surfaces function effect. it will make a figure for each building created
    #idf.view_model(test=True, FigCenter=(0,0))

    # lets define the zone level now
    try:
        # start = time.time()
        GrlFct.setZoneLevel(idf, building,FloorZoning)
        # end = time.time()
        # print('[Time Report] : The setZoneLevel took : ', round(end - start, 2), ' sec')
    except:
        msg = '[Error] The setZoneLevel failed...\n'
        print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return

    try:
        # add some extra energy loads like domestic Hot water
        # start = time.time()
        GrlFct.setExtraEnergyLoad(idf,building)
    except:
        msg = '[Error] The setExtraEnergyLoad definition failed...\n'
        print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return
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
        if CreateFMU:
            GrlFct.CreatFMU(idf,building,nbcase,epluspath,SimDir, currentRun,EMSOutputs,LogFile,DebugMode)
        else:
             # saving files and objects
            idf.saveas('Building_' + str(nbcase) +  'v'+str(currentRun)+'.idf')

        #the data object is saved as needed afterward aside the Eplus results (might be not needed, to be checked)
        with open('Building_' + str(nbcase) +  'v'+str(currentRun)+ '.pickle', 'wb') as handle:
            pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)

        msg = 'Building_' + str(nbcase)+' IDF file ' + str(currentRun+1)+ '/'  + str(TotNbRun)+ ' is done\n'
        print(msg[:-1])
        GrlFct.Write2LogFile('##############################################################\n', LogFile)
        if FirstRun:
            LogFile.close()
        # lets get back to the Main Folder we were at the very beginning
        os.chdir(MainPath)
    except:
        msg = '[Error] The process after the Zonelevel definition failed...\n'
        print(msg[:-1])
        os.chdir(MainPath)
        if FirstRun:
            GrlFct.Write2LogFile(msg, LogFile)
            GrlFct.Write2LogFile('##############################################################\n', LogFile)
            return


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
        elif (currArg.startswith('-TotNbRun')):
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