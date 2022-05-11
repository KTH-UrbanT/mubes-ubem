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
from geomeppy.geom.polygons import Polygon2D
import CoreFiles.setConfig as setConfig
from BuildObject.BuildingObject import Building
import numpy as np
import json
from shapely.geometry import Polygon, LineString, Point

import matplotlib.pyplot as plt

def MakeIntermediateFig(bld, bld1, bldunit,StartingEdge, EndingEdge):
    plt.figure()
    x,y = zip(*bld)
    plt.plot(x,y,'k-')
    x, y = zip(*bld1)
    plt.plot(x, y, 'b-')
    x, y = zip(*bldunit)
    plt.plot(x, y, 'y-')
    x, y = zip(*StartingEdge)
    plt.plot(x, y, 's-')
    x, y = zip(*EndingEdge)
    plt.plot(x, y, 's-')
    plt.show()

def CreatePolygonEnviro(GlobKey,config,WithBackSide = True):
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
        PolygonEnviro[nbfile] = {'Bld_ID': [], 'EdgesAndHeights': [], 'Bld_Height': [],'BlocNum':[],
                            'AggregFootPrint':[],'FootPrint': [], 'BldNum': [], 'WindowSize': [],
                            'Centroid': []}
        PolygonEnviro[nbfile]['PathName'] = keyPath['Buildingsfile']
        Edges2Store = {}
        NewEdges2Store = {}
        DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath,config['1_DATA']['EPSG_REF'])
        Size = len(DataBaseInput['Build'])
        print('Studying buildings file : '+os.path.basename(keyPath['Buildingsfile']))
        print('Urban Area under construction with:')
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            print('\r', end='')
            print('--building '+str(bldNum+1) +' / '+str(Size), end='', flush=True)
            try: BldObj = Building('Bld'+str(bldNum), DataBaseInput, bldNum, SimDir,keyPath['Buildingsfile'],LogFile=[],PlotOnly=True, DebugMode=False)
            except: continue
            BldObj = GrlFct.MakeAbsoluteCoord(BldObj,roundfactor=4)
            BldID = BldObj.BuildID[BldObj.BuildID['BldIDKey']]
            if WithBackSide:
                Edges = getBlocEdgesAndHeights(BldObj, roundfactor=4)
                for blocnum, bloc in enumerate(BldObj.footprint):
                    PolygonEnviro[nbfile]['FootPrint'].append(bloc)
                    PolygonEnviro[nbfile]['Bld_Height'].append(BldObj.BlocHeight[blocnum]+BldObj.BlocAlt[blocnum])
                    PolygonEnviro[nbfile]['Bld_ID'].append(BldID)
                    PolygonEnviro[nbfile]['BldNum'].append(bldNum)
                    PolygonEnviro[nbfile]['BlocNum'].append(blocnum)
            else:
                Edges = getBldEdgesAndHeights(BldObj, roundfactor=4)
                PolygonEnviro[nbfile]['AggregFootPrint'].append(BldObj.AggregFootprint)
                PolygonEnviro[nbfile]['Bld_ID'].append(BldID)
                PolygonEnviro[nbfile]['BldNum'].append(bldNum)
                PolygonEnviro[nbfile]['BlocNum'].append(0)
                PolygonEnviro[nbfile]['Bld_Height'].append(max(BldObj.BlocHeight)+min(BldObj.BlocAlt))
            Edges2Store[bldNum] = Edges
        print('\nUrban area constructed')
        PolygonEnviro[nbfile]['EdgesAndHeights'] = Edges2Store
        TotalSimDir.append(SimDir)
    return PolygonEnviro,TotalSimDir

def getBlocEdgesAndHeights(BldObj,roundfactor = 8):
    EdgesAndHeights = {'Height':[],'Edge':[],'BlocNum':[]}
    for idx,poly in enumerate(BldObj.footprint):
        localBloc = Polygon2D(poly)
        for edge in localBloc.edges:
            EdgesAndHeights['Edge'].append([(round(x,roundfactor),round(y,roundfactor)) for x,y in edge.vertices])
            EdgesAndHeights['Height'].append(BldObj.BlocHeight[idx]+ BldObj.BlocAlt[idx])
            EdgesAndHeights['BlocNum'].append(idx)
    EdgesAndHeights['BldID']= BldObj.BuildID
    return EdgesAndHeights

def getBldEdgesAndHeights(BldObj,roundfactor = 8):
    GlobalFootprint = Polygon2D(BldObj.AggregFootprint[:-1])
    EdgesHeights = {'Height': [], 'Edge': [], 'BlocNum': []}
    for edge in GlobalFootprint.edges:
        EdgesHeights['Edge'].append(
            [(round(x, roundfactor), round(y, roundfactor)) for x, y in
             edge.vertices])
        EdgesHeights['Height'].append(0)
        EdgesHeights['BlocNum'].append(0)
    for idx, poly in enumerate(BldObj.footprint):
        localBloc = Polygon2D(poly)
        for edge, edge_reversed in zip(localBloc.edges, localBloc.edges_reversed):
            Heightidx1 = [idx for idx, val in enumerate(GlobalFootprint.edges) if edge == val]
            Heightidx2 = [idx for idx, val in enumerate(GlobalFootprint.edges_reversed) if edge == val]
            if Heightidx1 or Heightidx2:
                Heigthidx = Heightidx1 if Heightidx1 else Heightidx2
                EdgesHeights['Height'][Heigthidx[0]] = BldObj.BlocHeight[idx] + BldObj.BlocAlt[idx]
    EdgesHeights['BldID'] = BldObj.BuildID
    return EdgesHeights

def MakePointOutside(Edge,poly):
    p1 = Edge[0]
    p2 = Edge[1]
    epsilon = 1e-2
    resolution = 3
    x = round((p2[0] + p1[0]) / 2,resolution) + epsilon
    y = round((p2[1] + p1[1]) / 2,resolution) + epsilon
    x1 = round((0.9*p2[0] + 0.1*p1[0]), resolution) + epsilon
    y1 = round((0.9*p2[1] + 0.1*p1[1]), resolution) + epsilon
    x2 = round((0.1*p2[0] + 0.9*p1[0]), resolution) + epsilon
    y2 = round((0.1*p2[1] + 0.9*p1[1]), resolution) + epsilon
    orientation = 1
    if Polygon(poly).contains(Point(x,y)): #helper_fcts.inside_polygon(x, y, np.array(poly), border_value=False):
        x -= 2*epsilon
        y -= 2*epsilon
        x1 -= 2 * epsilon
        y1 -= 2 * epsilon
        x2 -= 2 * epsilon
        y2 -= 2 * epsilon
        orientation = -1
    return (x,y),(x1,y1),(x2,y2),orientation

def getEdgeIdx(Matches,Edge,BldID,BldBloc):
    p1 = Edge[0]
    p2 = Edge[1]
    edgeIdx = [idx for idx,Shade in enumerate(Matches.keys()) if \
               ([p1, p2] == Matches[Shade]['AbsCoord'] and BldID == Matches[Shade]['OwnerBld_ID'] and BldBloc == Matches[Shade]['OwnerBld_Bloc'])
            or ([p2, p1] == Matches[Shade]['AbsCoord'] and BldID == Matches[Shade]['OwnerBld_ID'] and BldBloc == Matches[Shade]['OwnerBld_Bloc'])]
    if len(edgeIdx)>1:
        print('heu...error in the index caught forthe edges done or not...several locations')
    return edgeIdx[0] if edgeIdx else -999

def isBldDone(Matches,EdgeIdx,BldID):
    BldDone = BldID in Matches[EdgeIdx]['RecepientBld_ID']
    return BldDone

def isBldBlocDone(Matches,EdgeIdx,BldID,Bloc):
    BldDone = BldID in Matches[EdgeIdx]['RecepientBld_ID'] and Bloc in Matches[EdgeIdx]['RecepientBlocNum']
    return BldDone


def signed_area(pr2):
    """Return the signed area enclosed by a ring using the linear time
    algorithm at http://www.cgafaq.info/wiki/Polygon_Area. A value >= 0
    indicates a counter-clockwise oriented ring."""
    xs, ys = map(list, zip(*pr2))
    xs.append(xs[1])
    ys.append(ys[1])
    return sum(xs[i] * (ys[i + 1] - ys[i - 1]) for i in range(1, len(pr2))) / 2.0

def getLineCoef(Edge):
    p1 = Edge[0]
    p2 = Edge[1]
    try : a = (p2[1] - p1[1]) / (p2[0] - p1[0])
    except ZeroDivisionError : a = 1e9
    b = p2[1] - a * p2[0]
    return a,b

def checkEdgeOrientation(Edge,Point):
    a,b = getLineCoef(Edge)
    #make test with x
    if Point[1]-(a * Point[0] + b)>0:
        Orientation = 1
    else:
        Orientation = -1
    return a,b,Orientation

def checkVisibility(Target,a,b,Orientation):
    TargetVisibility = [node[1] - a * node[0] - b for node in Target]
    if (len([val for val in TargetVisibility if val < 0]) == len(Target) and Orientation > 0) or \
            (len([val for val in TargetVisibility if val > 0]) == len(Target) and Orientation < 0):
        return False
    else:
        return True

def feedMatches(Matches,Data,EdgeIdx,BldIdx,Raylength):
    if not isBldDone(Matches, EdgeIdx, Data['Bld_ID'][BldIdx]):
        Matches[EdgeIdx]['RecepientBld_ID'].append(Data['Bld_ID'][BldIdx])
        Matches[EdgeIdx]['RecepientBlocNum'].append(Data['BlocNum'][BldIdx])
        Matches[EdgeIdx]['RecepientBld_Height'].append(Data['Bld_Height'][BldIdx])
        Matches[EdgeIdx]['RecepientBld_Dist'].append(Raylength)
    return Matches

def isIntersection(bld,Rays):
    return [1 if Polygon(bld).intersection(Ray) else 0 for Ray in Rays]

def getAngle(a,a1):
    import math
    angle = abs((a1 - a) / (1 + a * a1))
    return math.atan(angle) * 180 / 3.14159

def checkEdgesOrientation(s1,s2,g1,g2):
    a, b = getLineCoef([s1,g1])
    a1, b1 = getLineCoef([s1, g2])
    a2, b2 = getLineCoef([s2, g1])
    a3, b3 = getLineCoef([s2, g2])
    Angles1 = getAngle(a, a1)
    Angles2 = getAngle(a2, a3)
    return Angles1,Angles2

def computMatchesForAllBuildings(Data,ThresholdDist = 200):
    NewBld, Matches = prepareElements(Data,'FootPrint')
    for bldidx,bld in enumerate(NewBld):
        print('\r', end='')
        print('---' + str(round(100*bldidx/(len(NewBld)-1),1)) + ' % has been treated', end='', flush=True)
        for bldidx1, bld1 in enumerate(NewBld):
            print('\r', end='')
            if bldidx1 % 4 == 0:
                print('-.  ' + str(round(100 * bldidx / (len(NewBld) - 1), 1)) + ' % has been treated', end='',
                      flush=True)
            else:
                print('-.. ' + str(round(100 * bldidx / (len(NewBld) - 1), 1)) + ' % has been treated', end='',
                      flush=True)
            if Data['Bld_ID'][bldidx] == Data['Bld_ID'][bldidx1]:
                continue #this means that we are looking at the same building (but two different blocs)
            Dist = Polygon(bld).centroid.distance(Polygon(bld1).centroid)
            if Polygon(bld).centroid.distance(Polygon(bld1).centroid) < ThresholdDist:
                for edge in Matches.keys():
                    if Data['Bld_ID'][bldidx1] == Matches[edge]['OwnerBld_ID']:
                        Matches = feedMatches(Matches, Data, edge, bldidx,Dist)

    return Matches,NewBld

def prepareElements(Data,FootKey):
    NewBld = []
    ShadowingHeight = []
    for bld in Data[FootKey]:
        ShadowingHeight.append(0)
        if bld[0]==bld[-1]:
            NewBld.append(bld[:-1])
        else:
            NewBld.append(bld)
    #lets compute distances now with starting points from all segments for all polygons and ending point all semgent of all polygons except the current one
    print('Computing visible surfaces...')
    offset = 0
    Matches = {}
    for i in Data['EdgesAndHeights'].keys():
        for j,edge in enumerate(Data['EdgesAndHeights'][i]['Edge']):
            Matches[i+j+offset] = {'AbsCoord': edge,
                          'OwnerBld_ID': Data['EdgesAndHeights'][i]['BldID'][Data['EdgesAndHeights'][i]['BldID']['BldIDKey']],
                          'OwnerBld_Bloc': Data['EdgesAndHeights'][i]['BlocNum'][j],
                          'RecepientBld_ID': [],
                          'RecepientBlocNum':[],
                          'RecepientBld_Height': [],
                          'RecepientBld_Dist': [],
                          'Height': Data['EdgesAndHeights'][i]['Height'][j],
                          'Rays': []}
        offset += j
    return NewBld,Matches

def computMatchesWithbackSideSurfaces(Data,WithBackSide = True,ThresholdDist = 200):
    if WithBackSide:
        NewBld,Matches = prepareElements(Data,'FootPrint')
    else:
        NewBld, Matches = prepareElements(Data, 'AggregFootPrint')
    for bldidx,bld in enumerate(NewBld[:-1]):
        print('\r', end='')
        print('---' + str(round(100*(bldidx+1)/(len(NewBld)-1),1)) + ' % has been treated', end='', flush=True)
        offsetidx = bldidx +1
        for bldidx1, bld1 in enumerate(NewBld[offsetidx:]):
            if Data['BldNum'][bldidx1 + offsetidx] in [5] and Data['BldNum'][bldidx] in [0]:
                tutu = 1
            if Data['Bld_ID'][bldidx]==Data['Bld_ID'][bldidx1+offsetidx]:
                continue #this means that we are looking at the same building (but two different blocs)
            #lets grab the coarse box around the building
            Dist = Polygon(bld).centroid.distance(Polygon(bld1).centroid)
            if Dist>ThresholdDist:
                continue
            box = Polygon(bld1).minimum_rotated_rectangle
            bld1Box = [(x,y) for x,y in box.exterior.coords][:-1]  #[(min(x),min(y)),(min(x),max(y)),(max(x),max(y)),(max(x),min(y))]
            print('\r', end='')
            if bldidx1%4==0:
                print('-.  ' + str(round(100 * bldidx / (len(NewBld) - 2), 1)) + ' % has been treated', end='', flush=True)
            else:
                print('-.. ' + str(round(100 * bldidx / (len(NewBld) - 2), 1)) + ' % has been treated', end='',
                      flush=True)
            for seg,vertex in enumerate(bld):
                StartingEdge = [vertex, bld[(seg + 1) % len(bld)]]
                StartingEdgeIdx = getEdgeIdx(Matches, StartingEdge, Data['Bld_ID'][bldidx], Data['BlocNum'][bldidx])
                #lets make the sarting point
                start_coordinates,s1,s2,StartOrientation = MakePointOutside(StartingEdge, np.array(bld))
                a, b, Orientation = checkEdgeOrientation(StartingEdge,start_coordinates)
                #check if the building or a piece of it is within the 180deg view from the edge
                if not checkVisibility(bld1Box, a, b, Orientation):
                    continue
                Rays = []
                for node in bld1Box:
                    Rays.append(LineString([s1, node]))
                    Rays.append(LineString([s2, node]))
                if sum(isIntersection(bld,Rays)) == len(Rays):
                    continue
                for seg1, vertex1 in enumerate(bld1):
                    EndingEdge = [vertex1, bld1[(seg1 + 1) % len(bld1)]]
                    #define if there is a need to go into this edge
                    if not checkVisibility(EndingEdge, a, b, Orientation):
                        continue
                    EndingEdgeIdx = getEdgeIdx(Matches, EndingEdge, Data['Bld_ID'][bldidx1 + offsetidx],Data['BlocNum'][bldidx1 + offsetidx])
                    if StartingEdge == EndingEdge or StartingEdge[::-1] == EndingEdge:
                        #in case of adjacent walls
                        Matches = feedMatches(Matches, Data, StartingEdgeIdx, bldidx1 + offsetidx, 0)
                        Matches = feedMatches(Matches, Data, EndingEdgeIdx, bldidx, 0)
                        continue
                    if isBldDone(Matches, StartingEdgeIdx, Data['Bld_ID'][bldidx1 + offsetidx]) and isBldDone(Matches, EndingEdgeIdx, Data['Bld_ID'][bldidx]):
                        continue
                    goal_coordinates,g1,g2,GoalOrientation = MakePointOutside(EndingEdge, np.array(bld1))
                    #the five Ray below are to consider either the middle point of the edge point (being 5% form the edges (see MakePointOutside())
                    Raym = LineString([start_coordinates, goal_coordinates])
                    Rays = [LineString([s1, g1]), LineString([s1, g2]), LineString([s2, g1]), LineString([s2, g2])]
                    #lets first check for intersection with it's own building bloc (if it's the case, no need to go along all the others
                    InterBld = isIntersection(bld,Rays)
                    InterBld1 = isIntersection(bld1, Rays)
                    InterBldBld1 = [a+b for a,b in zip(InterBld,InterBld1)]
                    if sum(InterBld1) == len(Rays) or sum(InterBld) == len(Rays) or 0 not in InterBldBld1:
                        continue
                    angles1, angles2 = checkEdgesOrientation(s1, s2, g1, g2)
                    if angles1 < 0.01 and angles2 < 0.01:
                        #MakeIntermediateFig(bld, bld1, NewBld[47], StartingEdge, EndingEdge)
                        continue
                    DirectVisible = True
                    OneLineHiddenBldIdx = []
                    HiddenRay = []
                    #Rays from Vertex now to avoid parallel intermediate building being missed
                    #doesn't work because we need to check as well same buildings for overlapping
                    RayVers = [LineString([StartingEdge[0], EndingEdge[0]]), LineString([StartingEdge[0], EndingEdge[1]]),
                            LineString([StartingEdge[1], EndingEdge[0]]), LineString([StartingEdge[1], EndingEdge[1]])]
                    for idxbetween,bldbeween in enumerate(NewBld):
                        Inter = isIntersection(bldbeween,Rays)
                        if sum(Inter) == len(Rays) and not WithBackSide:
                            DirectVisible = False
                            OneLineHiddenBldIdx = []
                            HiddenRay = []
                            break
                        if sum(Inter) > 0 :
                            #this means that at least one oint as a direct view
                            OneLineHiddenBldIdx.append(idxbetween)
                            HiddenRay.append(Inter)
                            DirectVisible = False
                    if DirectVisible:
                        Matches = feedMatches(Matches,Data,StartingEdgeIdx,bldidx1 + offsetidx,Raym.length)
                        Matches = feedMatches(Matches, Data, EndingEdgeIdx, bldidx, Raym.length)
                    else:
                        FullCoverBld = [OneLineHiddenBldIdx[idx] for idx, spot in enumerate(HiddenRay) if sum(spot) == len(Rays)]
                        NotFullIndex = [spot for spot in HiddenRay if sum(spot) < len(Rays)]
                        HeightFromFullCover = [0]
                        GlobalPartialHeight = [0]
                        if FullCoverBld:
                            Distance = [Polygon(NewBld[idxB]).distance(Point(start_coordinates)) for idxB in FullCoverBld]
                            HeightFromFullCover = [Data['Bld_Height'][idxB] for idxB in FullCoverBld]
                            ShadeOrder = sorted(range(len(Distance)), key=lambda k: Distance[k])
                        if NotFullIndex:
                            if 0 not in sum(np.array(NotFullIndex)): #if one ray still goes to the target directly, no need to add a height filter on this one
                                PartialDist = [Polygon(NewBld[idxB]).distance(Point(start_coordinates)) for idxB in OneLineHiddenBldIdx if idxB not in FullCoverBld]
                                HeightFromPartialCover = [Data['Bld_Height'][idxB] for idxB in OneLineHiddenBldIdx if idxB not in FullCoverBld]
                                HeigthAdnRays = np.array([[HeightFromPartialCover[id]*j for j in ray] for id,ray in enumerate(NotFullIndex)])
                                GlobalPartialHeight  = np.max(HeigthAdnRays,axis = 0)
                                ShadeOrder = sorted(range(len(PartialDist)), key=lambda k: PartialDist[k])
                            elif not WithBackSide:
                                Matches = feedMatches(Matches, Data, StartingEdgeIdx, bldidx1 + offsetidx, Raym.length)
                                Matches = feedMatches(Matches, Data, EndingEdgeIdx, bldidx, Raym.length)
                        if WithBackSide:
                            TotalShadowHeight = max(max(HeightFromFullCover),min(GlobalPartialHeight))
                            if NotFullIndex or FullCoverBld:
                                if Data['Bld_Height'][bldidx1 + offsetidx] > TotalShadowHeight:
                                    Matches = feedMatches(Matches, Data, EndingEdgeIdx, bldidx, Raym.length)
                                if Data['Bld_Height'][bldidx] > TotalShadowHeight:
                                    Matches = feedMatches(Matches, Data, StartingEdgeIdx, bldidx1 + offsetidx,Raym.length)
                            else:
                                print('[Warnings] Some weird case is being encountered with bldidx, bldidx1, seg and seg1 = ',str([bldidx, bldidx1, seg, seg1]))
    return Matches,NewBld

def cleaningTempFolders(SimDir):
    for Folder in SimDir:
        #empyting the files being inside"
        Liste = os.listdir(Folder)
        for file in Liste:
            os.remove(os.path.join(Folder,file))
        #remove the folder
        os.rmdir(Folder)

def SaveAndWrite(Matches,Data):
    print('\nAll building treated')
    j = json.dumps(Matches)
    PathName = os.path.dirname(Data['PathName'])
    FileName = os.path.basename(Data['PathName'])
    with open(os.path.join(PathName,FileName[:FileName.index('.')]+'_Walls.json'), 'w') as f:
        f.write(j)
    # import pickle
    # with open(os.path.join(PathName,FileName[:FileName.index('.')]+'_Walls.pickles'), 'wb') as handle:
    #     pickle.dump(Matches, handle, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__' :
    MainPath = os.getcwd()

    GlobKey, config, ShadeLim = setConfig.getConfig(App = 'Shadowing')

    WithBackSide = True
    ComputAllSurf = False #default is compute with backside surfaces
    if ShadeLim == 'AllSurf':
        ComputAllSurf = True
    elif ShadeLim == 'SimpleSurf':
        WithBackSide = False
    #this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    print('Urban Area is first build by aggregating all building in each geojson files')
    PolygonEnviro,Folders2Clean = CreatePolygonEnviro(GlobKey,config,WithBackSide = WithBackSide)
    print('Lets compute, for each building the shadowing surfaces from others')
    for Enviro in PolygonEnviro:
        if ComputAllSurf:
            Matches, NewBld = computMatchesForAllBuildings(PolygonEnviro[Enviro])
        else:
            Matches, NewBld = computMatchesWithbackSideSurfaces(PolygonEnviro[Enviro],WithBackSide=WithBackSide)
        SaveAndWrite(Matches, PolygonEnviro[Enviro])
    os.chdir(MainPath)
    cleaningTempFolders(Folders2Clean)
    print('Wall file created in the same folder of the Building file. see ***.json file')