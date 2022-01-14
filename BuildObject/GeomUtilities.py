# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import itertools
from shapely.geometry.polygon import Polygon, Point, LineString
from geomeppy.geom.polygons import Polygon3D
from geomeppy.utilities import almostequal

def is_clockwise(points):
    # points is your list (or array) of 2d points.
    assert len(points) > 0
    s = 0.0
    for p1, p2 in zip(points, points[1:] + [points[0]]):
        s += (p2[0] - p1[0]) * (p2[1] + p1[1])
    return s > 0.0

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
    if Polygon3D(new_poly).area > Polygon3D(new_poly_try).area:
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

def CheckMultiBlocFootprint(blocs,tol =1):
    validMultibloc = True
    if len(blocs)>1:
        validMultibloc = False
        for bloc1,bloc2 in itertools.product(blocs,repeat = 2):
            if bloc1 != bloc2:
                for ptidx,pt in enumerate(bloc1):
                    edge = [bloc1[ptidx],bloc1[(ptidx+1)%len(bloc1)]]
                    comEdges = []
                    for ptidx1,pt1 in enumerate(bloc2):
                        edge1 = [bloc2[ptidx1], bloc2[(ptidx1+1)%len(bloc2)]]
                        if is_parallel(edge,edge1,10) and confirmMatch(edge, edge1, tol):
                            validMultibloc = True
                            pt1 = False
                            pt2 = False
                            if LineString(edge1).distance(Point(edge[0])) < tol:
                                edge[0] = point_on_line(edge1[0], edge1[1],edge[0])
                                edge[0],conf= CoordAdjustement(edge1, edge[0], tol)
                                pt1 = True
                            if LineString(edge1).distance(Point(edge[1])) < tol:
                                edge[1] = point_on_line(edge1[0], edge1[1],edge[1])
                                edge[1],conf = CoordAdjustement(edge1, edge[1], tol)
                                pt2 = True
                            if pt1 and pt2:
                                if abs(getAngle(edge1, edge) -180) < 5:
                                    comEdges.append([edge[1],edge[0]])
                                else:
                                    comEdges.append(edge)
                    bloc1[ptidx] = edge[0]
                    bloc1[(ptidx + 1) % len(bloc1)] = edge[1]
                    #lets check if these nodes are also on bloc2
                    #first which bloc is concerned
                    for comEdge in comEdges:
                        if comEdge[0] in bloc2 and comEdge[1] not in bloc2:
                            index = bloc2.index(comEdge[0])+1
                            bloc2.insert(index,comEdge[1])
                            #bloc2 = bloc2[:index]+[comEdge[1]]+bloc2[index:]
                        if comEdge[1] in bloc2 and comEdge[0] not in bloc2:
                            index = bloc2.index(comEdge[1])
                            bloc2.insert(index,comEdge[0])
                            #bloc2 = bloc2[:index]+[comEdge[0]]+bloc2[index:]
    return blocs,validMultibloc

def point_on_line(a, b, p):
    import numpy as np
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
    import numpy as np
    v = np.array([vector_a_x, vector_a_y])
    w = np.array([vector_b_x, vector_b_y])
    return abs(np.rad2deg(np.arccos(round(v.dot(w) / (np.linalg.norm(v) * np.linalg.norm(w)), 4))))

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