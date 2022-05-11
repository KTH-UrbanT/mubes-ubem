# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import itertools
from shapely.geometry.polygon import Polygon, Point, LineString
from geomeppy.geom.polygons import Polygon3D, Polygon2D
from geomeppy.utilities import almostequal
from geomeppy.geom import core_perim
import numpy as np
import copy
import CoreFiles.GeneralFunctions as GrlFct

def is_clockwise(points):
    # points is your list (or array) of 2d points.
    assert len(points) > 0
    s = 0.0
    for p1, p2 in zip(points, points[1:] + [points[0]]):
        s += (p2[0] - p1[0]) * (p2[1] + p1[1])
    return s > 0.0

def RotatePolyOrder(poly):
    #poly is a list of tuple or list of two coordinates
    return poly[1:]+[poly[0]]

def chekIdenticalpoly(poly1,poly2,tolerance):

    #polygon are considered identical if there veretx are closer then tolrenece in each coordintate
    poly1 = [(round(v[0],tolerance),round(v[1],tolerance)) for v in poly1]
    poly2 = [(round(v[0],tolerance),round(v[1],tolerance)) for v in poly2]
    Identical = False
    if poly1[-1]==poly1[0]:
        poly1 = poly1[:-1]
    if poly2[-1] == poly2[0]:
        poly2 = poly2[:-1]
    tries = 0
    finished = False
    if is_clockwise(poly1) != is_clockwise(poly2):
        poly2.reverse()
    while not finished:
        if poly1 == poly2:
            Identical = True
            finished = True
        elif tries == len(poly2):
            finished = True
        else:
            tries += 1
            poly2 = RotatePolyOrder(poly2)
    if Identical == False:
        Identical = ExtraCheck(poly1,poly2)
    return Identical

def ExtraCheck(poly1,poly2):
    Identical = False
    poly1Shap = Polygon(poly1)
    poly2Shap = Polygon(poly2)
    if poly1Shap.contains(poly2Shap) or poly2Shap.contains(poly1Shap):
        if abs(poly1Shap.area-poly2Shap.area)<1: #it means that either one of the other is contaned inside with less than 1m2 of difference
            Identical = True
    return Identical

def getArea(poly):
    area = 0
    for i in range(len(poly)):
        area = Polygon(poly).area
        if area>0: break
        else: poly = poly[1:]+[poly[0]]
    return area


def mergeHole(poly,hole):
    #the two polygons needs to be in opposite direction to be merge into one with the hole
    if is_clockwise(poly) == is_clockwise(poly):
        hole.reverse()
    #lets computs the closes distance between each
    links = list(itertools.product(poly, hole))
    links = sorted(
        links, key=lambda x: getDistance(x[0],x[1])
    )
    #the two first vertexes are considered as starting points and ending point for the first polygon
    first_on_poly = [links[0][0]]
    last_on_hole = [links[0][1]]
    for i,link in enumerate(links):
        if link != links[0]:
            first_on_poly.append(links[i][0])
            last_on_hole.append(links[i][1])
            break
    # #now lets go along the poly and get the mid point of poly list to break the polygons
    # for i, link in enumerate(links):
    #     if link[0] == poly[(poly.index(first_on_poly[0]) + round(len(poly) / 2)) % len(poly)]:
    #         break
    # #both are catched, the two polygons can be created
    # first_on_poly.append(links[i][0])
    # last_on_hole.append(links[i][1])

    section_on_poly = getSection(poly,first_on_poly)
    section_on_hole = getSection(hole, last_on_hole)
    hole.reverse()
    section_on_holerev = getSection(hole, last_on_hole)
    final_poly1 = section_on_poly + section_on_hole
    final_poly1rev = section_on_poly + section_on_holerev
    first_on_poly.reverse()
    last_on_hole.reverse()
    section_on_poly = getSection(poly, first_on_poly)
    section_on_hole = getSection(hole, last_on_hole)
    if is_clockwise(section_on_poly) == is_clockwise(section_on_hole):
        section_on_hole.reverse()
    final_poly2 = section_on_poly + section_on_hole
    return [final_poly1,final_poly2]

def CleanPoly(poly,DistTol,roundVal):
    polycoor = []
    for j in poly:
        new = (j[0], j[1])
        new_coor = new  # []
        # for ii in range(len(RefCoord)):
        #     new_coor.append((new[ii] - RefCoord[ii]))
        polycoor.append(tuple(new_coor))
    if polycoor[0] == polycoor[-1]:
        polycoor = polycoor[:-1]
    # even before skewed angle, we need to check for tiny edge below the tolerance DisTol
    pt2remove = []
    #lets removes aligned edges only checkec from angle
    polycoor = removeAlignedEdges(polycoor)
    if len(polycoor)<3: return polycoor, []
    #lets removes the edges below a distance threshold
    polycoor = removeEdge(polycoor, DistTol)
    if len(polycoor)<3: return polycoor, []
    #letscheck for balcony effect (triangle form removing formerly small edges)
    polycoor = AvoidBalconyEffect(polycoor, DistTol)
    if len(polycoor)<3: return polycoor, []
    # lets removes aligned edges only checked from angle
    polycoor = removeAlignedEdges(polycoor)
    if len(polycoor)<3: return polycoor, []
    # for edge in Polygon2D(polycoor).edges:
    #     if edge.length < DistTol:
    #         pt2remove.append(edge.p2)
    # for pt in pt2remove:
    #     if len(polycoor) > 3:
    #         polycoor.remove(pt)
    newpolycoor, node = core_perim.CheckFootprintNodes(polycoor, 5) #the returned poly is not used finally investigation are to be done !
    polycoor = [(round(point[0],roundVal),round(point[1],roundVal)) for point in polycoor]
    return polycoor, node #the cleaner newpolycoord cannot be used here as it can be attachedto someother blocs, so the nodes are kept only

def AvoidBalconyEffect(poly,DistTol):
    finished = False
    while not finished:
        node2remove = []
        for nodei,nodej in itertools.combinations(enumerate(poly), 2):
            if getDistance(nodei[1],nodej[1])<DistTol and (nodej[0]-nodei[0])<3:
                node2remove.append(nodei[0])
                node2remove.append(nodej[0])
                break
        if node2remove:
            poly = [node for idx,node in enumerate(poly) if idx not in node2remove]
        else:
            finished = True
    return poly

def removeAlignedEdges(poly):
    finished = False
    while not finished:
        pt2remove = False
        for idx, pt in enumerate(poly):
            pt1 = poly[-1 if idx == 0 else idx - 1]
            pt2 = poly[(idx + 1) % len(poly)]
            if pt == pt1 or pt == pt2: #this if duplicate node is found
                pt2remove = True
                break
            line1 = (pt, pt1)
            line2 = (pt, pt2)
            angle = getAngle(line1,line2)
            if angle < 5 or abs(angle-180)<5:
                pt2remove = True
                break
        if pt2remove and len(poly) > 4:
            poly.pop(idx)
        else:
            finished = True
    return poly

def removeEdge(poly,DistTol):
    finished = False
    while not finished:
        pt2remove = False
        for idx,pt in enumerate(poly):
            pt2 = poly[(idx+1)%len(poly)]
            if getDistance(pt,pt2) < DistTol:
                midPoint = ((pt[0]+pt2[0])/2,(pt[1]+pt2[1])/2)
                line1 = (midPoint, poly[-1 if idx == 0 else idx - 1])
                line2 = (midPoint, poly[(idx + 2) % len(poly)])
                if getAngle(line1, line2)>80:
                    pt2remove = True
                    break
        if pt2remove and len(poly)>4:
            poly.pop(idx)
            poly.insert(idx,midPoint)
            poly.pop((idx+1)%len(poly))
        else:
            finished = True
    return poly

def mergeGeomeppy(poly,hole):
    poly = Polygon3D(poly)
    hole = Polygon3D(hole)
    links = list(itertools.product(poly, hole))
    links = sorted(
        links, key=lambda x: x[0].relative_distance(x[1])
    )  # fast distance check

    # first_on_poly = links[0][0]
    # if links[1][0] == first_on_poly:
    #     last_on_poly = links[2][0]
    # else:
    #     last_on_poly = links[1][0]
    #
    # first_on_hole = links[1][1]
    # if links[0][1]== first_on_hole:
    #     last_on_hole = links[-1][1]
    # else:
    #     last_on_hole = links[0][1]

    first_on_poly = links[0][0]
    last_on_hole = links[0][1]
    for i, link in enumerate(links):
        if link[0] != first_on_poly and link[1] != last_on_hole:
            last_on_poly = link[0]
            first_on_hole = link[1]
            break


    new_poly = section(first_on_poly, last_on_poly, poly[:] + poly[:]) + section(
        first_on_hole, last_on_hole, reversed(hole[:] + hole[:])
    )
    #for a simple case it, didn't work because of the position of the first points, the last was the one after the first withtout taking any other nodes
    #the hole was filled... the workaround is to compute both and take the smalest area
    new_poly_try = section(first_on_poly, last_on_poly, poly[:] + poly[:]) + section(
        first_on_hole, last_on_hole, (hole[:] + hole[:])
    )
    if getArea(new_poly) > getArea(new_poly_try) and getArea(new_poly_try) > 0:
        new_poly = new_poly_try

    new_poly = Polygon3D(new_poly)
    union = hole.union(new_poly)[0]
    try: new_poly2 = poly.difference(union)[0]
    except:
        return [new_poly]
    if not almostequal(new_poly.normal_vector, poly.normal_vector):
        new_poly = new_poly.invert_orientation()
    if not almostequal(new_poly2.normal_vector, poly.normal_vector):
        new_poly2 = new_poly2.invert_orientation()

    return [new_poly, new_poly2]

def MakeMerge(coord,poly2merge,DebugMode,LogFile,BlocHeight,BlocAlt,BlocMaxAlt):
    try:
        for i, idx in enumerate(poly2merge):
            # lets check if it's a tower of smaller footprint than the base:
            SmallerTower = False
            if BlocHeight[idx[1]] - BlocHeight[idx[0]] > 0:
                # if BlocAlt[idx[1]] - BlocAlt[idx[0]] > 0:
                #     UpperBloc = True
                #     continue
                # else:
                    SmallerTower = True
                # continue
            newtry = False
            if newtry:
                newSurface = mergeHole(coord[idx[0]], coord[idx[1]])
                coord[idx[0]] = newSurface[0]
                coord[idx[1]] = newSurface[1]
            else:
                new_surfaces = mergeGeomeppy(coord[idx[0]], coord[idx[1]])
                # new_surfaces = break_polygons(Polygon3D(coord[idx[0]]), Polygon3D(coord[idx[1]]))
                xs, ys, zs = zip(*list(new_surfaces[0]))
                coord[idx[0]] = [(xs[nbv], ys[nbv]) for nbv in range(len(xs))]
                if len(new_surfaces) > 1:
                    xs, ys, zs = zip(*list(new_surfaces[1]))
                    if SmallerTower:
                        coord.append([(xs[nbv], ys[nbv]) for nbv in range(len(xs))])
                        BlocHeight.append(BlocHeight[idx[0]])
                        BlocAlt.append(BlocAlt[idx[0]])
                        BlocMaxAlt.append(BlocMaxAlt[idx[0]])
                    else:
                        coord[idx[1]] = [(xs[nbv], ys[nbv]) for nbv in range(len(xs))]
                        BlocHeight[idx[1]] = BlocHeight[idx[0]]
                else:
                    coord.pop(idx[1])
                    BlocHeight.pop(idx[1])
                    BlocAlt.pop(idx[1])
                    BlocMaxAlt.pop(idx[1])
            msg = '[Geom Cor] There is a hole that will split the main surface in two blocs \n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    except:
        msg = '[Poly Error] Some error are present in the polygon parts. Some are identified as being inside others...\n'
        print(msg[:-1])
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        import matplotlib.pyplot as plt

        fig = plt.figure(0)
        for i in coord:
            xs, ys = zip(*i)
            plt.plot(xs, ys, '-.')
        return
        # plt.show()
        # titre = 'FormularId : '+str(DB.properties['FormularId'])+'\n 50A_UUID : '+str(DB.properties['50A_UUID'])
        # plt.title(titre)
        # plt.savefig(self.name+ '.png')
        # plt.close(fig)
    return coord

def check4UpperTower(BlocHeight,BlocAlt,idx):
    return BlocHeight[idx[1]] - BlocHeight[idx[0]] > 0 and BlocAlt[idx[1]] - BlocAlt[idx[0]] > 0


def checkForMerge(coord,DebugMode,LogFile,BlocHeight,BlocAlt,UpperBloc):
    poly2merge =  []
    area2merge = []
    for idx, coor in enumerate(coord):
        for i in range(len(coord) - idx - 1):
            if Polygon(coor).contains(Polygon(coord[idx + i + 1])) and not check4UpperTower(BlocHeight,BlocAlt,[idx, idx + i + 1]):
                poly2merge.append([idx, idx + i + 1])
                area2merge.append([Polygon(coor).area, Polygon(coord[idx + i + 1]).area])
            if Polygon(coord[idx + i + 1]).contains(Polygon(coor)) and not check4UpperTower(BlocHeight,BlocAlt,[idx + i + 1, idx]):
                poly2merge.append([idx + i + 1, idx])
                area2merge.append([Polygon(coord[idx + i + 1]).area, Polygon(coor).area])
            if check4UpperTower(BlocHeight, BlocAlt, [idx, idx + i + 1]) or check4UpperTower(BlocHeight,BlocAlt,[idx + i + 1, idx]):
                UpperBloc = True
    for i, c in enumerate(poly2merge):
        for j, c1 in enumerate(poly2merge):
            if c[0] == c1[1]:
                msg = '[Geom Error] The building has three polygons inside one another...please check your input file \n'
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                return
            if (c[0] == c1[0] or c[1] == c1[1]) and i != j:
                msg = '[Geom Warning] Some polygons are asked to be merged with 2 or more others...this can lead to Poly Error because merging with the first one might be not compatible with further mergings...please check initial file \n'
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    return poly2merge,area2merge,UpperBloc

def section(first, last, coords):
    section_on_hole = []
    for item in coords:
        if item == first:
            section_on_hole.append(item)
        elif section_on_hole:
            section_on_hole.append(item)
            if item == last:
                break
    return section_on_hole

def getDistance(pt1,pt2):
    return ((((pt2[0] - pt1[0]) ** 2) + ((pt2[1] - pt1[1]) ** 2)) ** 0.5)

def getSection(poly,mainNode):
    section = []
    for idx in range(2*len(poly)):
        if poly[idx%len(poly)] == mainNode[0] and not section:
            section.append(poly[idx])
        elif section:
            section.append(poly[idx%len(poly)])
            if poly[idx%len(poly)] == mainNode[1]:
                break
    return section

def CheckMultiBlocFootprint(blocs,blocAlt,tol =1):
    validMultibloc = True
    if len(blocs)>1:
        validMultibloc = False
        for idxbloc1,idxbloc2 in itertools.product(enumerate(blocs),repeat = 2):
            done = False
            if idxbloc1[1] != idxbloc2[1] and blocAlt[idxbloc1[0]]==blocAlt[idxbloc2[0]]:
                bloc1 = idxbloc1[1]
                bloc2 = idxbloc2[1]
                for ptidx,pt in enumerate(bloc1):
                    edge = [bloc1[ptidx],bloc1[(ptidx+1)%len(bloc1)]]
                    comEdges = []
                    for ptidx1,pt1 in enumerate(bloc2):
                        if ptidx1 == 1 and ptidx ==13 and idxbloc1[0]==2 and idxbloc2[0]==4:
                            tutu =1
                        edge1 = [bloc2[ptidx1], bloc2[(ptidx1+1)%len(bloc2)]]
                        if is_parallel(edge,edge1,10) and confirmMatch(edge, edge1, tol):
                            validMultibloc = True
                            pt1 = False
                            pt2 = False
                            if LineString(edge).distance(Point(edge1[0])) < tol:
                                edge1[0] = point_on_line(edge[0], edge[1],edge1[0])
                                edge1[0],conf= CoordAdjustement(edge, edge1[0], tol)
                                pt1 = True
                            if LineString(edge).distance(Point(edge1[1])) < tol:
                                edge1[1] = point_on_line(edge[0], edge[1],edge1[1])
                                edge1[1],conf = CoordAdjustement(edge, edge1[1], tol)
                                pt2 = True
                            if pt1 and pt2:
                                if abs(getAngle(edge, edge1) -180) < 5:
                                    comEdges.append([edge1[1],edge1[0]])
                                else:
                                    comEdges.append(edge1)
                            #lets make a try to see if the correction doesn't lead to a false polygon
                            if pt1 or pt2:
                                PolyTest = copy.deepcopy(bloc2)
                                PolyTest[ptidx1] = edge1[0]
                                PolyTest[(ptidx1 + 1) % len(bloc2)] = edge1[1]
                                if Polygon(PolyTest).is_valid:
                                    if PolyTest == bloc2 : done = True
                                    else:
                                        bloc2[ptidx1] = edge1[0]
                                        bloc2[(ptidx1 + 1) % len(bloc2)] = edge1[1]
                    #lets check if these nodes are also on bloc2
                    #first which bloc is concerned
                    for comEdge in comEdges:
                        if comEdge[0] in bloc1 and comEdge[1] not in bloc1:
                            index = bloc1.index(comEdge[0])+1
                            bloc1.insert(index,comEdge[1])
                            #bloc2 = bloc2[:index]+[comEdge[1]]+bloc2[index:]
                        if comEdge[1] in bloc1 and comEdge[0] not in bloc1:
                            index = bloc1.index(comEdge[1])
                            bloc1.insert(index,comEdge[0])
                            #bloc2 = bloc2[:index]+[comEdge[0]]+bloc2[index:]
    return blocs,validMultibloc

def point_on_line(a, b, p):
    a = np.array(a)
    b = np.array(b)
    p = np.array(p)
    ap = p - a
    ab = b - a
    result = a + np.dot(ap, ab) / np.dot(ab, ab) * ab
    return tuple(result)

def getAngle(line1,line2):
    vector_a_x = line1[1][0] - line1[0][0]
    vector_a_y = line1[1][1] - line1[0][1]
    vector_b_x = line2[1][0] - line2[0][0]
    vector_b_y = line2[1][1] - line2[0][1]
    v = np.array([vector_a_x, vector_a_y])
    w = np.array([vector_b_x, vector_b_y])
    # ang1 = np.arctan2(*v[::-1])
    # ang2 = np.arctan2(*w[::-1])
    # import matplotlib.pyplot as plt
    # plt.figure()
    # Makeplot(line1)
    # Makeplot(line2)
    # a = plt.gca()
    # a.set_aspect('equal', adjustable='box')
    # print(np.rad2deg((ang1 - ang2) % (2 * np.pi))%180, abs(np.rad2deg(np.arccos(round(v.dot(w) / (np.linalg.norm(v) * np.linalg.norm(w)), 4)))))
    # import warnings
    # warnings.simplefilter('error')
    try:
        angle= abs(np.rad2deg(np.arccos(round(v.dot(w) / (np.linalg.norm(v) * np.linalg.norm(w)), 4))))
    except:
        angle = 0
    return angle

# def getNewAngle(line1,line2):
#     if getDistance(line1[0],line2[1]) > max(getDistance(line1[0],line1[1]),getDistance(line2[0],line2[1])):
def Makeplot(poly):
    import matplotlib.pyplot as plt

    x, y = zip(*poly)
    plt.plot(x, y, '.-')


def is_parallel(line1, line2, tol = 5):
    angledeg = getAngle(line1, line2)
    if angledeg <tol or abs(angledeg-180) < tol:
        return True
    else:
        return False

def CoordAdjustement(edge,pt,tol):
    #if one point is closest than 1 m of on edge point, the point is moved to the edge's point
    coormade = False
    if Point(pt).distance(Point(edge[0])) < tol:
        coormade = True
        pt = edge[0]
    elif Point(pt).distance(Point(edge[1])) < tol:
        coormade = True
        pt = edge[1]
    return pt,coormade

def checkAltTolerance(BlocAlt,AltTolerance):
    msg = []
    for i, val in enumerate(BlocAlt):
        sameAltIdx = [i]
        for j, val1 in enumerate(BlocAlt[i + 1:]):
            if abs(val - val1) < AltTolerance:
                sameAltIdx.append(j + i + 1)
                msg = ('[Geom Info] Some polygon''s altitude were adjusted because of differences lower then '+str(AltTolerance)+' m were found with others. \n')
        AverageAlt = sum([BlocAlt[k] for k in sameAltIdx]) / len(sameAltIdx)
        BlocAlt = [AverageAlt if idx in sameAltIdx else alt for idx, alt in enumerate(BlocAlt)]
        if len(sameAltIdx)==len(BlocAlt): break
    return BlocAlt,msg

def confirmMatch(Edge, Edge1,tol):
    #this should be enough if both edges are already checked being //
    dist1 = min(LineString(Edge).distance(Point(Edge1[0])),LineString(Edge).distance(Point(Edge1[1])))
    dist2 = min(LineString(Edge1).distance(Point(Edge[0])), LineString(Edge1).distance(Point(Edge[1])))
    if dist1 <tol or dist2 < tol:
        #we want to avoid cases with exactly the same vertexes (shading going from the building edge to the outside)
        checkNode = [CoordAdjustement(Edge,Edge1[0],1),CoordAdjustement(Edge,Edge1[1],1) or CoordAdjustement(Edge1,Edge[0],1) or CoordAdjustement(Edge1,Edge[1],1)]
        if True not in [val[1] for val in checkNode]:
            return True
    #both shade vertex are on the edge
    dist1 = LineString(Edge).distance(Point(Edge1[0]))
    dist2 = LineString(Edge).distance(Point(Edge1[1]))
    if dist1 <tol and dist2 < tol:
        return True
    # both shade vertex are on the edge
    dist1 = LineString(Edge1).distance(Point(Edge[0]))
    dist2 = LineString(Edge1).distance(Point(Edge[1]))
    if dist1 < tol and dist2 < tol:
        return True
    return False


def checkShadeWithFootprint(AggregFootprint, ShadeWall,ShadeId,tol = 2):
    if ShadeId == 'V69467-8':
        a=1
    # check if some shadingssurfaces are too close to the building
    # we consider the middle coordinate point fo the shading surface
    # if less than 1m than lets consider that the boundary conditions should be adiabatique instead of outdoor conditions (adjacent buildings)
    ShadeMidCoord = ((ShadeWall[0][0] + ShadeWall[1][0]) / 2,
                     (ShadeWall[0][1] + ShadeWall[1][1]) / 2)
    #the footprint is closed in order to enable a full loop around all edges (including the last one between first and last veretx
    #closedFootprint.append(AggregFootprint[0])
    confirmed = False
    OverlapCode = 0
    # this code is 0 for fulloverlap from edge to edge,
    # 2 for partial overlap with one commun edge and longer shading element,
    # 4 for partial overlap with no commun edge,
    # it is further increased by one if the height is below the building
    if min([Point(ShadeWall[0]).distance(Polygon(AggregFootprint)), Point(ShadeWall[1]).distance(Polygon(AggregFootprint))])< tol:
        for idx, node in enumerate(AggregFootprint[:-1]):
            #dist1 = LineString([AggregFootprint[idx], AggregFootprint[idx + 1]]).distance(LineString(ShadeWall))
            if is_parallel([AggregFootprint[idx], AggregFootprint[idx + 1]], ShadeWall):#if dist1 < 0.1:
                #first the segment direction shall be compute for the closest point if not equal
                Edge = [AggregFootprint[idx], AggregFootprint[idx + 1]]
                if confirmMatch(Edge, ShadeWall,tol): #the tolerance is between points and edge (either from the footprint or the
                    OverlapCode = 4
                    confirmed = True
                    ShadeWall[0] = point_on_line(Edge[0], Edge[1],ShadeWall[0])
                    ShadeWall[0],CoorPt1 = CoordAdjustement(Edge, ShadeWall[0],tol)   #the tol is about distance bewteen 2 vertexes
                    if CoorPt1:
                        OverlapCode = 2
                    ShadeWall[1] = point_on_line(Edge[0], Edge[1],ShadeWall[1])
                    ShadeWall[1], CoorPt2 = CoordAdjustement(Edge,ShadeWall[1],tol)   #the tol is about distance bewteen 2 vertexes
                    if CoorPt2:
                        OverlapCode = 2
                    if CoorPt1 and CoorPt2: #it means that the sade's edge is exactly on a footprint's edge, no need to go further
                        OverlapCode = 0
                        return confirmed,ShadeWall,OverlapCode
        #if the middle point isinside the polygon (with a buffer zone of 1m, lets dropp it
        reduceInsideArea = Polygon(AggregFootprint).buffer(distance = -1, join_style=2)
        if reduceInsideArea.contains(Point(ShadeMidCoord)):
            return False, ShadeWall, 999
    return confirmed,ShadeWall,OverlapCode