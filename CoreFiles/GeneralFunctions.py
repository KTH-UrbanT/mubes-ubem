# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
sys.path.append("..")
import CoreFiles.GeomScripts as GeomScripts
import CoreFiles.Set_Outputs as Set_Outputs
import CoreFiles.Sim_param as Sim_param
import CoreFiles.Load_and_occupancy as Load_and_occupancy
import CoreFiles.DomesticHotWater as DomesticHotWater
import CoreFiles.MUBES_pygeoj as MUBES_pygeoj
import CoreFiles.BuildFMUs as BuildFMUs
from openpyxl import load_workbook
from SALib.sample import latin
import shutil

def appendBuildCase(StudiedCase,epluspath,nbcase,DataBaseInput,MainPath,LogFile,PlotOnly = False):
    StudiedCase.addBuilding('Building'+str(nbcase),DataBaseInput,nbcase,MainPath,epluspath,LogFile,PlotOnly)
    idf = StudiedCase.building[-1]['BuildIDF']
    building = StudiedCase.building[-1]['BuildData']
    return idf, building

def setSimLevel(idf,building):
    ####################################################################
    #Simulation Level
    #####################################################################
    Sim_param.Location_and_weather(idf,building)
    Sim_param.setSimparam(idf,building)

def setBuildingLevel(idf,building,LogFile,CorePerim = False,FloorZoning = False,ForPlots = False):
    ######################################################################################
    #Building Level
    ######################################################################################
    #this is the function that requires the most time
    GeomScripts.createBuilding(LogFile,idf,building, perim = CorePerim,FloorZoning = FloorZoning,ForPlots=ForPlots)


def setEnvelopeLevel(idf,building):
    ######################################################################################
    #Envelope Level (within the building level)
    ######################################################################################
    #the other geometric element are thus here
    GeomScripts.createRapidGeomElem(idf, building)

def setZoneLevel(idf,building,FloorZoning = False):
    ######################################################################################
    #Zone level
    ######################################################################################
    #control command related equipment, loads and leaks for each zones
    Load_and_occupancy.CreateZoneLoadAndCtrl(idf,building,FloorZoning)

def setExtraEnergyLoad(idf,building):
    if building.DHWInfos:
        DomesticHotWater.createWaterEqpt(idf,building)


def setOutputLevel(idf,building,MainPath,EMSOutputs,OutputsFile):
    #ouputs definitions
    Set_Outputs.AddOutputs(idf,building,MainPath,EMSOutputs,OutputsFile)

def readPathfile(Pathways):
    keyPath = {'epluspath': '', 'Buildingsfile': '', 'Shadingsfile': '','GeojsonProperties':''}
    with open(Pathways, 'r') as PathFile:
        Paths = PathFile.readlines()
        for line in Paths:
            for key in keyPath:
                if key in line:
                    keyPath[key] = os.path.normcase(line[line.find(':') + 1:-1])
    return keyPath

def ReadGeoJsonFile(keyPath):
    try:
        BuildObjectDict = ReadGeojsonKeyNames(keyPath['GeojsonProperties'])
        Buildingsfile = MUBES_pygeoj.load(keyPath['Buildingsfile'], round_factor=4)
        Shadingsfile = MUBES_pygeoj.load(keyPath['Shadingsfile'], round_factor=4)
        return {'BuildObjDict':BuildObjectDict,'Build' :Buildingsfile, 'Shades': Shadingsfile}
    except:
        Buildingsfile = MUBES_pygeoj.load(keyPath['Buildingsfile'], round_factor=4)
        Shadingsfile = MUBES_pygeoj.load(keyPath['Shadingsfile'], round_factor=4)
        return {'Build': Buildingsfile, 'Shades': Shadingsfile}

def SaveCase(MainPath,SepThreads,CaseName,nbBuild):
    SaveDir = os.path.join(os.path.dirname(os.path.dirname(MainPath)), 'SimResults')
    if not os.path.exists(SaveDir):
        os.mkdir(SaveDir)
    if SepThreads:
        os.rename(os.path.join(MainPath, 'RunningFolder'),
                  os.path.join(SaveDir, CaseName + '_Build_' + str(nbBuild)))
        try:
            os.rename(os.path.join(MainPath,CaseName+'_Logs.log'), os.path.join(os.path.join(SaveDir, CaseName + '_Build_' + str(nbBuild)),CaseName+'_Logs.log'))
        except:
            pass
    else:
        os.rename(os.path.join(os.getcwd(), 'RunningFolder'),
                  os.path.join(SaveDir,CaseName))
        try:
            os.rename(os.path.join(MainPath, CaseName + '_Logs.log'),
                  os.path.join(os.path.join(SaveDir,CaseName), CaseName + '_Logs.log'))
        except:
            pass

def CreateSimDir(CurrentPath,CaseName,SepThreads,nbBuild,idx,Refresh = False):
    if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(CurrentPath)),'MUBES_SimResults')):
        os.mkdir(os.path.join(os.path.dirname(os.path.dirname(CurrentPath)),'MUBES_SimResults'))
    SimDir = os.path.normcase(
        os.path.join(os.path.dirname(os.path.dirname(CurrentPath)), os.path.join('MUBES_SimResults', CaseName)))
    if not os.path.exists(SimDir):
        os.mkdir(SimDir)
    elif idx == 0 and Refresh:
        shutil.rmtree(SimDir)
        os.mkdir(SimDir)
    if SepThreads:
        SimDir = os.path.normcase(
            os.path.join(SimDir, 'Build_' + str(nbBuild)))
        if not os.path.exists(SimDir):
            os.mkdir(SimDir)
        elif idx == 0:
            shutil.rmtree(SimDir)
            os.mkdir(SimDir)
    return SimDir

    # if not SepThreads:
    #     SimDir = os.path.normcase(
    #             os.path.join(os.path.dirname(os.path.dirname(CurrentPath)), os.path.join('SimResults', CaseName)))
    # else:
    #     SimDir = os.path.normcase(
    #         os.path.join(os.path.dirname(os.path.dirname(CurrentPath)), os.path.join('SimResults', CaseName + '_Build_' + str(nbBuild))))
    # if not os.path.exists(SimDir):
    #     os.mkdir(SimDir)
    # elif SepThreads or idx == 0:
    #     shutil.rmtree(SimDir)
    #     os.mkdir(SimDir)

def getParamSample(VarName2Change,Bounds,nbruns):
    # Sampling process if someis define int eh function's arguments
    # It is currently using the latin hyper cube methods for the sampling generation (latin.sample)
    Param = [1]
    if len(VarName2Change) > 0:
        problem = {}
        problem['names'] = VarName2Change
        problem['bounds'] = Bounds  # ,
        problem['num_vars'] = len(VarName2Change)
        # problem = read_param_file(MainPath+'\\liste_param.txt')
        Param = latin.sample(problem, nbruns)
    return Param

def CreatFMU(idf,building,nbcase,epluspath,SimDir, i,varOut,LogFile):
    print('Building FMU under process...Please wait around 30sec')
    #get the heated zones first and set them into a zonelist
    BuildFMUs.setFMUsINOut(idf, building,varOut)
    idf.saveas('Building_' + str(nbcase) + 'v' + str(i) + '.idf')
    BuildFMUs.buildEplusFMU(epluspath, building.WeatherDataFile, os.path.join(SimDir,'Building_' + str(nbcase) + 'v' + str(i) + '.idf'))
    print('FMU created for this building')
    Write2LogFile('FMU created for this building\n',LogFile)
    Write2LogFile('##############################################################\n',LogFile)

def ReadGeojsonKeyNames(GeojsonProperties):
    file = load_workbook(GeojsonProperties).active
    #get the headers
    BldObjName = {}
    for i in range(1,file.max_column+1):
        header = file.cell(row = 1, column = i).internal_value
        if header == 'Field of application':
            AppColNb = i
            for j in range(2,file.max_row+1):
                currentname = file.cell(row = j, column = i).internal_value.replace(' ','_')
                if currentname not in BldObjName.keys():
                    BldObjName[currentname] = {'KeyWord': [],'Attributes':[],'Unit':[],'Format':[],'ExpectedVal':[]}
    # for each objectName, lets get list defined above
    for i in range(1, file.max_column + 1):
        header = file.cell(row=1, column=i).internal_value
        if header == 'Propertie Name':
            for j in range(2, file.max_row + 1):
                BldObjName[file.cell(row=j, column=AppColNb).internal_value.replace(' ','_')]['KeyWord'].append(file.cell(row = j, column = i).internal_value)
        if header == 'VariableName':
            for j in range(2, file.max_row + 1):
                BldObjName[file.cell(row=j, column=AppColNb).internal_value.replace(' ','_')]['Attributes'].append(file.cell(row = j, column = i).internal_value)
        if header == 'Unit':
            for j in range(2, file.max_row + 1):
                BldObjName[file.cell(row=j, column=AppColNb).internal_value.replace(' ','_')]['Unit'].append(file.cell(row = j, column = i).internal_value)
        if header == 'Format':
            for j in range(2, file.max_row + 1):
                BldObjName[file.cell(row=j, column=AppColNb).internal_value.replace(' ','_')]['Format'].append(file.cell(row = j, column = i).internal_value)
        if header == 'Expected values':
            for j in range(2, file.max_row + 1):
                BldObjName[file.cell(row=j, column=AppColNb).internal_value.replace(' ','_')]['ExpectedVal'].append(file.cell(row = j, column = i).internal_value)
    return BldObjName

def Write2LogFile(message,LogFile):
    try:
        LogFile.write(message)
    except:
        pass

def ReadZoneOfInterest(ZoneOfInterest,keyWord):
    BldIds = []
    with open(ZoneOfInterest, 'r') as handle:
        FileLines = handle.readlines()
    headers = FileLines[0].split("\t")
    idx = headers.index(keyWord)
    for i,line in enumerate(FileLines[1:]):
        Vals = line.split("\t")
        BldIds.append(Vals[idx])
    return BldIds


if __name__ == '__main__' :
    print('GeneralFunctions.py')