# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

from shapely.geometry.polygon import Polygon, Point, LineString
import CoreFiles.GeneralFunctions as GrlFct
import CoreFiles.MUBES_pygeoj as MUBES_pygeoj
from CoreFiles import setConfig as setConfig
from geomeppy.geom.polygons import Polygon2D, break_polygons, Polygon3D
from geomeppy import IDF
from geomeppy.geom import core_perim
import os
import json
import shutil
import BuildObject.GeomUtilities as GeomUtilities
import re
import CoreFiles.ProbGenerator as ProbGenerator

import matplotlib.pyplot as plt
#this class defines the building characteristics regarding available data in the geojson file

#function that checks if value is out of limits
def checkLim(val, ll, ul):
    if val < ll:
        val = ll
    elif val > ul:
        val = round(val/10)
        if val > ul:
            val = ul
    return val

#get the value from the correct key
def getDBValue(DB, Keys):
    Val = ''
    IdKey = ''
    if type(Keys) ==list:
        for key in Keys:
            try:
                Val = DB[key]
                IdKey = key
                break
            except:
                pass
    else:
        try:
            Val = DB[Keys]
            IdKey = Keys
        except: pass
    return Val,IdKey


#find the wall id for the shading surfaces from surrounding buildings
def findWallId(Id, Shadingsfile, ref,GE):
    finished = 0
    ii = 0
    ShadeWall = {}
    while finished == 0:
        if Id in Shadingsfile[ii].properties[GE['ShadingIdKey']]:
            ShadeWall[GE['BuildingIdKey']] = Shadingsfile[ii].properties[GE['BuildingIdKey']]
            ShadeWall[GE['ShadingIdKey']] = Shadingsfile[ii].properties[GE['ShadingIdKey']]
            try:
                ShadeWall['height'] = float(Shadingsfile[ii].properties['zmax'])-float(Shadingsfile[ii].properties['zmin'])
            except:
                pass
            ShadeWall[GE['VertexKey']] = []
            for jj in Shadingsfile[ii].geometry.coordinates:
                ShadeWall[GE['VertexKey']].append(tuple([jj[0]-ref[0],jj[1]-ref[1]]))
            finished = 1
        else:
            ii = ii+1
        if ii>=len(Shadingsfile):
            finished = 1
    return ShadeWall

#find the height the building's ID
def findBuildId(Id, Buildingsfile,GE):
    finished = 0
    ii = 0
    height = 0
    while finished == 0:
        if Id == Buildingsfile[ii].properties[GE['BuildingIdKey']]:
            height = Buildingsfile[ii].properties['height']
            finished = 1
        else:
            ii = ii+1
        if ii>len(Buildingsfile):
            print('No finded Build Id ....')
            finished = 1
    return height

class BuildingList:
    def __init__(self):
        self.building = []

    def addBuilding(self,name,DataBaseInput,nbcase,MainPath,keypath,LogFile,PlotOnly, DebugMode):
        #idf object is created here
        IDF.setiddname(os.path.join(keypath['epluspath'],"Energy+.idd"))
        idf = IDF(os.path.normcase(os.path.join(keypath['epluspath'],"ExampleFiles/Minimal.idf")))
        idf.idfname = name
        #building object is created here
        building = Building(name, DataBaseInput, nbcase, MainPath,keypath['Buildingsfile'],LogFile,PlotOnly, DebugMode)
        #both are append as dict in the globa studied case list
        self.building.append({
            'BuildData' : building,
            'BuildIDF' : idf,
        }
        )

class Building:
    def __init__(self,name,DataBaseInput,nbcase,MainPath,BuildingFilePath,LogFile,PlotOnly,DebugMode):
        import time
        Buildingsfile = DataBaseInput['Build']
        DB = Buildingsfile[nbcase]
        config = setConfig.read_yaml('ConfigFile.yml')
        DBL = config['3_SIM']['DBLimits']
        BE = config['3_SIM']['3_BasisElement']
        self.GE = config['3_SIM']['GeomElement'] #these element might be needed afterward for parametric simulation, thus the keys words are needed
        EPC = config['3_SIM']['EPCMeters']
        SD = config['3_SIM']['2_SimuData']
        ExEn = config['3_SIM']['ExtraEnergy']
        WeatherData = config['3_SIM']['1_WeatherData']
        try:
            self.CRS = Buildingsfile.crs['properties']['name'] #this is the coordinates reference system for the polygons
        except:
            self.CRS = 'Null'
        self.getBEData(BE)
        self.getSimData(SD)
        self.getSimData(WeatherData)
        self.name = name
        self.BuildingFilePath = BuildingFilePath
        self.BuildID = self.getBuildID(DB,LogFile)
        self.Multipolygon = self.getMultipolygon(DB)
        self.nbfloor = self.getnbfloor(DB, DBL,LogFile,DebugMode)
        self.nbBasefloor = self.getnbBasefloor(DB, DBL)
        self.height = self.getheight(DB, DBL)
        self.DistTol = self.GE['DistanceTolerance']
        self.footprint,  self.BlocHeight, self.BlocNbFloor = self.getfootprint(DB,LogFile,self.nbfloor,DebugMode)
        self.AggregFootprint = self.getAggregatedFootprint()
        self.RefCoord = self.getRefCoord()
        self.DB_Surf = self.getsurface(DB, DBL,LogFile,DebugMode)
        self.SharedBld, self.VolumeCorRatio = self.IsSameFormularIdBuilding(Buildingsfile, nbcase, LogFile, DBL,DebugMode)
        self.BlocHeight, self.BlocNbFloor, self.StoreyHeigth = self.EvenFloorCorrection(self.BlocHeight, self.nbfloor, self.BlocNbFloor, self.footprint, LogFile,DebugMode)
        self.EPHeatedArea = self.getEPHeatedArea(LogFile,DebugMode)
        self.AdjacentWalls = [] #this will be appended in the getshade function if any present
        self.shades = self.getshade(nbcase, Buildingsfile,LogFile, PlotOnly=PlotOnly,DebugMode=DebugMode)
        self.Materials = config['3_SIM']['BaseMaterial']
        self.InternalMass = config['3_SIM']['InternalMass']
        self.MakeRelativeCoord(roundfactor = 4)# we need to convert into local coordinate in order to compute adjacencies with more precision than keeping thousand of km for x and y
        #self.edgesHeights = self.getEdgesHeights(roundfactor= 4)
        if not PlotOnly:
            #the attributres above are needed in all case, the one below are needed only if energy simulation is asked for
            self.VentSyst = self.getVentSyst(DB, config['3_SIM']['VentSyst'], LogFile,DebugMode)
            self.AreaBasedFlowRate = self.getAreaBasedFlowRate(DB, DBL, BE)
            self.OccupType = self.getOccupType(DB, config['3_SIM']['OccupType'], LogFile,DebugMode)
            self.nbStairwell = self.getnbStairwell(DB, DBL)
            #self.WeatherDataFile = WeatherData
            self.year = self.getyear(DB, DBL)
            self.EPCMeters = self.getEPCMeters(DB, EPC, LogFile,DebugMode)
            if len(self.SharedBld) > 0:
                self.CheckAndCorrEPCs(Buildingsfile, LogFile, nbcase, EPC,DebugMode)
            self.nbAppartments = self.getnbAppartments(DB, DBL)
            #we define the internal load only if it's not for making picture
            self.IntLoad = self.getIntLoad(MainPath,LogFile,DebugMode)
            self.DHWInfos = self.getExtraEnergy(ExEn, MainPath)
            #if there are no cooling comsumption, lets considerer a set point at 50deg max
            # for key in self.EPCMeters['Cooling']:
            #     if self.EPCMeters['Cooling'][key]>0:
            #         self.setTempUpL = BE['setTempUpL']
            #         self.intT_freecool = 50
            #     else:
            #         self.setTempUpL = [50]*len(BE['setTempUpL'])

    #No more needed, embedded in the MakeShadowingWallFile
    # def getEdgesHeights(self,roundfactor = 8):
    #     GlobalFootprint = Polygon2D(self.AggregFootprint[:-1])
    #     EdgesHeights = {'Height':[],'Edge':[],'BlocNum': []}
    #     for edge in GlobalFootprint.edges:
    #         EdgesHeights['Edge'].append([(round(x+self.RefCoord[0],roundfactor),round(y+self.RefCoord[1],roundfactor)) for x,y in edge.vertices])
    #         EdgesHeights['Height'].append(0)
    #         EdgesHeights['BlocNum'].append(0)
    #     for idx,poly in enumerate(self.footprint):
    #         localBloc = Polygon2D(poly)
    #         for edge,edge_reversed in zip(localBloc.edges,localBloc.edges_reversed):
    #             Heightidx1 = [idx for idx,val in enumerate(GlobalFootprint.edges) if edge == val]
    #             Heightidx2 = [idx for idx, val in enumerate(GlobalFootprint.edges_reversed) if edge == val]
    #             if Heightidx1 or Heightidx2:
    #                 Heigthidx = Heightidx1 if Heightidx1 else Heightidx2
    #                 EdgesHeights['Height'][Heigthidx[0]] = self.BlocHeight[idx]
    #     EdgesHeights['BldID']= self.BuildID
    #     return EdgesHeights

    def MakeRelativeCoord(self,roundfactor= 8):
        # we need to convert change the reference coordinate because precision is needed for boundary conditions definition:
        newfoot = []
        x,y = self.RefCoord
        self.RefCoord = (round(x,roundfactor),round(y,roundfactor))
        for foot in self.footprint:
            newfoot.append([(round(node[0] - self.RefCoord[0],roundfactor), round(node[1] - self.RefCoord[1],roundfactor)) for node in foot])
        self.footprint = newfoot
        for shade in self.shades.keys():
            newcoord = [(round(node[0] - self.RefCoord[0],roundfactor), round(node[1] - self.RefCoord[1],roundfactor)) for node in
                        self.shades[shade]['Vertex']]
            self.shades[shade]['Vertex'] = newcoord
        newwalls = []
        new_Agreg = [(round(node[0] - self.RefCoord[0],roundfactor), round(node[1] - self.RefCoord[1],roundfactor)) for node in self.AggregFootprint]
        self.AggregFootprint = new_Agreg
        for Wall in self.AdjacentWalls:
            newcoord = [(round(node[0] - self.RefCoord[0],roundfactor), round(node[1] - self.RefCoord[1],roundfactor)) for node in Wall['geometries']]
            Wall['geometries'] = newcoord

    def CheckAndCorrEPCs(self,Buildingsfile,LogFile,nbcase,EPC,DebugMode):
        totHeat = []
        tocheck = [nbcase]+self.SharedBld
        for share in tocheck:
            val = 0
            Meas = self.getEPCMeters(Buildingsfile[share],EPC)
            for key in Meas['Heating'].keys():
                val += Meas['Heating'][key]
            totHeat.append(val)
        # correction on the DDB_SurfBSurf if it is the same on all (should be)
        HeatDiff = [totHeat[idx + 1] - A for idx, A in enumerate(totHeat[:-1])]
        if all(v == 0 for v in HeatDiff):
            newval = 0
            for keyType in self.EPCMeters.keys():
                for key in self.EPCMeters[keyType].keys():
                    try:
                        self.EPCMeters[keyType][key] *= self.VolumeCorRatio
                    except:
                        pass
                    if 'Heating' == keyType:
                        newval += self.EPCMeters['Heating'][key]
            msg = '[EPCs correction] The EPCs total heat needs for the each shared buildings is :'+str(totHeat)+'\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            msg = '[EPCs correction] All EPCs metrix will be modified by the Volume ratio as for the DBSurface\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            msg = '[EPCs correction] For example, the Heat needs is corrected from : '+ str(totHeat[0])+ ' to : '+ str(newval)+'\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)

    def IsSameFormularIdBuilding(self,Buildingsfile,nbcase,LogFile,DBL,DebugMode):
        SharedBld = []
        VolumeCorRatio = 1
        Correction = False
        for nb,Build in enumerate(Buildingsfile):
            try:
                if Build.properties['FormularId'] == self.BuildID['FormularId'] and nb != nbcase:
                    SharedBld.append(nb)
                    Correction = True
            except:
                pass
        maxHeight=[max(self.BlocHeight)]
        floors = [self.nbfloor]
        DB_Surf = [self.DB_Surf]
        Volume = [sum([Polygon(foot).area * self.BlocHeight[idx] for idx,foot in enumerate(self.footprint)])]
        for nb in SharedBld:
            DB_Surf.append(self.getsurface(Buildingsfile[nb], DBL))
            floors.append(self.getnbfloor(Buildingsfile[nb],DBL))
            Bldfootprint,  BldBlocHeight, BldBlocNbFloor = self.getfootprint(Buildingsfile[nb],[],floors[-1])
            maxHeight.append(max(BldBlocHeight))
            Volume.append(sum([Polygon(foot).area * BldBlocHeight[idx] for idx,foot in enumerate(Bldfootprint)]))
        if Correction:
            #some correction is needed on the nb of floor because a higher one, with the same FormularId is higher
            newfloor = max(int(floors[maxHeight.index(max(maxHeight))] / (max(maxHeight) / maxHeight[0])),1)
            msg = '[Shared EPC] Buildings are found with same FormularId: '+str(SharedBld)+'\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            msg = '[Nb Floor Cor] The nb of floors will be corrected by the height ratio of this building with the highests one with same FormularId (but cannot be lower than 1)\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            msg = '[Nb Floor Cor] nb of floors is thus corrected from : '+ str(self.nbfloor)+ ' to : '+ str(newfloor)+'\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            self.nbfloor = newfloor
            #correction on the DB_Surf if it is the same on all (should be)
            Adiff = [DB_Surf[idx+1]-A for idx,A in enumerate(DB_Surf[:-1])]
            if all(v == 0 for v in Adiff):
                VolumeCorRatio = Volume[0] / sum(Volume)
                newATemp = self.DB_Surf * VolumeCorRatio
                msg = '[DB_Surf Cor] The DB_Surf will also be modified by the volume ratio of this building over the volume sum of all concerned building \n'
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                msg = '[DB_Surf Cor] The DB_Surf is thus corrected from : '+ str(self.DB_Surf)+ ' to : '+ str(newATemp)+'\n'
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                self.DB_Surf  = newATemp
        return SharedBld, VolumeCorRatio


    def getBEData(self,BE):
        for key in BE.keys():
            setattr(self, key, BE[key])

    def getExtraEnergy(self,ExEn,MainPath):
        output={}
        for key in ExEn.keys():
            try:
                ifFile = os.path.join(os.path.dirname(MainPath),os.path.normcase(ExEn[key]))
                if os.path.isfile(ifFile):
                    AbsInputFileDir,InputFileDir = self.isInputDir()
                    iflocFile = os.path.join(AbsInputFileDir,os.path.basename(ifFile))
                    if not os.path.isfile(iflocFile):
                        shutil.copy(ifFile,iflocFile)
                    output[key] = os.path.join(InputFileDir,os.path.basename(ifFile))
                else:
                    output[key] = ExEn[key]
            except:
                output[key] = ExEn[key]
        return output

    def getSimData(self,SD):
        for key in SD.keys():
            setattr(self, key, SD[key])

    def getBuildID(self,DB,LogFile):
        BuildID={}
        for key in self.GE['BuildIDKey']:
            try:
                BuildID[key] = DB.properties[key]
                BuildID['BldIDKey'] = key
                break
            except: pass
        if not BuildID:
            BuildID['BldIDKey'] = 'NoBldID'
            BuildID['NoBldID'] = 'NoBldID'
        msg = '[Bld ID] '+ 'BldIDKey'+' : ' + str(BuildID['BldIDKey']) + '\n'
        GrlFct.Write2LogFile(msg, LogFile)
        msg = '[Bld ID] '+ str(BuildID['BldIDKey'])+' : ' + str(BuildID[BuildID['BldIDKey']]) + '\n'
        GrlFct.Write2LogFile(msg, LogFile)
        return BuildID

    # def getMultipolygon(self,DB):
    #     test = DB.geometry.coordinates[0][0][0]
    #     if type(test) is list:
    #         Multipolygon = True
    #     else:
    #         Multipolygon = False
    #     return Multipolygon
    def getMultipolygon(self,DB):
        Multipolygon = False
        try:
            DB.geometry.poly3rdcoord
            Multipolygon = True
        except: pass
        return Multipolygon

    def getRefCoord(self):
        "get the reference coodinates for visualisation afterward"
        #check for Multipolygon first
        if self.Multipolygon:
            centroide = [list(Polygon(foot).centroid.coords) for foot in self.footprint] #same reason than below, foot print is computed before now [list(Polygon(DB.geometry.coordinates[i][0]).centroid.coords) for i in range(len(DB.geometry.coordinates))]
            x = sum([centroide[i][0][0] for i in range(len(centroide))])/len(centroide)
            y = sum([centroide[i][0][1] for i in range(len(centroide))])/len(centroide)
        else:
            centroide = list(Polygon(self.footprint[0]).centroid.coords)# now the foot print is computed nbefore the reference. before it was defined with list(Polygon(DB.geometry.coordinates[0]).centroid.coords)
            x = centroide[0][0]
            y = centroide[0][1]
        #ref = (round(x,8), round(y,8))
        offset = ((2*Polygon(self.AggregFootprint).area)**0.5)/8
        ref = (x-offset, y-offset) #there might be not a true need for suche precision....
        return ref

    def getfootprint(self,DB,LogFile=[],nbfloor=0,DebugMode = False):
        "get the footprint coordinate and the height of each building bloc"
        DistTol = self.GE['DistanceTolerance']
        coord = []
        node2remove =[]
        BlocHeight = []
        BlocNbFloor = []
        #we first need to check if it is Multipolygon
        if self.Multipolygon:
            #then we append all the floor and roof fottprints into one with associate height
            MatchedPoly = [0]*len((DB.geometry.coordinates))
            for idx1,poly1 in enumerate(DB.geometry.coordinates[:-1]):
                for idx2,poly2 in enumerate(DB.geometry.coordinates[idx1+1:]):
                    if GeomUtilities.chekIdenticalpoly(poly1[0], poly2[0]) and  \
                            round(abs(DB.geometry.poly3rdcoord[idx1]-DB.geometry.poly3rdcoord[idx2+idx1+1]),1) >0:
                        MatchedPoly[idx1] = 1
                        MatchedPoly[idx2+idx1+1] = 1
                        newpolycoor,node = GeomUtilities.CleanPoly(poly1[0],DistTol)
                        node2remove.append(node)
                         #polycoor.reverse()
                        #test of identical polygone maybe (encountered from geojon made out of skethup
                        skipit = False
                        for donPoly in coord:
                            if GeomUtilities.chekIdenticalpoly(donPoly, newpolycoor):
                                skipit = True #no need to store the same polygone....
                        if not skipit:
                            coord.append(newpolycoor)
                            BlocHeight.append(round(abs(DB.geometry.poly3rdcoord[idx1]-DB.geometry.poly3rdcoord[idx2+idx1+1]),1))
        else:
            #for dealing with 2D files
            singlepoly = False
            for j in DB.geometry.coordinates[0]:
                if len(j)==2:
                    new = (j[0], j[1])
                    coord.append(tuple(new))
                    singlepoly = True
                else:
                    # new = []
                    # for jj in j:
                    #     new.append(tuple(jj))
                    # # even before skewed angle, we need to check for tiny edge below the tolerance onsdered aftward (0.5m)
                    # pt2remove = []
                    # for edge in Polygon2D(new).edges:
                    #     if edge.length < DistTol:
                    #         pt2remove.append(edge.p2)
                    # for pt in pt2remove:
                    #     if len(new) > 3:
                    #         new.remove(pt)
                    # newpolycoor, node = core_perim.CheckFootprintNodes(new, 5)
                    newpolycoor, node = GeomUtilities.CleanPoly(j, DistTol)
                    coord.append(newpolycoor)
                    node2remove.append(node)
            if singlepoly:
                newpolycoor, node = core_perim.CheckFootprintNodes(coord, 5)
                node2remove.append(node)
                coord = [coord]
            for i in range(len(coord)):
                BlocNbFloor.append(nbfloor)
                BlocHeight.append(self.height)

        #if a polygonew has been seen alone, it means that it should be exruded down to the floor
        if self.Multipolygon:
            for idx,val in enumerate(MatchedPoly):
                if val ==0:
                    if len(DB.geometry.coordinates[idx][0]) > 2 : poly = DB.geometry.coordinates[idx][0]
                    else: poly = DB.geometry.coordinates[idx]
                    missedPoly,node = GeomUtilities.CleanPoly(poly, DistTol)
                    coord.append(missedPoly)
                    node2remove.append(node)
                    height = DB.geometry.poly3rdcoord[idx] if DB.geometry.poly3rdcoord[idx]>0 else self.height
                    BlocHeight.append(height)
        # we need to clean the footprint from the node2remove but not if there are part of another bloc
        newbloccoor = []
        for idx, coor in enumerate(coord):
            newcoor = []
            FilteredNode2remove = []
            single = False
            for node in node2remove[idx]:
                single = True
                for idx1, coor1 in enumerate(coord):
                    if idx != idx1:
                        if coor[node] in coor1 and coor[node] not in [n for i, n in enumerate(coor1[idx1]) if
                                                                      i in node2remove[idx1]]:
                            single = False
                if single:
                    FilteredNode2remove.append(node)
            for nodeIdx, node in enumerate(coor):
                if not nodeIdx in FilteredNode2remove:
                    newcoor.append(node)
            newbloccoor.append(newcoor)
        coord = newbloccoor
        # these following lines are here to highlight holes in footprint and split it into two blocs...
        # it may appear some errors for other building with several blocs and some with holes (these cases havn't been checked)
        poly2merge = []
        for idx, coor in enumerate(coord):
            for i in range(len(coord) - idx - 1):
                if Polygon(coor).contains(Polygon(coord[idx + i + 1])):
                    poly2merge.append([idx, idx + i + 1])
                if Polygon(coord[idx + i + 1]).contains(Polygon(coor)):
                    poly2merge.append([idx + i + 1,idx])
        try:
            for i, idx in enumerate(poly2merge):
                #lets check if it's a tower of smaller foorptin than the base:
                SmallerTower = False
                if BlocHeight[idx[1]]-BlocHeight[idx[0]]>0:
                    SmallerTower = True
                newtry = False

                if newtry :

                    newSurface = GeomUtilities.mergeHole(coord[idx[0]],coord[idx[1]])
                    coord[idx[0]] = newSurface[0]
                    coord[idx[1]] = newSurface[1]
                else:
                    new_surfaces = GeomUtilities.mergeGeomeppy(coord[idx[0]], coord[idx[1]])
                    #new_surfaces = break_polygons(Polygon3D(coord[idx[0]]), Polygon3D(coord[idx[1]]))
                    xs, ys, zs = zip(*list(new_surfaces[0]))
                    coord[idx[0]] = [(xs[nbv], ys[nbv]) for nbv in range(len(xs))]
                    if len(new_surfaces) > 1:
                        xs, ys, zs = zip(*list(new_surfaces[1]))
                        if SmallerTower:
                            coord.append([(xs[nbv], ys[nbv]) for nbv in range(len(xs))])
                            BlocHeight.append(BlocHeight[idx[0]])
                        else:
                            coord[idx[1]] = [(xs[nbv], ys[nbv]) for nbv in range(len(xs))]
                            BlocHeight[idx[1]] = BlocHeight[idx[0]]
                    else:
                        coord.pop(idx[1])
                        BlocHeight.pop(idx[1])


                msg = '[Geom Cor] There is a hole that will split the main surface in two blocs \n'
                GrlFct.Write2LogFile(msg, LogFile)
        except:
            msg = '[Poly Error] Some error are present in the polygon parts. Some are identified as being inside others...\n'
            print(msg[:-1])
            GrlFct.Write2LogFile(msg, LogFile)
            import matplotlib.pyplot as plt
            fig = plt.figure(0)
            for i in coord:
                xs, ys = zip(*i)
                plt.plot(xs, ys, '-.')
            #plt.show()
            # titre = 'FormularId : '+str(DB.properties['FormularId'])+'\n 50A_UUID : '+str(DB.properties['50A_UUID'])
            # plt.title(titre)
            # plt.savefig(self.name+ '.png')
            # plt.close(fig)
    #before submitting the full coordinates, we need to check correspondance in case of multibloc
        coord, validFootprint = GeomUtilities.CheckMultiBlocFootprint(coord,tol = DistTol)
        if not validFootprint:
            msg = '[Poly Error] The different bloc are not adjacent...\n'
            #print(msg[:-1])
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            return
        # multibloc should share at least one edge and not a polygon as bld:a3848e24-d29e-44bc-a395-a25b5fd26598 in area : 0180C3170 of Sodermalm_V4
        SmallEdge = False
        for bloc in coord:
            if [val for val in Polygon2D(bloc).edges_length if val < 2]:
                SmallEdge = True
        if SmallEdge:
            msg = '[Geom Warning] This building has at least one edge length below 2m\n'
            #print(msg[:-1])
            if DebugMode : GrlFct.Write2LogFile(msg, LogFile)
        #lets make a final check of the polygon orientation
        #for energy plu inputs, floor needs to be clockwise oriented
        for poly in coord:
            if GeomUtilities.is_clockwise(poly):
                poly.reverse()
        return coord, BlocHeight, BlocNbFloor

    def EvenFloorCorrection(self,BlocHeight,nbfloor,BlocNbFloor,coord,LogFile,DebugMode=False):
        # we compute a storey height as well to choosen the one that correspond to the highest part of the building afterward
        BlocNbFloor=[] #the number of blocks is reset to comply with the old 2D geojson files is anyway empty for multipolygons files
        StoreyHeigth = 3
        if nbfloor !=0:
            storeyRatio = StoreyHeigth / (max(BlocHeight) / nbfloor) if (max(BlocHeight) / nbfloor) > 0.5 else 1
            msg = '[Geom Info] The max bloc height is : ' + str(round(max(BlocHeight), 2)) + ' for ' + str(
                nbfloor) + ' floors declared in the EPC \n'
        else:
            nbfloor= round(max(BlocHeight)/StoreyHeigth)
            try:
                storeyRatio = StoreyHeigth / (max(BlocHeight) / nbfloor) if (max(BlocHeight) / nbfloor) > 0.5 else 1
            except:
                storeyRatio = 0
            msg = '[Geom Info] The max bloc height is : ' + str(round(max(BlocHeight), 2)) + ' for ' + str(
                nbfloor) + ' floors computed from max bloc height\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        msg = '[Geom Cor] A ratio of ' + str(storeyRatio) + ' will be applied on each bloc height\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)

        for height in range(len(BlocHeight)):
            BlocHeight[height] *= storeyRatio
        for idx, Height in enumerate(BlocHeight):
            val = int(round(Height, 1) / StoreyHeigth)
            BlocNbFloor.append(max(1, val))  # the height is ed to the closest 10cm
            BlocHeight[idx] = BlocNbFloor[-1] * StoreyHeigth
            msg = '[Geom Info] Bloc height : ' + str(BlocHeight[idx]) + ' with ' + str(BlocNbFloor[-1]) + ' nb of floors\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            msg = '[Geom Info] This bloc has a footprint with : ' + str(len(coord[idx])) + ' vertexes\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            if val == 0:
                try:
                    LogFile.write(
                        '[WARNING] /!\ This bloc as a height below 3m, it has been raized to 3m to enable construction /!\ \n')
                except:
                    pass
        return BlocHeight, BlocNbFloor, StoreyHeigth

    def getEPHeatedArea(self,LogFile,DebugMode):
        "get the heated area based on the footprint and the number of floors"
        self.BlocFootprintArea=[]
        EPHeatedArea = 0
        for i,foot in enumerate(self.footprint):
            EPHeatedArea += Polygon(foot).area*self.BlocNbFloor[i]
            self.BlocFootprintArea.append(Polygon(foot).area)
        msg = '[Geom Info] Blocs footprint areas : '+ str(self.BlocFootprintArea)+'\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        msg = '[Geom Info] The total heated area is : ' + str(EPHeatedArea)+' for a declared DB_Surf of : '+str(self.DB_Surf)+' --> discrepancy of : '+str(round((self.DB_Surf-EPHeatedArea)/self.DB_Surf*100,2))+'\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        return EPHeatedArea

    def getsurface(self,DB, DBL,LogFile = [],DebugMode = False):
        "Get the surface from the input file, DB_Surf"
        DB_Surf, IdKey = getDBValue(DB.properties, DBL['surface_key'])
        try: DB_Surf = int(DB_Surf)
        except: DB_Surf = 1
        if DB_Surf == 1:
            msg = '[Geom Error] Surface ID not recognized as number, fixed to 1\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        DB_Surf = checkLim(DB_Surf,DBL['surface_lim'][0],DBL['surface_lim'][1])
        self.DBSurfOriginal= DB_Surf     #this is to keep the original value as some correction might done afterward if more then 1 bld is present in 1 Id
        return int(DB_Surf)

    def getnbfloor(self,DB, DBL,LogFile = [], DebugMode = False):
        "Get the number of floor above ground"
        nbfloor, IdKey = getDBValue(DB.properties, DBL['nbfloor_key'])
        try: nbfloor = int(nbfloor)
        except: nbfloor = 0
        if nbfloor == 0:
            msg = '[EPCs Warning] The nb of floors is 0. It will be defined using the max bloc height and a storey height of 3m\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        nbfloor = checkLim(nbfloor,DBL['nbfloor_lim'][0],DBL['nbfloor_lim'][1])
        return int(nbfloor)

    def getnbStairwell(self,DB, DBL):
        "Get the number of stariwell, need for natural stack effect on infiltration"
        nbStairwell, IdKey = getDBValue(DB.properties, DBL['nbStairwell_key'])
        try: nbStairwell = int(nbStairwell)
        except: nbStairwell=0
        nbStairwell = checkLim(nbStairwell,DBL['nbStairwell_lim'][0],DBL['nbStairwell_lim'][1])
        return int(nbStairwell)


    def getnbBasefloor(self,DB, DBL):
        "Get the number of floor below ground"
        nbBasefloor, IdKey = getDBValue(DB.properties, DBL['nbBasefloor_key'])
        try: nbBasefloor = int(nbBasefloor)
        except: nbBasefloor = 0
        nbBasefloor = checkLim(nbBasefloor,DBL['nbBasefloor_lim'][0],DBL['nbBasefloor_lim'][1])
        return int(nbBasefloor)

    def getyear(self,DB, DBL):
        "Get the year of construction in the input file"
        year, IdKey = getDBValue(DB.properties, DBL['year_key'])
        try: year = int(year)
        except: year = 1900
        year = checkLim(year,DBL['year_lim'][0],DBL['year_lim'][1])
        return int(year)

    def getEPCMeters(self,DB,EPC,LogFile = [], DebugMode = False):
        "Get the EPC meters values"
        Meters = {}
        for key1 in EPC:
            Meters[key1] = {}
            for key2 in EPC[key1]:
                if '_key' in key2:
                    try:
                        Meters[key1][key2[:-4]] = DB.properties[EPC[key1][key2]]
                        Meters[key1][key2[:-4]] = int(DB.properties[EPC[key1][key2]])*EPC[key1][key2[:-4]+'COP']
                    except:
                        pass
        return Meters

    def getnbAppartments(self, DB, DBL):
        "Get the number of appartment in the building"
        nbApp, IdKey = getDBValue(DB.properties, DBL['nbAppartments_key'])
        try: nbApp = int(nbApp)
        except: nbApp = 0
        nbApp = checkLim(nbApp,DBL['nbAppartments_lim'][0],DBL['nbAppartments_lim'][1])
        return int(nbApp)

    def getheight(self, DB, DBL):
        "Get the building height from the input file, but not used if 3D coordinates in the footprints"
        height, IdKey = getDBValue(DB.properties, DBL['height_key'])
        try: height = int(height)
        except: height = 3
        height = checkLim(height,DBL['height_lim'][0],DBL['height_lim'][1])
        return int(height)

    def getAggregatedFootprint(self):
        # lets compute the aggregaded external footprint of the different blocs
        # starting with the first one
        AggregFootprint = self.footprint[0]
        RemainingBlocs = self.footprint[1:]
        idx = 0
        while RemainingBlocs:
            Intersectionline = Polygon(AggregFootprint).intersection(Polygon(RemainingBlocs[idx]))
            if Intersectionline and type(Intersectionline) != Point:
                AggregFootprint = list(Polygon(AggregFootprint).union(Polygon(RemainingBlocs[idx])).exterior.coords)
                RemainingBlocs.remove(RemainingBlocs[idx])
                idx = 0
            else:
                idx += 1
        # in order to close the loop if not already done
        if AggregFootprint[0] != AggregFootprint[-1]:
            AggregFootprint.append(AggregFootprint[0])
        return AggregFootprint

    def getShadesFromJson(self,ShadowingWalls):
        # shades: dict of dict with key being shade ID and sub key are
        # 'Vertex (list of tuple)' \
        # 'height (in m)' \
        # 'distance'
        # and that should be enough
        shades = {}
        RelativeAgregFootprint = [(node[0] - self.RefCoord[0], node[1] - self.RefCoord[1]) for node in
                                  self.AggregFootprint]
        Meancoordx = list(Polygon(RelativeAgregFootprint).centroid.coords)[0][0]
        Meancoordy = list(Polygon(RelativeAgregFootprint).centroid.coords)[0][1]
        for key in ShadowingWalls:
            if self.BuildID[self.BuildID['BldIDKey']] in ShadowingWalls[key]['RecepientBld_ID']:
                x,y = zip(*ShadowingWalls[key]['AbsCoord'])
                meanPx = sum(x)/2- self.RefCoord[0]
                meanPy = sum(y) / 2 - self.RefCoord[1]
                dist = (abs(meanPx - Meancoordx) ** 2 + abs(meanPy - Meancoordy) ** 2) ** 0.5
                shades[key] = {}
                shades[key]['Vertex'] = ShadowingWalls[key]['AbsCoord']
                shades[key]['height'] = ShadowingWalls[key]['Height']
                shades[key]['distance'] = dist
        return shades

    def getshade(self, nbcase, Buildingsfile,LogFile, PlotOnly=True, DebugMode=False):
        "Get all the shading surfaces to be build for surrounding building effect"
        JSONFile = []
        GeJsonFile = []
        shades = {}
        BuildingFileName = os.path.basename(self.BuildingFilePath)
        JSonTest = os.path.join(os.path.dirname(self.BuildingFilePath),BuildingFileName[:BuildingFileName.index('.')] + '_Walls.json')
        GeoJsonTest = os.path.join(os.path.dirname(self.BuildingFilePath),BuildingFileName.replace('Buildings', 'Walls'))
        GeoJsonTest1 = True  if 'Walls' in GeoJsonTest else False
        if os.path.isfile(JSonTest):
            JSONFile = JSonTest
        elif os.path.isfile(GeoJsonTest) and GeoJsonTest1:
            GeJsonFile = GeoJsonTest
        else:
            msg = '[Shadowing Info] No Shadowing wall file were found\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            return shades

        if JSONFile:
            msg = '[Shadowing Info] Shadowing walls are taken from a json file\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            with open(JSONFile) as json_file:
                ShadowingWalls = json.load(json_file)
            return self.getShadesFromJson(ShadowingWalls)
        if GeJsonFile:
            msg = '[Shadowing Info] Shadowing walls are taken from a GeoJson file\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
            Shadingsfile = MUBES_pygeoj.load(GeJsonFile)
            Shadingsfile = GrlFct.checkRefCoordinates(Shadingsfile)
            try:
                GE = self.GE
                shadesID = Buildingsfile[nbcase].properties[GE['ShadingIdKey']]
            except:
                return shades
            ModifiedShadeVertexes ={'ShadeId' : [], 'OldCoord': [], 'NewCoord' : []} #this dict will log the changes in the vertex coordinate to adjust other shading if necesseray afterward

            RelativeAgregFootprint = [(node[0] - self.RefCoord[0], node[1] - self.RefCoord[1]) for node in self.AggregFootprint]
            Meancoordx = list(Polygon(RelativeAgregFootprint).centroid.coords)[0][0]
            Meancoordy = list(Polygon(RelativeAgregFootprint).centroid.coords)[0][1]


            currentRef = self.getRefCoord()
            ref = (0, 0) if currentRef==self.RefCoord else self.RefCoord
            idlist = [-1]
            for m in re.finditer(';', shadesID):
                idlist.append(m.start())
            for ii, sh in enumerate(idlist):
                if ii == len(idlist) - 1:
                    wallId = shadesID[idlist[ii] + 1:]
                else:
                    wallId = shadesID[idlist[ii] + 1:idlist[ii + 1]]
                ShadeWall = findWallId(wallId, Shadingsfile, ref, GE)
                if not ShadeWall:
                    msg = '[Shading Info] The wallId :'+str(wallId)+' is not found in the Wall file'
                    if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                    continue
                if not 'height' in ShadeWall.keys():
                    ShadeWall['height'] = findBuildId(ShadeWall[GE['BuildingIdKey']], Buildingsfile,GE)
                    if ShadeWall['height']==None:
                        ShadeWall['height'] = self.height
                currentShadingElement = [(node[0]-self.RefCoord[0],node[1]-self.RefCoord[1]) for node in ShadeWall[GE['VertexKey']]]
                meanPx = (currentShadingElement[0][0] + currentShadingElement[1][0]) / 2
                meanPy = (currentShadingElement[0][1] + currentShadingElement[1][1]) / 2
                edgelength = LineString(currentShadingElement).length
                if edgelength<2:
                    msg = '[Shadowing Info] This one is dropped, less than 2m wide ('+str(round(edgelength,2))+'m), shading Id : '+ ShadeWall[GE['ShadingIdKey']] +'\n'
                    if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                    #print(msg[:-1])
                    continue
                confirmed,currentShadingElement,OverlapCode = GeomUtilities.checkShadeWithFootprint(RelativeAgregFootprint,
                                currentShadingElement,ShadeWall[GE['ShadingIdKey']],tol = self.GE['DistanceTolerance'])
                if confirmed:
                    if ShadeWall['height']<=(max(self.BlocHeight)+self.StoreyHeigth):
                        OverlapCode +=1
                        ShadeWall['height'] = self.StoreyHeigth*round(ShadeWall['height'] / self.StoreyHeigth) #max(self.BlocHeight)#
                    self.AdjacentWalls.append(ShadeWall)
                    shades[wallId] = {}
                    shades[wallId]['Vertex'] = [(node[0]+self.RefCoord[0],node[1]+self.RefCoord[1]) for node in currentShadingElement]
                    shades[wallId]['height'] = ShadeWall['height']
                    shades[wallId]['distance'] = 0
                    ModifiedShadeVertexes['ShadeId'].append(ShadeWall[GE['ShadingIdKey']])
                    ModifiedShadeVertexes['OldCoord'].append(ShadeWall[GE['VertexKey']])
                    ModifiedShadeVertexes['NewCoord'].append(shades[wallId]['Vertex'])
                    msg = '[Adjacent Wall] This Shading wall is considered as adjacent with an overlap code of '+str(OverlapCode)+', shading Id : ' + ShadeWall[
                        GE['ShadingIdKey']] + '\n'
                    #print(msg[:-1])
                    if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                    continue
                if OverlapCode== 999:
                    msg = '[Shadowing Error] This Shading wall goes inside the building...It is dropped, shading Id : ' + ShadeWall[
                              GE['ShadingIdKey']] + '\n'
                    #print(msg[:-1])
                    if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
                    continue
                dist = (abs(meanPx - Meancoordx) ** 2 + abs(meanPy - Meancoordy) ** 2) ** 0.5
                shades[wallId] = {}
                shades[wallId]['Vertex'] = ShadeWall[GE['VertexKey']]
                shades[wallId]['height'] = round(ShadeWall['height'],2)
                shades[wallId]['distance'] = dist
            return shades




    def getVentSyst(self, DB,VentSystDict,LogFile,DebugMode):
        "Get ventilation system type"
        VentSyst = {}
        for key in VentSystDict:
            try:
                VentSyst[key] = True if 'Ja' in DB.properties[VentSystDict[key]] else False
            except:
                VentSyst[key] = False
        nbVentSyst = [idx for idx, key in enumerate(VentSyst) if VentSyst[key]]
        nbVentSystWithHR = [idx for idx, key in enumerate(VentSyst) if
                            VentSyst[key] and key[-1] == 'X']
        if len(nbVentSyst) > 1:
            msg = '[Vent Warning] This building has '+str(len(nbVentSyst))+' ventilation systems declared\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        if len(nbVentSystWithHR)>1:
            msg = '[Vent Warning] This building has '+str(len(nbVentSystWithHR))+' ventilation systems with heat recovery\n'
            if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        return VentSyst

    def getAreaBasedFlowRate(self, DB, DBL, BE):
        "Get the airflow rates based on the floor area"
        val,key = getDBValue(DB.properties, DBL['AreaBasedFlowRate_key'])
        try: AreaBasedFlowRate = float(val)
        except : AreaBasedFlowRate = BE['AreaBasedFlowRate']
        AreaBasedFlowRate = checkLim(AreaBasedFlowRate,DBL['AreaBasedFlowRate_lim'][0],DBL['AreaBasedFlowRate_lim'][1])
        return AreaBasedFlowRate

    def getOccupType(self,DB,OccupTypeDict,LogFile,DebugMode):
        "get the occupency type of the building"
        OccupType = {}
        self.OccupRate = {}
        for key in OccupTypeDict:
            if '_key' in key:
                try:
                    OccupType[key[:-4]] = int(DB.properties[OccupTypeDict[key]])/100
                except:
                    OccupType[key[:-4]] = 0
            if '_Rate' in key:
                self.OccupRate[key[:-5]] = OccupTypeDict[key]
        msg = '[Usage Info] This building has ' + str(1 - OccupType['Residential']) + ' % of none residential occupancy type\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        return OccupType

    def isInputDir(self):
        InputFileDir = 'InputFiles'
        AbsInputFileDir = os.path.join(os.getcwd(),InputFileDir)
        if not os.path.exists(AbsInputFileDir):
            os.mkdir(AbsInputFileDir)
        return AbsInputFileDir,AbsInputFileDir #both values are identicial since the relative path was still creating issues with FMUs afterward...

    def getIntLoad(self, MainPath,LogFile,DebugMode = False):
        "get the internal load profil or value"
        #we should integrate the loads depending on the number of appartemnent in the building
        type = self.IntLoadType
        # Input_path = os.path.join(MainPath,'InputFiles')
        # #lets used StROBE package by defaults (average over 10 profile
        # IntLoad = os.path.join(Input_path, 'P_Mean_over_10.txt')
        try:
            IntLoad = self.ElecYearlyLoad   #this value is in W\m2 prescies in DB_Data
        except:
            IntLoad = 0
        #now we compute power time series in order to match the measures form EPCs
        eleval = 0
        try :
            for x in self.EPCMeters['ElecLoad']:
                if self.EPCMeters['ElecLoad'][x]:
                    eleval += self.EPCMeters['ElecLoad'][x]*1000 #to convert kW in W
        except:
            pass
        if eleval>0:
            try:
                if 'Cste' in type:
                    IntLoad = eleval/self.EPHeatedArea/8760 #this value is thus in W/m2 #division by number of hours to convert Wh into W
                else:
                    AbsInputFileDir,InputFileDir = self.isInputDir()
                    if 'winter' in type:
                        IntLoad = os.path.join(InputFileDir, self.name + '_winter.txt')
                        ProbGenerator.SigmoFile('winter', self.IntLoadCurveShape, eleval/self.EPHeatedArea * 100, IntLoad) #the *100 is because we have considered 100m2 for the previous file
                    if 'summer' in type:
                        IntLoad = os.path.join(InputFileDir, self.name + '_summer.txt')
                        ProbGenerator.SigmoFile('summer', self.IntLoadCurveShape, eleval / self.EPHeatedArea * 100,IntLoad)  # the *100 is because we have considered 100m2 for the previous file
            except:
                msg = '[Int Load Error] Unable to write the internal load file...\n'
                #print(msg[:-1])
                if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
        return IntLoad