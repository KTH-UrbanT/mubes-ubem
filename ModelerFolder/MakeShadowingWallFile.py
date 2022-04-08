# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
import re
import yaml
import shutil

# #add the required path for geomeppy special branch
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add the reauired path for all the above folder
sys.path.append('..')
MUBES_Paths = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'MUBES_UBEM'))
sys.path.append(MUBES_Paths)

import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.setConfig as setConfig
from BuildObject.BuildingObject import Building
import numpy as np
import json
from shapely.geometry import Polygon, LineString, Point


def Read_Arguments_Old():
    #these are defaults values:
    UUID = []
    DESO = []
    CaseName = []
    DataPath = []
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-UUID')):
            currIdx += 1
            UUID = sys.argv[currIdx]
        elif (currArg.startswith('-DESO')):
            currIdx += 1
            DESO = int(sys.argv[currIdx])
        elif (currArg.startswith('-CaseName')):
            currIdx += 1
            CaseName = sys.argv[currIdx]
        elif (currArg.startswith('-DataPath')):
            currIdx += 1
            DataPath = sys.argv[currIdx]
        currIdx += 1

    ListUUID = re.findall("[^,]+", UUID) if UUID else []

    return ListUUID,DESO,CaseName,DataPath

def Read_Arguments():
    #these are defaults values:
    Config2Launch = []
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-CONFIG')):
            currIdx += 1
            Config2Launch = json.loads(sys.argv[currIdx])
        if (currArg.startswith('-yml')):
            currIdx += 1
            Config2Launch = sys.argv[currIdx]
            return Config2Launch
        if (currArg.startswith('-geojson')):
            currIdx += 1
            Config2Launch = sys.argv[currIdx]
            return Config2Launch
        currIdx += 1
    return Config2Launch

def CreatePolygonEnviro(UUID,GlobKey,config):
    PolygonEnviro = {}
    MainPath = os.getcwd()
    TotalSimDir = []
    for nbfile,keyPath in enumerate(GlobKey):
        #we need to create a temporary folder to stor the log file if needed
        SimDir = os.path.join(os.path.dirname(keyPath['Buildingsfile']),'Temp')
        if not os.path.isdir(SimDir):
            os.mkdir(SimDir)
        os.chdir(SimDir)
        with open(os.path.join(SimDir, 'ConfigFile.yml'), 'w') as file:
            documents = yaml.dump(config, file)
        PolygonEnviro[nbfile] = {'Bld_ID': [], 'EdgesHeights': [], 'FootPrint': [], 'BldNum': [], 'WindowSize': [],
                         'Centroid': []}
        PolygonEnviro[nbfile]['PathName'] = keyPath['Buildingsfile']
        Edges2Store = {}
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
        Size = len(DataBaseInput['Build'])-1
        print('Studying buildings file : '+os.path.basename(keyPath['Buildingsfile']))
        print('Urban Area under construction with:')
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            print('\r', end='')
            print('--building '+str(bldNum) +' / '+str(Size), end='', flush=True)
            BldObj = Building('Bld'+str(bldNum), DataBaseInput, bldNum, SimDir,keyPath['Buildingsfile'],LogFile=[],PlotOnly=True, DebugMode=False)
            PolygonEnviro[nbfile]['FootPrint'].append(BldObj.AggregFootprint)
            try: BldID = BldObj.BuildID['50A_UUID']
            except: BldID = 'BuildingIndexInFile:' + str(bldNum)
            PolygonEnviro[nbfile]['Bld_ID'].append(BldID)
            PolygonEnviro[nbfile]['BldNum'].append(bldNum)
            Edges2Store[bldNum] = BldObj.edgesHeights
        print('\nUrban area constructed')
        PolygonEnviro[nbfile]['EdgesHeights'] = Edges2Store
        TotalSimDir.append(SimDir)
    return PolygonEnviro,TotalSimDir

def MakePointOutside(Edge,poly):
    p1 = Edge[0]
    p2 = Edge[1]
    epsilon = 1e-1
    resolution = 3
    x = round((p2[0] + p1[0]) / 2,resolution) + epsilon
    y = round((p2[1] + p1[1]) / 2,resolution) + epsilon
    x1 = round((0.95*p2[0] + 0.05*p1[0]), resolution) + epsilon
    y1 = round((0.95*p2[1] + 0.05*p1[1]), resolution) + epsilon
    x2 = round((0.05*p2[0] + 0.95*p1[0]), resolution) + epsilon
    y2 = round((0.05*p2[1] + 0.95*p1[1]), resolution) + epsilon
    if Polygon(poly).contains(Point(x,y)): #helper_fcts.inside_polygon(x, y, np.array(poly), border_value=False):
        x -= 2*epsilon
        y -= 2*epsilon
        x1 -= 2 * epsilon
        y1 -= 2 * epsilon
        x2 -= 2 * epsilon
        y2 -= 2 * epsilon
    return (x,y),(x1,y1),(x2,y2)

def isEdgeDone(Matches,Edge):
    p1 = Edge[0]
    p2 = Edge[1]
    edgeIdx = [idx+1 for idx,Shade in enumerate(Matches.keys()) if [p1, p2] == Matches[Shade]['RelCoord'] or [p2, p1] == Matches[Shade]['RelCoord']]
    if len(edgeIdx)>1:
        print('heu...error in the index caught forthe edges done or not...several locations')
    return edgeIdx[0] if edgeIdx else False

def isBldDone(Matches,EdgeIdx,Bld):
    BldDone = 0
    if EdgeIdx:
        BldDone = Bld in Matches[EdgeIdx]['RecepientBld_ID']
    return BldDone

def signed_area(pr2):
    """Return the signed area enclosed by a ring using the linear time
    algorithm at http://www.cgafaq.info/wiki/Polygon_Area. A value >= 0
    indicates a counter-clockwise oriented ring."""
    xs, ys = map(list, zip(*pr2))
    xs.append(xs[1])
    ys.append(ys[1])
    return sum(xs[i] * (ys[i + 1] - ys[i - 1]) for i in range(1, len(pr2))) / 2.0

def checkEdgeOrientation(Edge,Point):
    p1 = Edge[0]
    p2 = Edge[1]
    a = (p2[1]-p1[1])/(p2[0]-p1[0])
    b = p2[1]-a*p2[0]
    #make test with x
    if Point[1]-(a * Point[0] + b)>0:
        Orientation = 1
    else:
        Orientation = -1
    return a,b,Orientation

def computMatchesNew(Data):
    NewBld = []
    for bld in Data['FootPrint']:
        # if signed_area(bld) > 0: #this was usfule for the initial method, with shapely, I don't really know (didn't try without yet)
        #     bld.reverse()
        NewBld.append(bld[:-1])
    #lets compute distances now with starting points from all segments for all polygons and ending point all semgent of all polygons except the current one
    print('Computing visible surfaces...')
    NbEdges = 0
    for i in Data['EdgesHeights'].keys():
        NbEdges += len(Data['EdgesHeights'][i]['Edge'])
    Matches = {}
    for i in range(1,NbEdges+1):
        Matches[i] = {'RelCoord': [], 'AbsCoord': [], 'OwnerBld_ID': [],
                    'RecepientBld_ID': [], 'Height': [], 'Rays': []}
    edgeidx = 1
    for bldidx,bld in enumerate(NewBld[:-1]):
        print('\r', end='')
        print('Building ' + str(bldidx) + ' is currently treated', end='', flush=True)
        offsetidx = bldidx +1
        for bldidx1, bld1 in enumerate(NewBld[offsetidx:]):
            #print('Building ' + str(bldidx) + ' with building ' + str(bldidx1 + offsetidx))
            #lets grab the coarse box around the building
            x, y = zip(*bld1)
            bldBox = [(min(x),min(y)),(min(x),max(y)),(max(x),max(y)),(max(x),min(y))]
            for seg,vertex in enumerate(bld):
                StartingEdge = [vertex, bld[(seg + 1) % len(bld)]]
                #lets make the tsarting point
                start_coordinates,s1,s2 = MakePointOutside(StartingEdge, np.array(bld))
                a, b, Orientation = checkEdgeOrientation(StartingEdge,start_coordinates)
                #lets check if the building is in the view of the segde
                Bldvisible = False
                for bldvertex in bldBox:
                    Ray = LineString([start_coordinates, bldvertex])
                    if not Polygon(bld).intersection(Ray):
                        Bldvisible = True
                        break
                if not Bldvisible:
                    continue
                for seg1, vertex1 in enumerate(bld1):
                    EndingEdge = [vertex1, bld1[(seg1 + 1) % len(bld1)]]
                    #MakeIntermediateFig(bld, bld1, bldBox, StartingEdge, EndingEdge)
                    #define if there is a need to go into this edge
                    test1 = EndingEdge[0][1]-a*EndingEdge[0][0]-b
                    test2 = EndingEdge[1][1]-a*EndingEdge[1][0]-b
                    if (test1<0 and test2 < 0 and Orientation > 0) or (test1>0 and test2 > 0 and Orientation < 0):
                        continue
                    #lets check if this edge has already been treated, just to append the list of recipient only
                    EdgeDone = isEdgeDone(Matches, EndingEdge)
                    #lets check if the current building has already been treated for the edge and building (reciprocity from the first analyses)
                    BldDone = isBldDone(Matches, EdgeDone, Data['Bld_ID'][bldidx])
                    if EdgeDone and not BldDone or not EdgeDone:
                        goal_coordinates,g1,g2 = MakePointOutside(EndingEdge, np.array(bld1))
                        #the five Ray below are to consider either the middle point of the edge point (being 5% form the edges (see MakePointOutside())
                        Raym = LineString([start_coordinates, goal_coordinates])
                        Ray11 = LineString([s1, g1])
                        Ray12 = LineString([s1, g2])
                        Ray21 = LineString([s2, g1])
                        Ray22 = LineString([s2, g2])
                        for bldunit in NewBld:
                            Visible = True
                            if Polygon(bldunit).intersection(Ray11) and Polygon(bldunit).intersection(Ray12) and \
                                Polygon(bldunit).intersection(Ray21) and Polygon(bldunit).intersection(Ray22):
                                Visible = False
                                break
                        if not Visible:
                            continue
                        else:
                            #MakeIntermediateFig(bld, bld1, bldBox, StartingEdge, EndingEdge)
                            if not EdgeDone:
                                #lets feed the disctionnary for this edge
                                Matches[edgeidx]['RelCoord'] = EndingEdge
                                Matches[edgeidx]['AbsCoord'] = Data['EdgesHeights'][bldidx1+offsetidx]['Edge'][seg1]
                                Matches[edgeidx]['Height'] = Data['EdgesHeights'][bldidx1 + offsetidx]['Height'][seg1]
                                Matches[edgeidx]['OwnerBld_ID'] = Data['Bld_ID'][bldidx1 + offsetidx]
                                Matches[edgeidx]['RecepientBld_ID'].append(Data['Bld_ID'][bldidx])
                                Matches[edgeidx]['Rays'].append([start_coordinates,goal_coordinates])
                                edgeidx += 1
                                #lets feed the reciprocity as well
                                EdgeDone = isEdgeDone(Matches, StartingEdge)
                                BldDone = isBldDone(Matches, EdgeDone, Data['Bld_ID'][bldidx1 + offsetidx])
                                if not EdgeDone:
                                    Matches[edgeidx]['RelCoord'] = StartingEdge
                                    Matches[edgeidx]['AbsCoord'] = Data['EdgesHeights'][bldidx]['Edge'][seg]
                                    Matches[edgeidx]['Height'] = Data['EdgesHeights'][bldidx]['Height'][seg]
                                    Matches[edgeidx]['OwnerBld_ID'] = Data['Bld_ID'][bldidx]
                                    Matches[edgeidx]['RecepientBld_ID'].append(Data['Bld_ID'][bldidx1 + offsetidx])
                                    Matches[edgeidx]['Rays'].append([start_coordinates, goal_coordinates])
                                    edgeidx += 1
                                elif not BldDone:
                                    Matches[EdgeDone]['RecepientBld_ID'].append(Data['Bld_ID'][bldidx1 + offsetidx])
                                    Matches[EdgeDone]['Rays'].append([start_coordinates, goal_coordinates])
                            else:
                                Matches[EdgeDone]['RecepientBld_ID'].append(Data['Bld_ID'][bldidx])
                                Matches[EdgeDone]['Rays'].append([start_coordinates, goal_coordinates])

    print('\nAll building treated')
    j = json.dumps(Matches)
    PathName = os.path.dirname(Data['PathName'])
    FileName = os.path.basename(Data['PathName'])
    with open(os.path.join(PathName,FileName[:FileName.index('.')]+'_Walls.json'), 'w') as f:
        f.write(j)
    # import pickle
    # with open(os.path.join(PathName,FileName[:FileName.index('.')]+'_Walls.pickles'), 'wb') as handle:
    #     pickle.dump(Matches, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return Matches,NewBld

def cleaningTempFolders(SimDir):
    for Folder in SimDir:
        #empyting the files being inside"
        Liste = os.listdir(Folder)
        for file in Liste:
            os.remove(os.path.join(Folder,file))
        #remove the folder
        os.rmdir(Folder)


if __name__ == '__main__' :
    MainPath = os.getcwd()
    ConfigFromArg = Read_Arguments()
    config = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()),'CoreFiles','DefaultConfig.yml'))
    configUnit = setConfig.read_yaml(
        os.path.join(os.path.dirname(os.getcwd()), 'CoreFiles', 'DefaultConfigKeyUnit.yml'))
    geojsonfile = False
    print(ConfigFromArg)
    if type(ConfigFromArg) == str and ConfigFromArg[-4:] == '.yml':
        localConfig = setConfig.read_yaml(ConfigFromArg)
        config = setConfig.ChangeConfigOption(config, localConfig)
    elif type(ConfigFromArg) == str and ConfigFromArg[-8:] == '.geojson':
        geojsonfile = True
    elif ConfigFromArg:
        config = setConfig.ChangeConfigOption(config, ConfigFromArg)
    else:
        config,filefound,msg = setConfig.check4localConfig(config, os.getcwd())
        if msg: print(msg)
        print('[Config Info] Config complted by ' + filefound)
    config = setConfig.checkConfigUnit(config, configUnit)
    if type(config) != dict:
        print('[Config Error] Something seems wrong : \n' + config)
        sys.exit()
    config, SepThreads = setConfig.checkGlobalConfig(config)
    if type(config) != dict:
        print('[Config Error] Something seems wrong in : ' + config)
        sys.exit()
        # the config file is now validated, lets vreate a smaller dict that will called along the process
    Key2Aggregate = ['0_GrlChoices', '1_SimChoices', '2_AdvancedChoices']
    CaseChoices = {}
    for key in Key2Aggregate:
        for subkey in config['2_CASE'][key]:
            CaseChoices[subkey] = config['2_CASE'][key][subkey]
    if CaseChoices['Verbose']: print('[OK] Input config. info checked and valid.')
    epluspath = config['0_APP']['PATH_TO_ENERGYPLUS']
    #a first keypath dict needs to be defined to comply with the current paradigme along the code
    Buildingsfile = os.path.abspath(config['1_DATA']['PATH_TO_DATA'])
    keyPath =  {'epluspath': epluspath, 'Buildingsfile': Buildingsfile,'pythonpath': '','GeojsonProperties':''}
    if geojsonfile:
        keyPath['Buildingsfile'] = ConfigFromArg
    #this function makes the list of dictionnary with single input files if several are present inthe sample folder
    GlobKey, MultipleFiles = GrlFct.ListAvailableFiles(keyPath)
    #this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    print('Urban Area is first build by aggregating all building in each geojson files')
    PolygonEnviro,Folders2Clean = CreatePolygonEnviro(CaseChoices['BldID'],GlobKey,config)
    print('Lets compute, for each building the shadowing surfaces from others')
    for Enviro in PolygonEnviro:
        computMatchesNew(PolygonEnviro[Enviro])
    os.chdir(MainPath)
    cleaningTempFolders(Folders2Clean)
    print('Wall file created in the same folder of the Building file. see ***.json file')