from shapely.geometry import Polygon, Point
from geomeppy.geom.polygons import Polygon2D
from geomeppy import IDF
from geomeppy.geom import core_perim
import os
import DataBase.DB_Data as DB_Data
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
        if ii>len(Shadingsfile):
            print('No finded Wall Id ....')
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

    def addBuilding(self,name,Buildingsfile,Shadingsfile,nbcase,MainPath,epluspath):
        #idf object is created here
        IDF.setiddname(os.path.join(epluspath,"Energy+.idd"))
        idf = IDF(os.path.normcase(os.path.join(epluspath,"ExampleFiles/Minimal.idf")))
        idf.idfname = name
        #building object is created here
        building = Building(name, Buildingsfile, Shadingsfile, nbcase, MainPath)
        #both are append as dict in the globa studied case list
        self.building.append({
            'BuildData' : building,
            'BuildIDF' : idf,
        }
        )

class Building:

    def __init__(self,name,Buildingsfile,Shadingsfile,nbcase,MainPath):
        DB = Buildingsfile[nbcase]
        DBL = DB_Data.DBLimits
        BE = DB_Data.BasisElement
        GE = DB_Data.GeomElement
        EPC = DB_Data.EPCMeters
        SD = DB_Data.SimuData
        self.getBEData(BE)
        self.getSimData(SD)
        self.name = name
        self.RefCoord = self.getRefCoord(DB)
        self.nbfloor = self.getnbfloor(DB, DBL)
        self.nbBasefloor = self.getnbBasefloor(DB, DBL)
        self.footprint = self.getfootprint(DB)
        self.ATemp = self.getsurface(DB, DBL)
        self.year = self.getyear(DB, DBL)
        self.EPCMeters = self.getEPCMeters(DB,EPC)
        self.nbAppartments = self.getnbAppartments(DB, DBL)
        self.height = self.getheight(DB, DBL)
        self.MaxShadingDist = GE['MaxShadingDist']
        self.shades = self.getshade(DB,Shadingsfile,Buildingsfile,GE)
        self.VentSyst = self.getVentSyst(DB)
        self.AreaBasedFlowRate = self.getAreaBasedFlowRate(DB,DBL, BE)
        self.OccupType = self.getOccupType(DB)
        self.nbStairwell = self.getnbStairwell(DB, DBL)
        self.EPHeatedArea = self.getEPHeatedArea()
        self.Materials = DB_Data.BaseMaterial
        self.WeatherDataFile = DB_Data.WeatherFile['Loc']
        self.InternalMass = DB_Data.InternalMass
        self.IntLoad = self.getIntLoad(MainPath)
        self.BuildID = self.getBuildID(DB,GE)

        #if there are no cooling comsumption, lets considerer a set point at 50deg max
        for key in self.EPCMeters['Cooling']:
            if self.EPCMeters['Cooling'][key]>0:
                self.setTempUpL = BE['setTempUpL']
            else:
                self.setTempUpL = 50

    def getBEData(self,BE):
        for key in BE.keys():
            setattr(self, key, BE[key])

    def getSimData(self,SD):
        for key in SD.keys():
            setattr(self, key, SD[key])

    def getBuildID(self,DB,GE):
        BuildID={}
        for key in GE['BuildIDKey']:
            try:
                BuildID[key] = DB.properties[key]
            except:
                BuildID[key] = None
        return BuildID



    def getRefCoord(self,DB):
        "get the reference coodinates for visualisation afterward"
        #check for Multipolygon first
        test = DB.geometry.coordinates[0][0][0]
        if type(test) is list:
            centroide = [list(Polygon(DB.geometry.coordinates[i][0]).centroid.coords) for i in range(len(DB.geometry.coordinates))]
            x = sum([centroide[i][0][0] for i in range(len(centroide))])/len(centroide)
            y = sum([centroide[i][0][1] for i in range(len(centroide))])/len(centroide)
            self.Multipolygon = True
        else:
            centroide = list(Polygon(DB.geometry.coordinates[0]).centroid.coords)
            x = centroide[0][0]
            y = centroide[0][1]
            self.Multipolygon = False
        ref = (x, y)
        #ref = (670000, 6581600) #this is the ref taken for multi building 3D plot
        return ref

    def getfootprint(self,DB):
        "get the footprint coordinate and the height of each building bloc"
        coord = []
        node2remove =[]
        self.BlocHeight = []
        self.BlocNbFloor = []
        #we first need to check if it is Multipolygon
        if self.Multipolygon:
            #then we append all the floor and roff fottprints into one with associate height
            for idx1,poly1 in enumerate(DB.geometry.coordinates[:-1]):
                for idx2,poly2 in enumerate(DB.geometry.coordinates[idx1+1:]):
                    if poly1 == poly2:
                        polycoor = []
                        for j in poly1[0]:
                            new = (j[0], j[1])
                            new_coor = []
                            for ii in range(len(self.RefCoord)):
                                new_coor.append((new[ii] - self.RefCoord[ii]))
                            polycoor.append(tuple(new_coor))
                        if polycoor[0]==polycoor[-1]:
                            polycoor = polycoor[:-1]
                        newpolycoor, node = core_perim.CheckFootprintNodes(polycoor,5)
                        node2remove.append(node)
                        coord.append(polycoor)
                        self.BlocHeight.append(abs(DB.geometry.poly3rdcoord[idx1]-DB.geometry.poly3rdcoord[idx2+idx1+1]))
            #we compute a storey hieght as well to choosen the one that correspond to the highest part of the building afterward
            self.StoreyHeigth = max(self.BlocHeight)/self.nbfloor
            for idx,Height in enumerate(self.BlocHeight):
                self.BlocNbFloor.append(int(Height / self.StoreyHeigth))
            #we need to clean the foot print from the node2 remove but not if there are part of another bloc
            FilteredNode2remove = []
            newbloccoor= []
            for idx,coor in enumerate(coord):
                newcoor = []
                single = False
                for node in node2remove[idx]:
                    single = True
                    for idx1,coor1 in enumerate(coord):
                        if idx!=idx1:
                            if coor[0] in coor1:
                                single =False
                if single:
                    FilteredNode2remove.append(node)
                for nodeIdx,node in enumerate(coor):
                    if not nodeIdx in FilteredNode2remove:
                        newcoor.append(node)
                newbloccoor.append(newcoor)
            coord = newbloccoor

        else:
            #old fashion of making thing with the very first 2D file
            for j in DB.geometry.coordinates[0]:
                new = (j[0], j[1])
                new_coor = []
                for ii in range(len(self.RefCoord)):
                    new_coor.append((new[ii] - self.RefCoord[ii]))
                coord.append(tuple(new_coor))
                self.BlocNbFloor.append(self.nbfloor)
        return coord

    def getEPHeatedArea(self):
        "get the heated area based on the footprint and the number of floors"
        self.BlocFootprintArea=[]
        if self.Multipolygon:
            EPHeatedArea = 0
            for i,foot in enumerate(self.footprint):
                EPHeatedArea += Polygon(foot).area*self.BlocNbFloor[i]
                self.BlocFootprintArea.append(Polygon(foot).area)
        else:
            EPHeatedArea = Polygon(self.footprint).area * self.nbfloor
            self.BlocFootprintArea.append(Polygon(self.footprint).area)
        return EPHeatedArea

    def getsurface(self,DB, DBL):
        "Get the surface from the input file, ATemp"
        try:
            ATemp = int(DB.properties[DBL['surface_key'] ])
        except:
            ATemp = 100
        ATemp = checkLim(ATemp,DBL['surface_lim'][0],DBL['surface_lim'][1])
        return ATemp

    def getnbfloor(self,DB, DBL):
        "Get the number of floor above ground"
        try:
            nbfloor = int(DB.properties[DBL['nbfloor_key']])
        except:
            nbfloor = 1
        nbfloor = checkLim(nbfloor,DBL['nbfloor_lim'][0],DBL['nbfloor_lim'][1])
        return nbfloor

    def getnbStairwell(self,DB, DBL):
        "Get the number of stariwell, need for natural stack effect on infiltration"
        try:
            nbStairwell = int(DB.properties[DBL['Stairwell_key']])
        except:
            nbStairwell = 0
        nbStairwell = checkLim(nbStairwell,DBL['nbStairwell_lim'][0],DBL['nbStairwell_lim'][1])
        return nbStairwell


    def getnbBasefloor(self,DB, DBL):
        "Get the number of floor below ground"
        try:
            nbBasefloor = int(DB.properties[DBL['nbBasefloor_key']])
        except:
            nbBasefloor = 0
        nbBasefloor = checkLim(nbBasefloor,DBL['nbBasefloor_lim'][0],DBL['nbBasefloor_lim'][1])
        return nbBasefloor

    def getyear(self,DB, DBL):
        "Get the year of construction in the input file"
        try:
            year = int(DB.properties[DBL['year_key']])
        except:
            year = 1900
        year = checkLim(year,DBL['year_lim'][0],DBL['year_lim'][1])
        return year

    def getEPCMeters(self,DB,EPC):
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
        try:
            nbApp = int(DB.properties[DBL['nbAppartments_key']])
        except:
            nbApp = 0
        nbApp = checkLim(nbApp,DBL['nbAppartments_lim'][0],DBL['nbAppartments_lim'][1])
        return nbApp

    def getheight(self, DB, DBL):
        "Get the building height from the input file, but not used if 3D coordinates in the footprints"
        try:
            height = int(DB.properties[DBL['height_key']])
        except:
            height = 0
        height = checkLim(height,DBL['height_lim'][0],DBL['height_lim'][1])
        return height

    def getshade(self, DB,Shadingsfile,Buildingsfile,GE):
        "Get all the shading surfaces to be build for surrounding building effect"
        shades = {}
        shadesID = DB.properties[GE['ShadingIdKey']]
        ref = self.RefCoord
        idlist = [-1]
        for m in re.finditer(';', shadesID):
            idlist.append(m.start())
        for ii, sh in enumerate(idlist):
            if ii == len(idlist) - 1:
                wallId = shadesID[idlist[ii] + 1:-1]
            else:
                wallId = shadesID[idlist[ii] + 1:idlist[ii + 1]]
            ShadeWall = findWallId(wallId, Shadingsfile, ref, GE)
            if not 'height' in ShadeWall.keys():
                ShadeWall['height'] = findBuildId(ShadeWall[GE['BuildingIdKey']], Buildingsfile,GE)
            meanPx = ShadeWall[GE['VertexKey']][0][0] + ShadeWall[GE['VertexKey']][1][0]
            meanPy = ShadeWall[GE['VertexKey']][0][1] + ShadeWall[GE['VertexKey']][1][1]
            coordx = []
            coordy = []
            if self.Multipolygon:
                for j in self.footprint:
                    for i in j:
                        coordx.append(i[0])
                        coordy.append(i[1])
            else:
                for i in self.footprint:
                    coordx.append(i[0])
                    coordy.append(i[1])
            coordx = sum(coordx) / len(self.footprint)
            coordy = sum(coordy) / len(self.footprint)
            dist = (abs(meanPx - coordx) ** 2 + abs(meanPy - coordy) ** 2) ** 0.5

            # shading facade are taken into account only of closer than 200m
            if dist <= self.MaxShadingDist:
                try:
                    float(ShadeWall['height'])
                except:
                    ShadeWall['height'] = self.height
                keepit = True
                test = Polygon2D(ShadeWall[GE['VertexKey']]).edges_length
                if test[0]<0.1:
                    keepit = False
                    print('Avoid one shade : '+ ShadeWall[GE['ShadingIdKey']])
                if keepit:
                    shades[wallId] = {}
                    shades[wallId]['Vertex'] = ShadeWall[GE['VertexKey']]
                    shades[wallId]['height'] = ShadeWall['height']
        return shades

    def getVentSyst(self, DB):
        "Get ventilation system type"
        VentSyst = {}
        for key in DB_Data.VentSyst:
            try:
                VentSyst[key] = [True if 'Ja' in DB.properties[DB_Data.VentSyst[key]] else False]
            except:
                VentSyst[key] = False
        return VentSyst

    def getAreaBasedFlowRate(self, DB, DBL, BE):
        "Get the airflow rates based on the floor area"
        try:
            AreaBasedFlowRate = float(DB.properties[DBL['AreaBasedFlowRate_key']])
        except:
            AreaBasedFlowRate = BE['AreaBasedFlowRate']  #l/s/m2, minimum flowrate
        AreaBasedFlowRate = checkLim(AreaBasedFlowRate,DBL['AreaBasedFlowRate_lim'][0],DBL['AreaBasedFlowRate_lim'][1])
        return AreaBasedFlowRate

    def getOccupType(self,DB):
        "get the occupency type of the building"
        OccupType = {}
        self.OccupRate = {}
        for key in DB_Data.OccupType:
            if '_key' in key:
                try:
                    OccupType[key[:-4]] = int(DB.properties[DB_Data.OccupType[key]])/100
                except:
                    OccupType[key[:-4]] = 0
            if '_Rate' in key:
                self.OccupRate[key[:-5]] = DB_Data.OccupType[key]
        return OccupType

    def getIntLoad(self, MainPath):
        "get the internal load profil or value"
        #we should integrate the loads depending on the number of appartemnent in the building
        type = self.IntLoadType
        Input_path = os.path.join(MainPath,'InputFiles')
        #lets used StROBE package by defaults (average over 10 profile
        IntLoad = os.path.join(Input_path, 'P_Mean_over_10.txt')
        #now we compute power time series in order to match the measures form EPCs
        eleval = 0
        try :
            for x in self.EPCMeters['ElecLoad']:
                if self.EPCMeters['ElecLoad'][x]:
                    eleval += self.EPCMeters['ElecLoad'][x]*1000 #division by number of hours to convert Wh into W
        except:
            pass
        if eleval>0:
            if 'Cste' in type:
                IntLoad = eleval/self.EPHeatedArea/8760 #this value is thus in W/m2
            if 'winter' in type:
                IntLoad = os.path.join(Input_path, self.name + '_winter.txt')
                ProbGenerator.SigmoFile('winter', 3, eleval/self.EPHeatedArea * 100, IntLoad) #the *100 is because we have considered 100m2 for the previous file
            if 'summer' in type:
                IntLoad = os.path.join(Input_path, self.name + '_summer.txt')
                ProbGenerator.SigmoFile('summer', 3, eleval / self.EPHeatedArea * 100,IntLoad)  # the *100 is because we have considered 100m2 for the previous file
        return IntLoad


