# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

from geomeppy import geom
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
import CoreFiles.Envelope_Param as Envelope_Param
import itertools

def BuildBloc(idf,perim,bloc,bloc_coord,Height,nbstories,nbBasementstories,BasementstoriesHeight,Perim_depth):
    if perim:
        idf.add_block(
            name='Build' + str(bloc),
            coordinates=bloc_coord,
            height=Height,
            num_stories=nbstories + nbBasementstories,
            # building.nbfloor+building.nbBasefloor, #it defines the numbers of zones !
            below_ground_stories=nbBasementstories,
            below_ground_storey_height=BasementstoriesHeight if nbBasementstories > 0 else 0,
            zoning='core/perim',
            perim_depth=Perim_depth,
        )
    else:
        idf.add_block(
            name='Build' + str(bloc),
            coordinates=bloc_coord,
            height=Height,
            num_stories=nbstories + nbBasementstories,
            # building.nbfloor+building.nbBasefloor, #it defines the numbers of zones !
            below_ground_stories=nbBasementstories,
            below_ground_storey_height=BasementstoriesHeight if nbBasementstories > 0 else 0
        )

def createBuilding(LogFile,idf,building,perim,FloorZoning,ForPlots =False):
    #here, the building geometry is created and extruded for each bloc composing the builing, it uses the function above as well
    Full_coord = building.footprint
    Nb_blocs = len(Full_coord)
    #print('Number of blocs for this building : '+ str(Nb_blocs))
    # try:
    #     LogFile.write('Number of blocs for this building : ' + str(Nb_blocs)+'\n')
    # except:
    #     pass
    for bloc in range(Nb_blocs):
        bloc_coord =  Full_coord[bloc]
        Height = building.BlocHeight[bloc]
        nbstories = building.BlocNbFloor[bloc] if FloorZoning else 1
        nbBasementstories = building.nbBasefloor if FloorZoning else min(building.nbBasefloor,1)
        BasementstoriesHeight = 2.5 if FloorZoning else 2.5*building.nbBasefloor
        Perim_depth = 3 #the perimeter depth is fixed to 3m and is reduced if some issue are encountered.
        matched = False
        while not matched:
            try:
                BuildBloc(idf, perim, bloc, bloc_coord, Height, nbstories, nbBasementstories, BasementstoriesHeight, Perim_depth)
                matched = True
            except:
                Perim_depth = Perim_depth/2
                print('I reduce half the perim depth')
                try:
                    LogFile.write('I reduce half the perim depth\n')
                except:
                    pass
            if Perim_depth<0.5:
                try:
                    LogFile.write(
                    'Sorry, but this building cannot have Perim/Core option..it failed with perim below 0.75m\n')
                except:
                    pass
                return print('Sorry, but this building cannot have Perim/Core option..it failed with perim below 0.75m')

    # the shading walls around the building are created with the function below
    # these are used in the function that defines the boundary conditions
    createShadings(building, idf)
    #this function enable to create all the boundary conditions for all surfaces
    try:
        MatchedShade = idf.intersect_match()
        if MatchedShade:
            LogFile.write('[Nb Adjacent_Surfaces] This building has ' + str(len(MatchedShade)) + ' adiabatic surfaces\n')
        #defineAdjacencies(idf,building)
    except:
        LogFile.write('[Error - Boundary] function intersect_match() failed....\n')
        print('[Error - Boundary] function intersect_match() failed....')
        #this is to generate an erro as it'shandles elswhere
        int('process failded')

    # this last function on the Geometry is here to split the non convex surfaces
    # if not, some warning are appended because of shading computation.
    # it should thus be only the roof surfaces. Non convex internal zone are not concerned as Solar distribution is 'FullExterior'
    try:
        #if not ForPlots:
        split2convex(idf)
    except:
        try:
            LogFile.write('[Error] The Split2convex function failed for this building....\n')
        except:
            pass
        print('The Split2convex function failed for this building....')
        pass

def defineAdjacencies(idf,building):
    # this function was suppose to deal with adiabatic conditions in case of adjacent shadowing element, buyt finaly
    # this paradigm is already embedded in geomeppy and int intersect_match() function
    surfaces = idf.getsurfaces()
    for surf in surfaces:
        if surf.Surface_Type == 'wall' and surf.Outside_Boundary_Condition =='outdoors':
            # fig = plt.figure()
            # ax = plt.axes(projection="3d")
            # x,y,z = zip(*surf.coords)
            # plt.plot(x,y,z)
            if surf.Name == 'Block Build0 Storey 0 Wall 0005':
                a=1
            for wall in building.AdjacentWalls:
                surfshade = [(wall['geometries'][0][0], wall['geometries'][0][1], 0.0), (wall['geometries'][1][0], wall['geometries'][1][1], 0.0),
                             (wall['geometries'][1][0], wall['geometries'][1][1], wall['height']), (wall['geometries'][0][0], wall['geometries'][0][1], wall['height'])]
                # x, y, z = zip(*surfshade)
                # plt.plot(x, y, z)
                #Block Build0 Storey 1 Wall 0001'
                if Polygon(surfshade).intersects(Polygon(surf.coords)) or Polygon(surf.coords).intersects(Polygon(surfshade)):
                    a=1
                # if wall[0][0] in x and wall[1][0] in x and wall[0][1] in y and wall[1][1] in y:
                #     surf.Outside_Boundary_Condition = 'Adiabatic'
                #     surf.Sun_Exposure = 'NoSun'
                #     surf.Wind_Exposure = 'NoWind'


def createRapidGeomElem(idf,building):
    #envelop can be created now and allocated to the correct surfaces
    createEnvelope(idf, building)

    #create parition walls
    #from EP9.2 there is a dedicated construction type (to be tried as well), but 'Fullexeterior' option is still required
    #see https://unmethours.com/question/42542/interior-air-walls-for-splitting-nonconvex-zones/
    # see https://unmethours.com/question/13094/change-all-interior-walls-to-air-walls/
    #see https://unmethours.com/question/41171/constructionairboundary-solar-enclosures-for-grouped-zones-solar-distribution/
    createAirwallsCstr(idf)

    #the shading walls around the building are created with the function below
    #createShadings(building, idf)

    return idf

def createShadings(building,idf):
    for ii,sh in enumerate(building.shades):
        if building.shades[sh]['distance'] <= building.MaxShadingDist:
            idf.add_shading_block(
                name='Shading_'+sh,
                coordinates=building.shades[sh]['Vertex'], #[GeomElement['VertexKey']],
                height=building.shades[sh]['height'],
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
    # lets change the construction for some specific zones surfaces, like the link between none heated zones like
    # basement and the above floors
    # creating the construction, see Envelope_Param for material specifications for seperation with heated and non heated zones
    Envelope_Param.createNewConstruction(idf, 'Project Heated1rstFloor', 'Heated1rstFloor')
    Envelope_Param.createNewConstruction(idf, 'Project Heated1rstFloor Rev', 'Heated1rstFloor')
    # special loop to assign the construction that seperates the basement to the other storeis.
    for idx, zone in enumerate(idf.idfobjects["ZONE"]):
        storey = int(zone.Name[zone.Name.find(
            'Storey') + 6:])  # the name ends with Storey # so lets get the storey number this way
        sur2lookat = (s for s in zone.zonesurfaces if s.key not in ['INTERNALMASS'])
        for s in sur2lookat:
            if s.Surface_Type in 'ceiling' and storey == -1:  # which mean that we are on the basements just below ground
                s.Construction_Name = 'Project Heated1rstFloor Rev'  #this will enable to reverse the construction for the cieling compared to the floor of the adjacent zone
            if s.Surface_Type in 'floor' and storey == 0:  # which mean that we are on the first floors just above basement this states that whether or not there is basement zone, the floor slab is defined by this layer
                s.Construction_Name = 'Project Heated1rstFloor'
    #for all construction, see if some other material than default exist
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
            # if Rev is present, then we need to reverse the order of the materials because same construction but seen from two adjacent zones (heated and not heated zones)
            if 'Rev' in id_cstr.Name:
                Wall_Cstr.reverse()
            if 'Basement' in id_cstr.Name:
                id_cstr.Outside_Layer = Wall_Cstr[inertia_idx]
            else:
                id_cstr.Outside_Layer =  Wall_Cstr[0]
            if len(Wall_Cstr)>1 and 'Basement' not in id_cstr.Name:
                id_cstr.Layer_2 = Wall_Cstr[1] #cannot create a list comprehension for this because the else '' creates an error....


    #setting windows on all wall with ratio specified in DB-Database
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
    Envelope_Param.CreatAirwallsMat(idf)
    #for all construction, see if some other material than default exist
    cstr = idf.idfobjects['CONSTRUCTION']
    airmat = idf.getobject('MATERIAL','AirWallMaterial')
    #airmat = idf.getobject('MATERIAL:INFRAREDTRANSPARENT', 'AirWallMaterial') #this was a try to take into account for transperant partition between core/perim nbut also between blocs.... is there any sence ??
    for id_cstr in cstr:
        if 'Partition' in id_cstr.Name:
                id_cstr.Outside_Layer = airmat.Name
    return idf


def split2convex(idf):
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
                    print('[Splitting Area Warning] The smallest surfaces remain below the threshold for all possible order combination')
        stillleft = True
        while stillleft:
            #mergeTrigle, stillleft = MergeTri(trigle)
            mergeTrigle, stillleft = NewMergeTri(trigle)
            trigle = mergeTrigle
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
            if 'Roof' in surf2treat.Name and surftri.tilt == 180:
                    surftri.setcoords(reversed(new_coord))
        idf.removeidfobject(surf2treat)
    return idf

# def MergeTri(trigleNonSorted):
#     stillleft = True
#     newtrigle = {}
#     #the triangle needs to be sorted by area as very small area can occure, so lets start by merging these ones
#     sortedIdx = sorted(range(len(trigleNonSorted)), key=lambda k: Polygon(trigleNonSorted[k]).area)
#     trigle = [trigleNonSorted[idx] for idx in sortedIdx]
#     for nbi, subsurfi in enumerate(trigle):
#         PossibleMerge = {}
#         PossibleMerge['Edge'] = []
#         PossibleMerge['EdLg'] = []
#         PossibleMerge['surf1'] = []
#         PossibleMerge['surf2'] = []
#         PossibleMerge['surf1Area'] = []
#         PossibleMerge['surf2Area'] = []
#         PossibleMerge['Vertexidx'] = []
#         for nbj, subsurfj in enumerate(trigle):
#             if nbj>nbi:
#                 edge, idx = isCommunNode(subsurfi, subsurfj)
#                 if len(edge)  == 2:
#                     PossibleMerge['Edge'].append(edge)
#                     PossibleMerge['Vertexidx'].append(idx)
#                     PossibleMerge['EdLg'].append(edgeLength(edge[0],edge[1]))
#                     PossibleMerge['surf1']=[i for i in subsurfi]
#                     PossibleMerge['surf2']=[i for i in subsurfj]
#                     PossibleMerge['surf1Area'] = Polygon(subsurfi).area
#                     PossibleMerge['surf2Area'] = Polygon(subsurfj).area
#         newtrigle[nbi]= PossibleMerge
#     #now lets find the longests edge that could lead to merging surfaces
#     #try to merge and if not, lets take the edge just befor and so on
#     finished =0
#     nb_tries = 0
#     while finished==0:
#         lg = 0
#         for key in newtrigle:
#             if newtrigle[key]['EdLg']:
#                 if newtrigle[key]['EdLg'][0] > lg:
#                     lg = newtrigle[key]['EdLg'][0]
#                     idx = key  # dict(sorted(PossibleMerge.items(), key=lambda item: item[1]))
#         try :
#             isconv, newsurf = merge2surf(newtrigle[idx])
#         except:
#             a=1
#         if isconv:
#             newTrigle = composenewtrigle(trigle,newtrigle[idx],newsurf)
#             finished = 1
#         else:
#             nb_tries+=1
#             newtrigle[idx]['EdLg'][0]=0 #we just force the edge length to be 0 in order to avoid the above selection
#             if nb_tries>len(newtrigle):
#                 newTrigle = trigle
#                 stillleft = False
#                 finished = 1
#     return newTrigle,stillleft

def NewMergeTri(trigleNonSorted):
    stillleft = True
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