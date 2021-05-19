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


def LaunchProcess(SimDir,DataBaseInput,LogFile,bldidx,keyPath,nbcase,CorePerim = False,FloorZoning = False,FigCenter=(0,0),PlotBuilding = False):
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
    idf_ref.idfname = 'Building_' + str(nbcase) + '\n FormularId : ' + str(
        building_ref.BuildID['FormularId']) + '\n 50A_UUID : ' + str(building_ref.BuildID['50A_UUID'])

    print('50A_UUID : ' + str(building_ref.BuildID['50A_UUID']))
    print('FormularId : ' + str(building_ref.BuildID['FormularId']))
    FigCenter.append(building_ref.RefCoord)
    refx = sum([center[0] for center in FigCenter]) / len(FigCenter)
    refy = sum([center[1] for center in FigCenter]) / len(FigCenter)
    #Rounds of check if we continue with this building or not
    Var2check = len(building_ref.BlocHeight) if building_ref.Multipolygon else building_ref.height
    #if the building have bloc with no Height or if the hiegh is below 1m (shouldn't be as corrected in the Building class now)
    if len(building_ref.BlocHeight) > 0 and min(building_ref.BlocHeight) < 1:
        Var2check = 0
    #is heated area is below 50m2, we just drop the building
    if building_ref.EPHeatedArea < 50:
        Var2check = 0
    #is no floor is present...(shouldn't be as corrected in the Building class now)
    if 0 in building_ref.BlocNbFloor:
        Var2check = 0

    if Var2check == 0:
        msg =  '[Error] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n'
        print(msg[:-1])
        os.chdir(MainPath)
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)
        return epluspath, building_ref.WeatherDataFile,(refx,refy)

    if not PlotBuilding:
        building_ref.MaxShadingDist = 0
        building_ref.shades = building_ref.getshade(DataBaseInput['Build'][nbcase], DataBaseInput['Shades'], DataBaseInput['Build'],DB_Data.GeomElement,LogFile)
    # change on the building __init__ class in the simulation level should be done here as the function below defines the related objects
    GrlFct.setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here as the function below defines the related objects
    GrlFct.setBuildingLevel(idf_ref, building_ref,LogFile,CorePerim,FloorZoning,ForPlots = True)

    GrlFct.setEnvelopeLevel(idf_ref, building_ref)
    FigCentroid = building_ref.RefCoord if PlotBuilding else (refx, refy)
    idf_ref.view_model(test=PlotBuilding, FigCenter=FigCentroid)

    GrlFct.Write2LogFile('##############################################################\n', LogFile)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)
    return epluspath, building_ref.WeatherDataFile, (refx,refy)


if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART     ##################################################################################
######################################################################################################################
#The Modeler have to fill in the following parameter to define his choices

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
    FloorZoning = True
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
        SimDir = CurrentPath
        LogFile = open(os.path.join(SimDir, 'PlotBuilder_Logs.log'), 'w')
        for idx,nbBuild in enumerate(BuildNum2Launch):
            if idx<len(DataBaseInput['Build']):
                #getting through the mainfunction above :LaunchProcess() each building sees its idf done in a row within this function
                try:
                    epluspath, weatherpath,NewCentroid = LaunchProcess(SimDir,DataBaseInput,LogFile,idx,keyPath,nbBuild,CorePerim,FloorZoning,
                            FigCenter,PlotBuilding)
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
        import matplotlib.pyplot as plt
        plt.show()
        sys.path.remove(path2addgeom)