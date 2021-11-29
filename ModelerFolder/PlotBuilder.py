# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys

path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'geomeppy')
sys.path.append(path2addgeom)
sys.path.append("..")
import CoreFiles.GeneralFunctions as GrlFct
from BuildObject.DB_Building import BuildingList
import BuildObject.DB_Data as DB_Data
from BuildObject.DB_Filter4Simulations import checkBldFilter
import matplotlib.pyplot as plt


def LaunchProcess(SimDir, DataBaseInput, LogFile, bldidx, keyPath, nbcase, CorePerim=False, FloorZoning=False,
                  FigCenter=(0, 0), WindSize=50, PlotBuilding=False):
    # process is launched for the considered building
    msg = 'Building ' + str(nbBuild) + ' is starting\n'
    print('#############################################')
    print(msg[:-1])
    GrlFct.Write2LogFile(msg, LogFile)
    MainPath = os.getcwd()
    epluspath = keyPath['epluspath']
    os.chdir(SimDir)
    StudiedCase = BuildingList()
    # lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath, LogFile,
                                                   PlotOnly=True)
    refName = 'Building_' + str(nbcase)
    for key in building_ref.BuildID:
        print(key + ' : ' + str(building_ref.BuildID[key]))
        refName += '\n ' + key + str(building_ref.BuildID[key])
    idf_ref.idfname = refName
    # Rounds of check if we continue with this building or not, see DB_Filter4Simulation.py if other filter are to add
    CaseOK = checkBldFilter(building_ref)

    if not CaseOK:
        msg = '[Error] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n'
        print(msg[:-1])
        os.chdir(MainPath)
        GrlFct.Write2LogFile(msg, LogFile)
        GrlFct.Write2LogFile('##############################################################\n', LogFile)
        return FigCenter, WindSize

    FigCenter.append(building_ref.RefCoord)
    refx = sum([center[0] for center in FigCenter]) / len(FigCenter)
    refy = sum([center[1] for center in FigCenter]) / len(FigCenter)

    if not PlotBuilding:
        a=1
        #building_ref.MaxShadingDist = 0
        # building_ref.shades = building_ref.getshade(DataBaseInput['Build'][nbcase], DataBaseInput['Shades'],
        #                                             DataBaseInput['Build'], DB_Data.GeomElement, [])#LogFile)
    GrlFct.setBuildingLevel(idf_ref, building_ref, LogFile, CorePerim, FloorZoning, ForPlots=True)
    GrlFct.setEnvelopeLevel(idf_ref, building_ref)
    FigCentroid = building_ref.RefCoord if PlotBuilding else (refx, refy)
    #we need to transform the prvious relatve coordinates into absolute one in order to make plot of several building keeping their location
    idf_ref, building_ref = GrlFct.MakeAbsoluteCoord(idf_ref,building_ref)

    # compåuting the window size for visualization
    for poly in building_ref.footprint:
        for vertex in poly:
            WindSize = max(GrlFct.ComputeDistance(FigCentroid, vertex), WindSize)

    surf = idf_ref.getsurfaces()
    ok2plot = False
    nbadiab = 0
    adiabsurf = []
    for s in surf:
        if s.Outside_Boundary_Condition == 'adiabatic':
            ok2plot = True
            if s.Name[:s.Name.index('_')] not in adiabsurf:
                adiabsurf.append(s.Name[:s.Name.index('_')])
                nbadiab += 1
    if ok2plot:
        GrlFct.Write2LogFile('[Nb Adjacent_Walls] This building has '+str(nbadiab)+' walls with adiabatic surfaces\n', LogFile)
    RoofSpecialColor = "firebrick"

    # with open('HamId.txt','r') as f:
    #     Lines = f.readlines()
    # Ids2look = [line[:-1] for line in Lines]
    # if building_ref.BuildID['50A_UUID'] in Ids2look:
    #     RoofSpecialColor = 'royalblue'
    idf_ref.view_model(test=PlotBuilding, FigCenter=FigCentroid, WindSize=2 * WindSize, RoofSpecialColor = RoofSpecialColor)

    GrlFct.Write2LogFile('##############################################################\n', LogFile)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)
    return (refx, refy), WindSize


if __name__ == '__main__':

    ######################################################################################################################
    ########        MAIN INPUT PART     ##################################################################################
    ######################################################################################################################
    # This file is only to make graphs of the building geometry given in the GoeJsonF

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

    import numpy as np
    BuildNum = []#,26,28,34,35]#[int(i) for i in np.linspace(5,10,6)]#[int(i) for i in np.linspace(0,3,4)]#[40,41,42,43,44,45,46,47,48,49]##[52]#,51,52,53]#[40,41,42,43,44,45,46,47,48,49]#[30,31,32,33,34,35,36,37,38,39]#[20,21,22,23,24,25,26,27,28,29]#[10,11,12,13,14,15,16,17,18,19]#[0,1,2,3,4,5,6,7,8,9]#[50,51,52,53]#
    PathInputFile = 'Minneberg2D.txt'#'ExergiProject1.txt'#'Hammarby0401.txt'#'Pathways_Template.txt'# 'Hammarby0401.txt'#'Pathways_Template.txt'#'Sodermalm4.txt'  #'MinnebergLast.txt'#'Minneberg2D.txt'#'Sodermalm4.txt'##
    CorePerim = False
    FloorZoning = True
    PlotBuilding = False
    ZoneOfInterest = ''

    ######################################################################################################################
    ########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
    ######################################################################################################################
    CaseName = 'ForTest'
    # reading the pathfiles and the geojsonfile
    GlobKey =[GrlFct.readPathfile(PathInputFile)]
    # lets see if the input file is a dir with several geojson files
    multipleFiles = False
    BuildingFiles,WallFiles = GrlFct.ReadGeoJsonDir(GlobKey[0])
    if BuildingFiles:
        multipleFiles = True
        MainRootPath = GlobKey[0]['Buildingsfile']
        GlobKey[0]['Buildingsfile'] = os.path.join(MainRootPath,BuildingFiles[0])
        GlobKey[0]['Shadingsfile'] = os.path.join(MainRootPath, WallFiles[0])
        for nb,file in enumerate(BuildingFiles[1:]):
            GlobKey.append(GlobKey[-1].copy())
            GlobKey[-1]['Buildingsfile'] = os.path.join(MainRootPath, file)
            GlobKey[-1]['Shadingsfile'] = os.path.join(MainRootPath, WallFiles[nb+1])

    for nbfile, keyPath in enumerate(GlobKey):
        # if nbfile not in [0]:
        #     continue
        if multipleFiles:
            nb = len(GlobKey)
            print('File number : '+str(nbfile) + ' which correspond to Area Ref : '+BuildingFiles[nbfile][:-18])
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
            if not plt.fignum_exists(0):
                FigCenter = []
                LogFile = []
                CurrentPath = os.getcwd()
                WindSize = 50
                SimDir = CurrentPath
                LogFile = open(os.path.join(SimDir, CaseName+'_Logs.log'), 'w')
            if multipleFiles:
                msg = '[New AREA] A new goejson file is open (num '+str(nbfile)+'), Area Id : '+BuildingFiles[nbfile][:-18]+'\n'
                print(msg[:-1])
                GrlFct.Write2LogFile(msg, LogFile)
            for idx, nbBuild in enumerate(BuildNum2Launch):
                if idx < len(DataBaseInput['Build']):
                    # getting through the mainfunction above :LaunchProcess() each building sees its idf done in a row within this function
                    try:
                        NewCentroid, WindSize = LaunchProcess(SimDir, DataBaseInput, LogFile, idx, keyPath, nbBuild,
                                                              CorePerim, FloorZoning,
                                                              FigCenter, WindSize, PlotBuilding)
                    except:
                        msg = '[Error] There was an error on this building, process aborted\n'
                        print(msg[:-1])
                        GrlFct.Write2LogFile(msg, LogFile)
                        GrlFct.Write2LogFile('##############################################################\n', LogFile)
                        os.chdir(CurrentPath)
                    # if choicies is done, once the building is finished parallel computing is launched for this one
                else:
                    print('All buildings in the input file have been treated.')
                    print('###################################################')
                    break
            if not multipleFiles:
                LogFile.close()
    plt.show()
    if multipleFiles:
        LogFile.close()
    sys.path.remove(path2addgeom)
