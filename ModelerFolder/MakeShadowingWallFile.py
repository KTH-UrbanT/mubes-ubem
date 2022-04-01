# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
import re

# #add the required path for geomeppy special branch
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
#add the reauired path for all the above folder
sys.path.append('..')
MUBES_Paths = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'MUBES_UBEM'))
sys.path.append(MUBES_Paths)

import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.setConfig as setConfig
from BuildObject.DB_Building import Building
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
        currIdx += 1
    return Config2Launch

def CreatePolygonEnviro(UUID,GlobKey):
    PolygonEnviro = {}
    for nbfile,keyPath in enumerate(GlobKey):
        PolygonEnviro[nbfile] = {'Bld_ID': [], 'EdgesHeights': [], 'FootPrint': [], 'BldNum': [], 'WindowSize': [],
                         'Centroid': []}
        PolygonEnviro[nbfile]['PathName'] = keyPath['Buildingsfile']
        Edges2Store = {}
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
        Size = len(DataBaseInput['Build'])-1
        print('Studying buildings file : '+os.path.basename(keyPath['Buildingsfile']))
        print('Urban Area under construction with:')
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            print('--building '+str(bldNum) +' / '+str(Size))
            BldObj = Building('Bld'+str(bldNum), DataBaseInput, bldNum, os.path.dirname(keyPath['Buildingsfile']),
                              keyPath['Buildingsfile'],LogFile=[],PlotOnly=False, DebugMode=False)
            PolygonEnviro[nbfile]['FootPrint'].append(BldObj.AggregFootprint)
            try: BldID = BldObj.BuildID['50A_UUID']
            except: BldID = 'BuildingIndexInFile:' + str(bldNum)
            PolygonEnviro[nbfile]['Bld_ID'].append(BldID)
            PolygonEnviro[nbfile]['BldNum'].append(bldNum)
            Edges2Store[bldNum] = BldObj.edgesHeights
        PolygonEnviro[nbfile]['EdgesHeights'] = Edges2Store
    return PolygonEnviro

def MakePointOutside(Edge,poly):
    p1 = Edge[0]
    p2 = Edge[1]
    epsilon = 1e-1
    resolution = 3
    x = round((p2[0] + p1[0]) / 2,resolution) + epsilon
    y = round((p2[1] + p1[1]) / 2,resolution) + epsilon
    if Polygon(poly).contains(Point(x,y)): #helper_fcts.inside_polygon(x, y, np.array(poly), border_value=False):
        x -= 2*epsilon
        y -= 2*epsilon
    return x,y

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
        print('Building ' + str(bldidx) + ' is currently treated')
        offsetidx = bldidx +1
        for bldidx1, bld1 in enumerate(NewBld[offsetidx:]):
            #print('Building ' + str(bldidx) + ' with building ' + str(bldidx1 + offsetidx))
            #lets grab the coarse box around the building
            x, y = zip(*bld1)
            bldBox = [(min(x),min(y)),(min(x),max(y)),(max(x),max(y)),(max(x),min(y))]
            for seg,vertex in enumerate(bld):
                StartingEdge = [vertex, bld[(seg + 1) % len(bld)]]
                #lets make the tsarting point
                x, y = MakePointOutside(StartingEdge, np.array(bld))
                start_coordinates = (x, y)
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
                    if seg == 18 and seg1 == 6:
                        toto = 1
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
                        x, y = MakePointOutside(EndingEdge, np.array(bld1))
                        goal_coordinates = (x, y)
                        Ray = LineString([start_coordinates, goal_coordinates])
                        for bldunit in NewBld:
                            Visible = True
                            if Polygon(bldunit).intersection(Ray):
                                Visible = False
                                break
                        if not Visible:
                            continue
                        else:
                            if edgeidx ==26:
                                a=1
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
                                if edgeidx == 26:
                                    a = 1
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

    j = json.dumps(Matches)
    PathName = os.path.dirname(Data['PathName'])
    FileName = os.path.basename(Data['PathName'])
    with open(os.path.join(PathName,FileName[:FileName.index('.')]+'_Walls.json'), 'w') as f:
        f.write(j)
    import pickle
    with open(os.path.join(PathName,FileName[:FileName.index('.')]+'_Walls.pickles'), 'wb') as handle:
        pickle.dump(Matches, handle, protocol=pickle.HIGHEST_PROTOCOL)
    #
    # json.dump(Matches, open(os.path.join(PathName,FileName[:FileName.index('.')]+'_WallsBis.json'), "w"))

    return Matches,NewBld

if __name__ == '__main__' :

    ######################################################################################################################
    ########        MAIN INPUT PART  (choices from the modeler)   ########################################################
    ######################################################################################################################
    #The Modeler have to fill in the following parameter to define his choices

    # CaseName = 'String'                   #name of the current study (the ouput folder will be renamed using this entry)
    # BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
    #                                       geojsonfile), if empty, all building in the geojson file will be considered
    # VarName2Change = ['String','String']  #list of strings: Variable names (same as Class Building attribute, if different
    #                                       see LaunchProcess 'for' loop for examples)
    # Bounds = [[x1,y1],[x2,y2]]            #list of list of 2 values  :bounds in which the above variable will be allowed to change
    # NbRuns = 1000                         #number of run to launch for each building (all VarName2Change will have automotaic
    #                                       allocated value (see sampling in LaunchProcess)
    # CPUusage = 0.7                        #factor of possible use of total CPU for multiprocessing. If only one core is available,
    #                                       this value should be 1
    # CreateFMU = False / True             #True = FMU are created for each building selected to be computed in BuildNum
    #                                       #no simulation will be run but the folder CaseName will be available for the FMUSimPlayground.py
    # CorePerim = False / True             #True = create automatic core and perimeter zonning of each building. This options increases in a quite
    #                                       large amount both building process and simulation process.
    #                                       It can used with either one zone per floor or one zone per heated or none heated zone
    #                                       building will be generated first, all results will be saved in one single folder
    # FloorZoning = False / True            True = thermal zoning will be realized for each floor of the building, if false, there will be 1 zone
    #                                       for the heated volume and, if present, one zone for the basement (non heated volume
    # PathInputFile = 'String'              #Name of the PathFile containing the paths to the data and to energyplus application (see ReadMe)
    # OutputsFile = 'String'               #Name of the Outfile with the selected outputs wanted and the associated frequency (see file's template)
    # ZoneOfInterest = 'String'             #Text file with Building's ID that are to be considered withoin the BuildNum list, if '' than all building in BuildNum will be considered

    #these are default values :
    #UUID,DESO,CaseName,DataPath = Read_Arguments()
    ConfigFromAPI = Read_Arguments()
    config = setConfig.read_yaml(os.path.join(os.path.dirname(os.getcwd()),'CoreFiles','DefaultConfig.yml'))
    CaseChoices = config['SIM']['CaseChoices']

    if ConfigFromAPI:
        config = setConfig.ChangeConfigOption(config, ConfigFromAPI)
        CaseChoices['OutputFile'] = 'Outputs4API.txt'
    else:
        config = setConfig.check4localConfig(config, os.getcwd())
    config = setConfig.checkGlobalConfig(config)
    if type(config) != dict:
        print('Something seems wrong in : ' + config)
        sys.exit()
    epluspath = config['APP']['PATH_TO_ENERGYPLUS']
    #a first keypath dict needs to be defined to comply with the current paradigme along the code
    Buildingsfile = os.path.abspath(config['DATA']['Buildingsfile'])
    Shadingsfile = os.path.abspath(config['DATA']['Shadingsfile'])
    keyPath =  {'epluspath': epluspath, 'Buildingsfile': Buildingsfile, 'Shadingsfile': Shadingsfile,'pythonpath': '','GeojsonProperties':''}
    #this function makes the list of dictionnary with single input files if several are present inthe sample folder
    GlobKey, MultipleFiles = GrlFct.ListAvailableFiles(keyPath)
    #this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    print('Urban Area is first build by aggregatong all building in each geojson files')
    PolygonEnviro = CreatePolygonEnviro(CaseChoices['UUID'],GlobKey)
    print('Lets compute, for each building the shadowing surfaces from others')
    for Enviro in PolygonEnviro:
        computMatchesNew(PolygonEnviro[Enviro])
    print('Wall file created in the same folder of the Building file. see ***.json file')