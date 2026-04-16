# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
import re

# #add the required path for geomeppy special branch
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))),'geomeppy')
sys.path.append(path2addgeom)
#add the reauired path for all the above folder
sys.path.append('..')
MUBES_Paths = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(MUBES_Paths)

import core.GeneralFunctions as GrlFct
import core.CaseBuilder_OAT as CB_OAT
import core.setConfig as setConfig
from shapely.geometry import Polygon
import building_geometry.GeomUtilities as GeomUtilities
import math
import json
import yaml
import copy
import matplotlib.pyplot as plt


def giveReturnFromPool(results):
    doNothing = 0
    print(results)

def getBasePlayGround():
    CurrentPath = os.getcwd()
    localDir = os.path.join(MUBES_Paths,'bin')
    os.chdir(localDir)
    CaseChoices,config, SepThreads,Pool2Launch, MultipleFiles = setConfig.getConfig(localDir)
    os.chdir(CurrentPath)
    File2Launch = {0:[]}
    for idx,Case in enumerate(Pool2Launch):
        keypath = Case['keypath']
        pythonpath = keypath['pythonpath']
        nbBuild = Case['BuildNum2Launch'] #this will be used in case the file has to be read again (launched through prompt cmd)
        CaseChoices['FirstRun'] = True
        #First, lets create the folder for the building and simulation processes
        SimDir = GrlFct.CreateSimDir(CurrentPath, config['0_APP']['PATH_TO_RESULTS'],CaseChoices['CaseName'],
                    SepThreads, nbBuild, idx, Refresh=CaseChoices['RefreshFolder'],Verbose = CaseChoices['Verbose'])
        #lest create the local yml file that will be used afterward
        if not os.path.isfile((os.path.join(SimDir,'ConfigFile.yml'))) or idx ==0:
            LocalConfigFile = copy.deepcopy(config)
            writeIds = False
            if CaseChoices['NbRuns'] >1:
                LocalConfigFile['2_CASE']['1_SimChoices']['BldID'] = CaseChoices['BldID'][idx]
            else:
                if len(CaseChoices['BldID'])>10:
                    LocalConfigFile['2_CASE']['1_SimChoices']['BldID'] = '# See ListOfBuiling_Ids.txt for list of IDs '
                    writeIds = True
                else:
                    LocalConfigFile['2_CASE']['1_SimChoices']['BldID'] = CaseChoices['BldID']
                if CaseChoices['VarName2Change']:
                    if CaseChoices['Verbose']: print('[Info] It seems that at least one parameter is to be changed but only one simulation is asked. Parameter default values will be used. ')
                CaseChoices['VarName2Change'] = []
            with open(os.path.join(SimDir,'ConfigFile.yml'), 'w') as file:
                documents = yaml.dump(LocalConfigFile, file)
        if CaseChoices['DataBaseInput']['Build'][idx].properties['allowVolumeModification']:
            File2Launch[0].append({'nbBuild': nbBuild, 'keypath': keypath, 'SimDir': SimDir, 'BuildID': Case['BuildID']})
    # #lets write a file for the building IDs as it can be very long.
    if writeIds:
        if CaseChoices['Verbose']: print('[Prep.Info] Writing List of Building''s ID file')
        for nbfile,ListKey in enumerate(File2Launch):
            with open(os.path.join(File2Launch[ListKey][0]['SimDir'],'ListOfBuiling_Ids.txt'),'w') as f:
                msg = 'SimNum' + '\t' + 'BldID_'+str(CaseChoices['BldIDKey'])
                f.write(msg + '\n')
                for file in File2Launch[ListKey]:
                    msg = str(file['nbBuild']) + '\t' + str(file['BuildID'])
                    f.write(msg+'\n')
    GlobPlayGround= {}
    for file_idx,file in enumerate(File2Launch[0]):
        BldObj,IDFObj,Check = CB_OAT.LaunchOAT(CaseChoices, file['SimDir'], file['keypath'], file['nbBuild'], [1], 0,
                                                    pythonpath,MakePlotOnly = True)
        BldObj = GrlFct.MakeAbsoluteCoord(BldObj)
        Id,Data = getNeededBase(BldObj,CaseChoices['DataBaseInput']['Build'][file['nbBuild']])
        GlobPlayGround[Id] = Data
    os.chdir(CurrentPath)
    GrlFct.CleanUpLogFiles(file['SimDir'])
    return GlobPlayGround

def getNeededBase(bld,GeoFeature):
    BldID = bld.BuildID[bld.BuildID['BldIDKey']]
    PlayGround = {}
    PlayGround['TowerAlt'] = max(bld.BlocMaxAlt)
    PlayGround['FootPrint'] = bld.AggregFootprint
    box = Polygon(bld.AggregFootprint).minimum_rotated_rectangle
    # lets make it a tiny wider to ensure that it contains the initial polygon
    box = box.buffer(0.001)  # the buufer shall be below the distance tolerance used further in MUBES !
    box1 = box.minimum_rotated_rectangle
    if box1.contains(Polygon(bld.AggregFootprint)):
        PlayGround['BoxCoord'] = [(x, y) for x, y in box1.exterior.coords]
        edge1 = (PlayGround['BoxCoord'][0], PlayGround['BoxCoord'][1])
        edge2 = (PlayGround['BoxCoord'][0],
                 (PlayGround['BoxCoord'][0][0] + 10, PlayGround['BoxCoord'][0][1]))
        angle = GeomUtilities.getAngle(edge1, edge2)
        PlayGround['RefAngle'] = angle if PlayGround['BoxCoord'][0][1] < PlayGround['BoxCoord'][1][
            1] else -angle
        PlayGround['Origin'] = PlayGround['BoxCoord'][0]
        PlayGround['EdgeLength'] = (GeomUtilities.getDistance(edge1[0], edge1[1]),
                                           GeomUtilities.getDistance(edge2[0], PlayGround['BoxCoord'][-2]))
    keys = ['maxHeight', 'minHeight', 'maxFootprint_m2', 'minFootprint_m2']
    for key in keys:
        PlayGround[key] = GeoFeature.properties[key]
    PlayGround = getFilteredVal(PlayGround)
    return BldID, PlayGround

def getFilteredVal(Bld):
    #lets defined the normalized value in wich the min and max area are possible to restraint the range of possibility for optimization
    Bld['maxFootprint_m2'] = min(int(0.5*Polygon(Bld['FootPrint']).area),Bld['maxFootprint_m2'])
    PossibleArea = [Bld['minFootprint_m2'],Bld['maxFootprint_m2']]
    shapeFactor = [0.99,1]
    edge1 = (PossibleArea[0]/shapeFactor[0])**0.5
    edge2 = edge1*shapeFactor[0]
    DistLim = min(edge1,edge2)/2
    Bld['DistLim'] = DistLim/min(Bld['EdgeLength'])
    Bld = getMatrixOfSpace(Bld)
    return Bld

def getMatrixOfSpace(Bld):
    import numpy as np
    PossibleArea = np.linspace(Bld['minFootprint_m2'], Bld['maxFootprint_m2'],10)
    shapeFactor = [0.8,0.9,1,1.1,1.2]
    # SpaceOfSol = np.arange(100*100*9*len(PossibleArea)*len(shapeFactor))
    # SpaceOfSol = np.reshape(SpaceOfSol, (100, 100, 9, len(PossibleArea), len(shapeFactor)))
    SpaceOfSolNew = {}
    for A,area in enumerate(PossibleArea):
        area = int(area)
        SpaceOfSolNew[area] = {}
        for sf,SFact in enumerate(shapeFactor):
            SpaceOfSolNew[area][SFact] = {}
            for angle in range(9):
                SpaceOfSolNew[area][SFact][angle] = []
                for x in range(100):
                    for y in range(100):
                        if checkTower(Bld, x=x/100, y=y/100, height=9, area=area, shapeF=SFact, angle=angle*10):
                            # SpaceOfSol[x,y,angle,A,sf] = 1
                            SpaceOfSolNew[area][SFact][angle].append((x,y))
                        # else:
                        #     SpaceOfSol[x, y, angle, A, sf] = 0
    # Bld['Space'] = SpaceOfSol
    Bld['SpaceNew'] = SpaceOfSolNew
    return Bld

def arrangePlayGround(GlobPlayGround):
    keys = ['BldID','BoxCoord','FootPrint','RefAngle','Origin']
    PlayGround = {}
    for bld in GlobPlayGround:
        BldID = bld.BuildID[bld.BuildID['BldIDKey']]
        PlayGround[BldID] = {}
        PlayGround[BldID]['FootPrint'] = bld.AggregFootprint
        box = Polygon(bld.AggregFootprint).minimum_rotated_rectangle
        #lets make it a tiny wider to ensure that it contains the initial polygon
        box = box.buffer(0.001) #the buufer shall be below the distance tolerance used further in MUBES !
        box1 = box.minimum_rotated_rectangle
        if box1.contains(Polygon(bld.AggregFootprint)):
            PlayGround[BldID]['BoxCoord'] = [(x, y) for x, y in box1.exterior.coords]
            edge1 = (PlayGround[BldID]['BoxCoord'][0],PlayGround[BldID]['BoxCoord'][1])
            edge2 = (PlayGround[BldID]['BoxCoord'][0],(PlayGround[BldID]['BoxCoord'][0][0]+10,PlayGround[BldID]['BoxCoord'][0][1]))
            angle = GeomUtilities.getAngle(edge1,edge2)
            PlayGround[BldID]['RefAngle'] = angle if PlayGround[BldID]['BoxCoord'][0][1]<PlayGround[BldID]['BoxCoord'][1][1] else -angle
            PlayGround[BldID]['Origin'] = PlayGround[BldID]['BoxCoord'][0]
            PlayGround[BldID]['EdgeLength'] = (GeomUtilities.getDistance(edge1[0],edge1[1]),GeomUtilities.getDistance(edge2[0],PlayGround[BldID]['BoxCoord'][-2]))
    return PlayGround

def checkTower(Bld,x=0.5,y=0.5,height=9,area=500,shapeF = 2,angle = 0):
    UpperTower = checkTowerLocation(Bld, x=x, y=y, height=height,
                                                       area=area, shapeF=shapeF, angle=angle)
    if Polygon(Bld['FootPrint']).contains(Polygon(UpperTower['Coord'])):
        return True
    else: return False

def checkTowerLocation(Bld,x=0.5,y=0.5,height=9,area=500,shapeF = 2,angle = 0):
    X,Y = makeGlobCoord(x,y,Bld) #centroid of the tower on the base
    #make the square shape
    #it requires a bounds for a shape factor (lets use 0.2 and 5, with a minimum of 5m for smallest edge length)
    #these should be given in the geojson file as can be specific to the building
    #computing the length of the edges
    edge1 = (area/shapeF)**0.5
    edge2 = edge1*shapeF
    Coord = [(-edge1/2,-edge2/2),(-edge1/2,edge2/2),(edge1/2,edge2/2),(edge1/2,-edge2/2)]
    Coord = [(rotateCoord(node,angle)) for node in Coord]
    TowerCoord = [(node[0]+X,node[1]+Y) for node in Coord]
    return  {'Coord' : TowerCoord, 'Height' : height}


def rotateCoord(node,angle):
    X = node[0] * math.cos(math.radians(angle)) - node[1] * math.sin(math.radians(angle))
    Y = node[0] * math.sin(math.radians(angle)) + node[1] * math.cos(math.radians(angle))
    return X,Y

def makeGlobCoord(x,y,Bld):
    # lets transform x and y into global coordinates
    # get x and y with value sized to the figure
    x = x * Bld['EdgeLength'][0]
    y = y * Bld['EdgeLength'][1]
    # rotation transformation
    X,Y = rotateCoord((x, y), Bld['RefAngle'])
    #translation transformation
    X += Bld['Origin'][0]
    Y += Bld['Origin'][1]
    return (X,Y)

def Makeplot(poly):
    x, y = zip(*poly)
    plt.plot(x, y, '.-')

def SaveAndWrite(Matches):
    print('\nAll building treated')
    import pickle
    with open(os.path.join(MUBES_Paths,'bin','UpperTower.pickle'), 'wb') as handle:
        pickle.dump(Matches, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # for key in Matches.keys():
    #     del Matches[key]['Space']
    # j = json.dumps(Matches)
    # with open(os.path.join(MUBES_Paths,'ModelerFolder','UpperTower.json'), 'w') as f:
    #     f.write(j)

def SaveAndWriteNew(Matches,Towers):
    for key in Matches.keys():
        Matches[key]['UpperTower'] = Towers[key]
    print('\nAll building treated')
    for key in Matches.keys():
        del Matches[key]['Space']
        del Matches[key]['SpaceNew']
    j = json.dumps(Matches)
    with open(os.path.join(MUBES_Paths,'ModelerFolder','UpperTower.json'), 'w') as f:
        f.write(j)

def forFun():
    TestCase = {}
    PlayGround = getBasePlayGround()
    SaveAndWrite(PlayGround)
    # for Bld in PlayGround.keys():
    #     done = False
    #     for x in range(0, 100):
    #         for y in range(0, 100):
    #             for teta in range(36):
    #                 PlayGround[Bld]['UpperTower'] = checkTowerLocation(PlayGround[Bld], x=x / 100, y=y / 100, height=30,
    #                                                                    area=300, shapeF=0.2, angle=teta * 10)
    #                 if Polygon(PlayGround[Bld]['FootPrint']).contains(Polygon(PlayGround[Bld]['UpperTower']['Coord'])):
    #                     # Makeplot(PlayGround[Bld]['BoxCoord'])
    #                     # Makeplot(PlayGround[Bld]['FootPrint'])
    #                     # Makeplot(PlayGround[Bld]['UpperTower']['Coord'])
    #                     # plt.show()
    #                     done = True
    #                 if done: break
    #             if done: break
    #         if done: break
    #     if not done:
    #         PlayGround[Bld]['UpperTower']['Coord'] = []
    #         print('Bld failed : '+str(Bld))
    #     else: print('Bld finished : '+str(Bld))
    # SaveAndWrite(PlayGround)

if __name__ == '__main__' :
    forFun()
