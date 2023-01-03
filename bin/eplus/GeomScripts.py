# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import sys
from shapely.geometry import Polygon
from shapely.ops import unary_union as cascaded_union #this is to consider the deprecation of the latter upon the former since shapely 1.8
import eplus.Envelope_Param as Envelope_Param
import core.GeneralFunctions as GrlFct
import itertools
from geomeppy import geom

def BuildBloc(idf,perim,bloc,bloc_coord,Height,nbstories,nbBasementstories,BasementstoriesHeight,Perim_depth,altitude):
    if perim:
        idf.add_block(
            name='Build' + str(bloc) + '_Alt'+str(altitude),
            coordinates=bloc_coord,
            height=Height,
            num_stories=nbstories + nbBasementstories,
            altitude=altitude,
            # building.nbfloor+building.nbBasefloor, #it defines the numbers of zones !
            below_ground_stories=nbBasementstories,
            below_ground_storey_height=BasementstoriesHeight if nbBasementstories > 0 else 0,
            zoning='core/perim',
            perim_depth=Perim_depth,
        )
    else:
        idf.add_block(
            name='Build' + str(bloc) + '_Alt'+str(altitude),
            coordinates=bloc_coord,
            height=Height,
            altitude = altitude,
            num_stories=nbstories + nbBasementstories,
            # building.nbfloor+building.nbBasefloor, #it defines the numbers of zones !
            below_ground_stories=nbBasementstories,
            below_ground_storey_height=BasementstoriesHeight if nbBasementstories > 0 else 0
        )

def createBuilding(LogFile,idf,building,perim,FloorZoning,ForPlots =False,DebugMode = False):
    #here, the building geometry is created and extruded for each bloc composing the builing, it uses the function above as well
    Full_coord = building.footprint
    Nb_blocs = len(Full_coord)
    for bloc in range(Nb_blocs):
        bloc_coord =  Full_coord[bloc]
        Height = building.BlocHeight[bloc]
        nbstories = building.BlocNbFloor[bloc] if FloorZoning else 1
        nbBasementstories = building.nbBasefloor if FloorZoning else min(building.nbBasefloor,1)
        BasementstoriesHeight = 2.5 if FloorZoning else 2.5*building.nbBasefloor
        Perim_depth = 3 #the perimeter depth is fixed to 3m and is reduced if some issue are encountered.
        matched = False
        try: altitude = building.BlocAlt[bloc] if ForPlots==1 else building.BlocAlt[bloc]-min(building.BlocAlt) #this try/except is because the altitude definition has been introduced later oin the platform developpement. thus to re-runs some cases, exception had to be introduced
        except: altitude = 0
        while not matched:
            try:
                BuildBloc(idf, perim, bloc, bloc_coord, Height, nbstories, nbBasementstories, BasementstoriesHeight, Perim_depth,altitude)
                matched = True
            except:
                Perim_depth = Perim_depth/2
                msg = '[Core Perimeter] the given perimeter depth had to be reduced by 2...\n'
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            if Perim_depth<0.5:
                msg = '[Core Perimeter] This building cannot have Perim/Core option..it failed with perimeter depth below 0.5m\n'
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                return

    # the shading walls around the building are created with the function below
    # these are used in the function that defines the boundary conditions
    #before going through the matching surface identification, we need to make shading surfaces being adjacents...
    createAdjacentWalls(building, idf)
    #this function enable to create all the boundary conditions for all surfaces
    try:
        # import time
        # start = time.time()
        MatchedShade = idf.intersect_match()
        # end = time.time()
        # print('[Time Report] : The intersect_match function took : ', round(end - start, 2), ' sec')
        if MatchedShade:
            msg = '[Nb Adjacent_Surfaces] This building has ' + str(len(MatchedShade)) + ' adiabatic surfaces\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    except:
        msg ='[Error - Boundary] function intersect_match() failed in CoreFiles\GeomScripts.py....\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        #this is to generate an error as it's handles else where
        int('process failed')

    # this last function on the Geometry is here to split the non convex surfaces
    # if not, some warnings are raised because of shading computation.
    # it should thus be only the roof surfaces. Non convex internal zone are not concerned as Solar distribution is 'FullExterior'
    try:
        if not ForPlots:
            split2convex(idf,DebugMode,LogFile)
    except:
        msg ='[Error - Convex] The Split2convex function failed for this building....\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        pass

def createRapidGeomElem(idf,building):
    #envelop can be created now and allocated to the correct surfaces
    createEnvelope(idf, building)
    createShadings(building, idf)
    #create parition walls
    #from EP9.2 there is a dedicated construction type (to be tried as well), but 'Fullexeterior' option is still required
    #see https://unmethours.com/question/42542/interior-air-walls-for-splitting-nonconvex-zones/
    # see https://unmethours.com/question/13094/change-all-interior-walls-to-air-walls/
    #see https://unmethours.com/question/41171/constructionairboundary-solar-enclosures-for-grouped-zones-solar-distribution/
    createAirwallsCstr(idf)
    return idf

def createAdjacentWalls(building,idf):
    try: BlocAlt = building.BlocAlt
    except: BlocAlt = [0]
    for ii,sh in enumerate(building.shades):
        if building.shades[sh]['distance'] == 0 and (building.shades[sh]['height']-min(BlocAlt))>0:
            idf.add_shading_block(
                name='Shading_'+sh,
                coordinates=building.shades[sh]['Vertex'], #[GeomElement['VertexKey']],
                height=building.shades[sh]['height']-min(BlocAlt),
                )
            #Because adding a shading bloc creates two identical surfaces, lets remove one to avoid too big input files
            newshade = idf.idfobjects["SHADING:SITE:DETAILED"]
            for i in newshade:
                if i.Name in ('Shading_'+sh+'_2'):
                    idf.removeidfobject(i)
    return idf

def createShadings(building,idf):
    try: BlocAlt = building.BlocAlt
    except: BlocAlt = [0]
    for ii,sh in enumerate(building.shades):
        if building.shades[sh]['distance'] <= building.MaxShadingDist and building.shades[sh]['distance'] > 0 and  (building.shades[sh]['height']-min(BlocAlt))>0:
            idf.add_shading_block(
                name='Shading_'+sh,
                coordinates=building.shades[sh]['Vertex'], #[GeomElement['VertexKey']],
                height=building.shades[sh]['height']-min(BlocAlt),
                )
            #Because adding a shading bloc creates two identical surfaces, lets remove one to avoid too big input files
            newshade = idf.idfobjects["SHADING:SITE:DETAILED"]
            for i in newshade:
                if i.Name in ('Shading_'+sh+'_2'):
                    idf.removeidfobject(i)
    return idf

def createEnvelope(idf,building):
    #settings for the materials and constructions
    idf.set_default_constructions()
    #creating the materials, see Envelope_Param for material specifications
    Envelope_Param.create_Material(idf, building.Materials)
    # lets change the construction for some specific zones surfaces: the partition between none heated zones like
    # basement and the above floors
    # creating the construction, see Envelope_Param for material specifications for seperation with heated and non heated zones
    Envelope_Param.createNewConstruction(idf, 'Project Heated1rstFloor', 'Heated1rstFloor')
    Envelope_Param.createNewConstruction(idf, 'Project Heated1rstFloor Rev', 'Heated1rstFloor')
    # special loop to assign the construction that separates the basement to the other storeis.
    for idx, zone in enumerate(idf.idfobjects["ZONE"]):
        storey = int(zone.Name[zone.Name.find('Storey') + 6:])  # the name ends with 'Storey' so lets get the storey number this way
        try: alt = float(zone.Name[zone.Name.find('_Alt') + 4:zone.Name.find('Storey')])
        except: alt = 0
        sur2lookat = (s for s in zone.zonesurfaces if s.key not in ['INTERNALMASS'])
        for s in sur2lookat:
            if s.Surface_Type in 'ceiling' and storey == -1:  # which means that we are on the basements just below ground
                s.Construction_Name = 'Project Heated1rstFloor Rev'  #this will enable to reverse the construction for the ceiling compared to the floor of the adjacent zone
            if s.Surface_Type in 'floor' and storey == 0 and int(alt)==0:  # which means that we are on the first floors just above basement this states that whether or not there is basement zone, the floor slab is defined by this layer
                s.Construction_Name = 'Project Heated1rstFloor'
    #for all construction, see if some other material than default exists
    cstr = idf.idfobjects['CONSTRUCTION']
    mat = idf.idfobjects['MATERIAL']
    win = idf.idfobjects['WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM']
    #we need to creates the associate wall from the material in two layers
    for id_cstr in cstr:
        Wall_Cstr = []
        for id_mat in mat:
            currentMat = id_mat.Name
            if id_mat.Name.find(' Insulation')>0:
                currentMat = id_mat.Name[:id_mat.Name.find(' Insulation')]
            if id_mat.Name.find(' Inertia')>0:
                currentMat = id_mat.Name[:id_mat.Name.find(' Inertia')]
            if currentMat in id_cstr.Name:
                Wall_Cstr.append(id_mat.Name)
        for id_win in win:
            if id_win.Name in id_cstr.Name:
                Wall_Cstr.append(id_win.Name)
        if len(Wall_Cstr)>0:
            # identification of the order between insulation and inertia
            inertia_idx = 0
            if 'Inertia' in Wall_Cstr[0] and building.ExternalInsulation:
                Wall_Cstr.reverse()
                inertia_idx = 1
            if 'Insulation' in Wall_Cstr[0] and not building.ExternalInsulation:
                Wall_Cstr.reverse()
            # if Rev is present, then we need to reverse the order of the materials because same construction is needed but seen from two adjacent zones (heated and not heated zones) (EP paradigm)
            if 'Rev' in id_cstr.Name:
                Wall_Cstr.reverse()
            if 'Basement' in id_cstr.Name:
                id_cstr.Outside_Layer = Wall_Cstr[inertia_idx]
            else:
                id_cstr.Outside_Layer =  Wall_Cstr[0]
            if len(Wall_Cstr)>1 and 'Basement' not in id_cstr.Name:
                id_cstr.Layer_2 = Wall_Cstr[1] #cannot create a list comprehension for this because the else '' creates an error....
    #setting windows on all wall with ratio specified in the yml file
    idf.set_wwr(building.wwr, construction="Project External Window")
    #used to removed unsued construction (just to limit the warning from EP of unused construction)
    check4UnusedCSTR(idf)

    # creating the material and construction for internalMass effect:
    for key in building.InternalMass:
        BuildIt=True
        if 'NonHeatedZone' in key and building.nbBasefloor == 0:
            BuildIt =False
        if building.InternalMass[key] and BuildIt:
            Envelope_Param.create_MaterialObject(idf, key, building.InternalMass[key])
            Envelope_Param.createNewConstruction(idf, key + 'Obj', key)
    return idf

def check4UnusedCSTR(idf):
    cstr = idf.idfobjects["CONSTRUCTION"]
    surf = idf.idfobjects["BUILDINGSURFACE:DETAILED"]
    fen = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]
    tosupress = []
    for i in cstr:
        Notused = True
        for j in surf:
            if i.Name in j.Construction_Name:
                Notused = False
                break
        for j in fen:
            if i.Name in j.Construction_Name:
                Notused = False
                break
        if Notused:
            tosupress.append(i)
    for i in reversed(tosupress):
        idf.removeidfobject(i)

def createAirwallsCstr(idf):
    #this function could take into account the new available construction type 'Construction:AirBoundary' starting with EP9.2
    #https://unmethours.com/question/41171/constructionairboundary-solar-enclosures-for-grouped-zones-solar-distribution/
    #creating the materials, see Envelope_Param for material specifications
    Envelope_Param.CreateAirwallsMat(idf)
    #for all construction, see if some other material than default exist
    cstr = idf.idfobjects['CONSTRUCTION']
    airmat = idf.getobject('MATERIAL','AirWallMaterial')
    #airmat = idf.getobject('MATERIAL:INFRAREDTRANSPARENT', 'AirWallMaterial') #this was a try to take into account for transperant partition between core/perim nbut also between blocs.... is there any sence ??
    for id_cstr in cstr:
        if 'Partition' in id_cstr.Name:
                id_cstr.Outside_Layer = airmat.Name
    return idf


def split2convex(idf,DebugMode,LogFile):
    surlist = idf.idfobjects['BUILDINGSURFACE:DETAILED']
    idxi = []
    for i, j in enumerate(surlist):
        if j.Outside_Boundary_Condition.lower() == "outdoors" and not('wall' in j.Surface_Type):
            roofcoord = j.coords
            coord2split = []
            for nbpt in roofcoord:
                coord2split.append(nbpt[0:2])
            isconv = geom.polygons.is_convex_polygon(coord2split)
            if not (isconv):
                idxi.append(j.Name)
    import tripy
    for surfi in idxi:
        coord2split = []
        surf2treat = idf.getobject('BUILDINGSURFACE:DETAILED',surfi)
        for nbpt in surf2treat.coords:
            coord2split.append(nbpt[0:2])
        height = nbpt[2]
        # #lets help a bit the process by adding nodes on the longest edges
        # poly = geom.polygons.Polygon2D(coord2split)
        # meanEdge = sum(poly.edges_length)/len(poly.edges_length)
        # largeEdges = [idx for idx, val in enumerate(poly.edges_length) if val > 3*meanEdge]
        # offset = 0
        # for idx in largeEdges:
        #     extraPt = ((poly.edges[idx].p2[0]+2*poly.edges[idx].p1[0])/3,(poly.edges[idx].p2[1]+2*poly.edges[idx].p1[1])/3)
        #     coord2split.insert(idx+1+offset, extraPt)
        #     extraPt = ((2*poly.edges[idx].p2[0] + poly.edges[idx].p1[0]) / 3,
        #                (2*poly.edges[idx].p2[1] + poly.edges[idx].p1[1]) / 3)
        #     coord2split.insert(idx + 2 + offset, extraPt)
        #     offset += idx+2
        #the methods below can lead to very small areas of triangles.
        #We shall avoid this to avoid warnings afterward
        #the work around is to change ending and starting point ofthe polygons and stop when all areas all above a threshold(0.1m2)
        TrianglesOK = False
        nbmove = 0
        while not TrianglesOK:
            trigle = tripy.earclip(coord2split)
            Areas = [Polygon(s).area for s in trigle]
            if min(Areas) >0.1:
                TrianglesOK = True
            else:
                coord2split = [coord2split[-1]] + coord2split[:-1]
                nbmove += 1
                if nbmove > len(coord2split):
                    TrianglesOK = True
                    # msg = '[Warning - Convex] The splitting surface process to make them all convex failed to find all surfaces above 0.1m2...\n'
                    # if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        stillleft = True
        while stillleft:
            mergeTrigle, stillleft = MergeTri(trigle)
            trigle = mergeTrigle
        Areas = [Polygon(s).area for s in trigle]
        if min(Areas) <= 0.1:
            msg = '[Warning - Convex] The splitting surface process to make them all convex failed to find all surfaces above 0.1m2...\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        for nbi, subsurfi in enumerate(trigle):
            new_coord = []
            for nbpt in subsurfi:
                x = nbpt[0]
                y = nbpt[1]
                z = height
                new_coord.append((x, y, z))
            #print(surf2treat.Name + str(nbi))
            surftri = idf.newidfobject(
                "BUILDINGSURFACE:DETAILED",
                Name=surf2treat.Name + '_'+ str(nbi),
                Surface_Type=surf2treat.Surface_Type,
                Construction_Name=surf2treat.Construction_Name,
                Outside_Boundary_Condition=surf2treat.Outside_Boundary_Condition,
                Sun_Exposure=surf2treat.Sun_Exposure,
                Zone_Name=surf2treat.Zone_Name,
                Wind_Exposure=surf2treat.Wind_Exposure,
            )
            surftri.setcoords(new_coord)
            if 'roof' in surf2treat.Name.lower() and surftri.tilt == 180:
                    surftri.setcoords(reversed(new_coord))
            if 'floor' in surf2treat.Name.lower() and surftri.tilt == 0:
                    surftri.setcoords(reversed(new_coord))
        idf.removeidfobject(surf2treat)
    return idf

def MergeTri(trigleNonSorted):
    newTrigle = trigleNonSorted
    #the triangle needs to be sorted by area as very small area can occure, so lets start by merging these ones
    sortedIdx = sorted(range(len(trigleNonSorted)), key=lambda k: Polygon(trigleNonSorted[k]).area)
    trigle = [trigleNonSorted[idx] for idx in sortedIdx]
    for s1,s2 in itertools.combinations(trigle,2):
        polygon1 = Polygon(s1)
        polygon2 = Polygon(s2)
        polygons = [polygon1, polygon2]
        u = cascaded_union(polygons)
        try:
            newsurfcoord = list(u.exterior.coords)[:-1]
            isconv = geom.polygons.is_convex_polygon(newsurfcoord)
            if isconv:
                newTrigle = []
                for i in trigleNonSorted:
                    if not i in [s1,s2]:
                        newTrigle.append(i)
                newTrigle.append(newsurfcoord)
                return newTrigle, True
        except:
            pass
    return newTrigle,False

def composenewtrigle(trigle,data,newsurf):
    newTrigle = []
    surf1 = data['surf1']
    surf2 = data['surf2']
    for i in trigle:
        current = list(i)
        if not str(current) in str(surf1) and not str(current) in str(surf2):
            newTrigle.append(i)
    newTrigle.append(newsurf)
    return newTrigle

def merge2surf(data):
    polygon1 = Polygon(data['surf1'])
    polygon2 = Polygon(data['surf2'])
    polygons = [polygon1, polygon2]
    u = cascaded_union(polygons)
    newsurfcoord = list(u.exterior.coords)[:-1]
    isconv = geom.polygons.is_convex_polygon(newsurfcoord)
    return isconv, newsurfcoord

def edgeLength(node1,node2):
    return ((node1[0] - node2[0]) ** 2 + (node1[1] - node2[1]) ** 2) ** 0.5

def isCommunNode(surf1,surf2):
    egde = []
    idx = []
    for i,nodei in enumerate(surf1):
        for j,nodej in enumerate(surf2):
            if str(nodei) in str(nodej):
                egde.append(nodei)
                idx.append((i,j))
    return egde, idx

if __name__ == '__main__' :
    print('GeomScript Main')