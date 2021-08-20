# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
sys.path.append("..")
import CoreFiles.GeneralFunctions as GrlFct
from BuildObject.DB_Building import BuildingList
import BuildObject.DB_Data as DB_Data
from BuildObject.DB_Filter4Simulations import checkBldFilter

def LaunchProcess(SimDir,DataBaseInput,LogFile,bldidx,keyPath,nbcase,CorePerim = False,FloorZoning = False,FigCenter=(0,0),WindSize = 50, PlotBuilding = False):
    #process is launched for the considered building
    msg = 'Building ' + str(nbBuild) + ' is starting\n'
    print('#############################################')
    print(msg[:-1])
    GrlFct.Write2LogFile(msg,LogFile)
    MainPath = os.getcwd()
    epluspath = keyPath['epluspath']
    os.chdir(SimDir)
    StudiedCase = BuildingList()
    #lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath,LogFile, PlotOnly = True)
    refName ='Building_' + str(nbcase)
    for key in building_ref.BuildID:
        print(key + ' : ' + str(building_ref.BuildID[key]))
        refName += '\n ' + key + str(building_ref.BuildID[key])
    idf_ref.idfname = refName
    # Rounds of check if we continue with this building or not, see DB_Filter4Simulation.py if other filter are to add
    CaseOK = checkBldFilter(building_ref)

    if not CaseOK:
        msg =  '[Error] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n'
        print(msg[:-1])
        os.chdir(MainPath)
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)

        return FigCenter, WindSize

    FigCenter.append(building_ref.RefCoord)
    refx = sum([center[0] for center in FigCenter]) / len(FigCenter)
    refy = sum([center[1] for center in FigCenter]) / len(FigCenter)

    if not PlotBuilding:
        building_ref.MaxShadingDist = 0
        building_ref.shades = building_ref.getshade(DataBaseInput['Build'][nbcase], DataBaseInput['Shades'], DataBaseInput['Build'],DB_Data.GeomElement,LogFile)

    GrlFct.setBuildingLevel(idf_ref, building_ref,LogFile,CorePerim,FloorZoning,ForPlots = True)
    GrlFct.setEnvelopeLevel(idf_ref, building_ref)
    FigCentroid = building_ref.RefCoord if PlotBuilding else (refx, refy)

    #compåuting the window size for visualization
    for poly in building_ref.footprint:
        for vertex in poly:
            WindSize = max(GrlFct.ComputeDistance(FigCentroid, vertex),WindSize)
    idf_ref.view_model(test=PlotBuilding, FigCenter=FigCentroid, WindSize = 2*WindSize)

    GrlFct.Write2LogFile('##############################################################\n', LogFile)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)

    return (refx,refy),WindSize


if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART     ##################################################################################
######################################################################################################################

#This file is only to make graphs of the building geometry given in the GoeJsonF

# BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
# PathInputFile = 'String'              #Name of the PathFile containing the paths to the data and to energyplus application (see ReadMe)
# CorePerim = False / True             #True = create automatic core and perimeter zonning of each building. This options increases in a quite
#                                       large amount both building process and simulation process.
#                                       It can used with either one zone per floor or one zone per heated or none heated zone
#                                       building will be generated first, all results will be saved in one single folder
# FloorZoning = False / True            True = thermal zoning will be realized for each floor of the building, if false, there will be 1 zone
#                                       for the heated volume and, if present, one zone for the basement (non heated volume
## PlotBuilding = False / True          #True = after each building the building will be plotted for visual check of geometry and thermal zoning.
#                                       It include the shadings, if False, all the building will be plotted wihtout the shadings
# ZoneOfInterest = 'String'             #Text file with Building's ID that are to be considered withoin the BuildNum list, if '' than all building in BuildNum will be considered

    BuildNum = []
    PathInputFile = 'Pathways_Template.txt'
    CorePerim = False
    FloorZoning = False
    PlotBuilding = False
    ZoneOfInterest = ''

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
######################################################################################################################
    CaseName = 'ForTest'

    # reading the pathfiles and the geojsonfile
    keyPath = GrlFct.readPathfile(PathInputFile)
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
        WindSize = 50
        SimDir = CurrentPath
        LogFile = open(os.path.join(SimDir, 'PlotBuilder_Logs.log'), 'w')
        for idx,nbBuild in enumerate(BuildNum2Launch):
            if idx<len(DataBaseInput['Build']):
                #getting through the mainfunction above :LaunchProcess() each building sees its idf done in a row within this function
                try:
                    NewCentroid,WindSize = LaunchProcess(SimDir,DataBaseInput,LogFile,idx,keyPath,nbBuild,CorePerim,FloorZoning,
                            FigCenter,WindSize,PlotBuilding)
                except:
                    msg = '[ERROR] There was an error on this building, process aborted\n'
                    print(msg[:-1])
                    GrlFct.Write2LogFile(msg, LogFile)
                    GrlFct.Write2LogFile('##############################################################\n', LogFile)
                    os.chdir(CurrentPath)
                #if choicies is done, once the building is finished parallel computing is launched for this one
            else:
                print('All buildings in the input file have been treated.')
                print('###################################################')
                break
        LogFile.close()
        import matplotlib.pyplot as plt
        plt.show()
        sys.path.remove(path2addgeom)