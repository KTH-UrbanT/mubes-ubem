# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
from geomeppy import IDF
#add needed packages
import pickle5 as pickle
import copy
import shutil
#add scripts from the project as well
sys.path.append("..")
import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.LaunchSim as LaunchSim
from BuildObject.DB_Building import BuildingList
import BuildObject.DB_Data as DB_Data
import multiprocessing as mp
import re

def LaunchProcess(SimDir,FirstRun,TotNbRun,currentRun,PathInputFiles,nbcase,CorePerim,FloorZoning,ParamVal,VarName2Change,
                  CreateFMU,OutputsFile):
    MainPath = os.getcwd()
    #Building and Shading objects fronm reading the geojson file as input for further functions
    keyPath = GrlFct.readPathfile(PathInputFiles)
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    Buildingsfile = DataBaseInput['Build']
    Shadingsfile = DataBaseInput['Shades']
    epluspath = keyPath['epluspath']
    os.chdir(SimDir)
    #process is launched for the considered building
    if FirstRun:
        LogFile = open(os.path.join(SimDir, 'Build_'+str(nbcase)+'_Logs.log'), 'w')
        msg = 'Building ' + str(nbcase) + ' is starting\n'
        print(msg[:-1])
        GrlFct.Write2LogFile(msg,LogFile)
    else:
        LogFile = False
    #All buildings are organized and append in a list (list of building object. But the process finally is not used as it have been thought to.
    #each building is laucnhed afterward using the idf file and not the object directly (see LaunchSim.runcase() function
    #Nevertheless this organization still enable to order things !
    if FirstRun:
        StudiedCase = BuildingList()
        #lets build the two main object we'll be playing with in the following'
        idf, building = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath,LogFile)

        #Rounds of check if we continue with this building or not
        Var2check = len(building.BlocHeight) if building.Multipolygon else building.height
        #if the building have bloc with no Height or if the hiegh is below 1m (shouldn't be as corrected in the Building class now)
        if len(building.BlocHeight) > 0 and min(building.BlocHeight) < 1:
            Var2check = 0
        #is heated area is below 50m2, we just drop the building
        if building.EPHeatedArea < 50:
            Var2check = 0
        #is no floor is present...(shouldn't be as corrected in the Building class now)
        if 0 in building.BlocNbFloor:
            Var2check = 0
        if Var2check == 0:
            msg =  '[Error] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n'
            print(msg[:-1])
            os.chdir(MainPath)
            if FirstRun:
                GrlFct.Write2LogFile(msg, LogFile)
                GrlFct.Write2LogFile('##############################################################\n', LogFile)

            # change on the building __init__ class in the simulation level should be done here as the function below defines the related objects
        GrlFct.setSimLevel(idf, building)
            # change on the building __init__ class in the building level should be done here as the function below defines the related objects
        GrlFct.setBuildingLevel(idf, building,LogFile,CorePerim,FloorZoning)

        if TotNbRun>1:
            Case = {}
            Case['BuildData'] = building
            idf.saveas('Building_' + str(nbcase) + '_template.idf')
            with open('Building_' + str(nbcase) + '_template.pickle', 'wb') as handle:
                pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        IDF.setiddname(os.path.join(epluspath, "Energy+.idd"))
        idf = IDF(os.path.normcase(os.path.join(SimDir, 'Building_' + str(nbcase) +  '_template.idf')))
        with open(os.path.join(SimDir,'Building_' + str(nbcase) +  '_template.pickle'), 'rb') as handle:
                LoadBld = pickle.load(handle)
        building = LoadBld['BuildData']
    Case = {}
    #Case['BuildIDF'] = idf
    Case['BuildData'] = building

    building.name = 'Building_' + str(nbcase) +  'v'+str(currentRun)

            # # example of modification with half of the runs with external insulation and half of the runs with internal insulation
            # if i < round(nbruns / 2):
            #     building.ExternalInsulation = True
            # else:
            #     building.ExternalInsulation = False

            #now lets go along the VarName2Change list and change the building object attributes
            #if these are embedded into several layer of dictionnaries than there is a need to make checks and change accordingly the correct element
            #here are examples for InternalMass impact using 'InternalMass' keyword in the VarName2Change list to play with the 'WeightperZoneArea' parameter
            #and for ExternalMass impact using 'ExtMass' keyword in the VarName2Change list to play with the 'Thickness' of the wall inertia layer
    for varnum,var in enumerate(VarName2Change):
        if 'InternalMass' in var:
            intmass = building.InternalMass
            intmass['HeatedZoneIntMass']['WeightperZoneArea'] = ParamVal[varnum]
            setattr(building, var, intmass)
        elif 'ExtMass' in var:
            exttmass = building.Materials
            exttmass['Wall Inertia']['Thickness'] = round(ParamVal[varnum],3)
            setattr(building, var, exttmass)
        elif 'WindowUval' in var:
            building.Materials['Window']['UFactor'] = round(ParamVal[varnum],3)
        elif 'setTempLoL' in var:
            building.setTempLoL = [round(ParamVal[varnum], 3),round(ParamVal[varnum], 3)]
        elif 'WallInsuThick' in var:
            exttmass = building.Materials
            exttmass['Wall Insulation']['Thickness'] = round(ParamVal[varnum], 3)
            setattr(building, var, exttmass)
        elif 'RoofInsuThick' in var:
            exttmass = building.Materials
            exttmass['Roof Insulation']['Thickness'] = round(ParamVal[varnum], 3)
            setattr(building, var, exttmass)
        elif 'MaxShadingDist' in var:
            building.shades = building.getshade(Buildingsfile[nbcase], Shadingsfile, Buildingsfile,DB_Data.GeomElement,LogFile)
        elif 'IntLoadCurveShape' in var:
            building.IntLoadCurveShape = round(ParamVal[varnum], 3)
            building.IntLoad = building.getIntLoad(MainPath, LogFile)
        elif 'AreaBasedFlowRate' in var:
            building.AreaBasedFlowRate = round(ParamVal[varnum], 3)
            building.AreaBasedFlowRateDefault = round(ParamVal[varnum], 3)
        else:
            try:
                setattr(building, var, ParamVal[varnum])     #for all other cases with simple float, this line just change the attribute's value directly
            except:
                print('This one needs special care : '+var)


                #here is an other example for changing the distance underwhich the surrounding building are considered for shading aspects
                #as 'MaxShadingDist' is an input for the Class building method getshade, the method shall be called again after modifying this value (see getshade methods)


            #here is an other example of simplemodification we want as forcing the building to have recovery on its ventilation system
            #or the change the U value of the Window.
            #for changes done this way, there are no modification in each runs. all the runs will have forced values for the considered attributes
            #lets put all ventilation with heat recovery to True
            # building.VentSyst['BalX'] = True
            # building.VentSyst['ExhX'] = True
            #lets change the windos U value
            # building.Materials['Window']['UFactor'] = 0.78

            ##############################################################
            ##After having made the changes we wanted in the building object, we can continue the construction of the idf (input file for EnergyPLus)
            # change on the building __init__ class in the envelope level should be done here

    GrlFct.setEnvelopeLevel(idf, building)

        #change on the building __init__ class in the zone level should be done here
    GrlFct.setZoneLevel(idf, building,FloorZoning)

            #Lets change the path of the water taps file :
            # ComputfFilePath = os.path.normcase('C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration')
            # building.DHWInfos['WatertapsFile'] = os.path.join(ComputfFilePath,'FlowRate'+str(nbcase)+'.txt')
            # building.DHWInfos['WaterTapsMultiplier'] = 1
            # nbAppartments = building.nbAppartments
            # building.nbAppartments = 1
            # Lets read the correction factors
    work_dir = os.path.normcase('C:\\Users\\xav77\Documents\FAURE\prgm_python\\UrbanT\Eplus4Mubes\MUBES_SimResults\ham4calibwithmeasuredandnewweather\Sim_Results')
    CorFactPath = os.path.normcase(os.path.join(work_dir, 'DHWCorFact.txt'))
    with open(CorFactPath, 'r') as handle:
        FileLines = handle.readlines()
    CorFact = {}
    for line in FileLines:
        CorFact[int(line[:line.index('\t')])] = float(line[line.index('\t') + 1:line.index('\n')])
    building.DHWInfos['WaterTapsMultiplier'] *= CorFact[nbcase]
            #add some extra energy loads like domestic Hot water
    GrlFct.setExtraEnergyLoad(idf,building)
            #to give back the good values
            # building.nbAppartments = nbAppartments

            #lets add the main gloval variable : Mean temperautre over the heated areas and the total building power consumption
            #and if present, the heating needs for DHW production as heated by direct heating
            #these are added thourgh EMS option of EnergyPlus
    EMSOutputs = []
    EMSOutputs.append('Mean Heated Zones Air Temperature')
    EMSOutputs.append('Total Building Heating Power')
    if building.DHWInfos:
        EMSOutputs.append('Total DHW Heating Power')

    GrlFct.setOutputLevel(idf,building,MainPath,EMSOutputs,OutputsFile)

    if CreateFMU:
        GrlFct.CreatFMU(idf,building,nbcase,epluspath,SimDir, currentRun,EMSOutputs,LogFile)
    else:
         # saving files and objects
        idf.saveas('Building_' + str(nbcase) +  'v'+str(currentRun)+'.idf')


            #the data object is saved as needed afterward aside the Eplus results
    with open('Building_' + str(nbcase) +  'v'+str(currentRun)+ '.pickle', 'wb') as handle:
        pickle.dump(Case, handle, protocol=pickle.HIGHEST_PROTOCOL)
    msg = 'Input IDF file ' + str(currentRun+1)+ '/'  + str(TotNbRun)+ ' is done\n'
    print(msg[:-1])
    GrlFct.Write2LogFile(msg, LogFile)
    GrlFct.Write2LogFile('##############################################################\n', LogFile)

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
        elif (currArg.startswith('-PathInputFiles')):
            currIdx += 1
            PathInputFiles = sys.argv[currIdx]
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
        ParamVal = re.findall("\d+\.\d+", ParamVal)
        ParamVal = [float(val) for val in ParamVal]
        VarName2Change = re.split(r'\W+', VarName2Change)[1:-1]

    LaunchProcess(SimDir, FirstRun, TotNbRun, currentRun,PathInputFiles, nbcase, CorePerim, FloorZoning, ParamVal,VarName2Change,
                  CreateFMU, OutputsFile)