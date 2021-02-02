from shapely.geometry import Polygon
from geomeppy import IDF
import os
import DataBase.DB_Data as DB_Data
DBL = DB_Data.DBLimits
SCD = DB_Data.BasisElement
GE = DB_Data.GeomElement
EPC = DB_Data.EPCMeters
import re
import CoreFiles.ProbGenerator as ProbGenerator
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
def findWallId(Id, Shadingsfile, ref):
    finished = 0
    ii = 0
    ShadeWall = {}
    while finished == 0:
        if Id in Shadingsfile[ii].properties[GE['ShadingIdKey']]:
            ShadeWall[GE['BuildingIdKey']] = Shadingsfile[ii].properties[GE['BuildingIdKey']]
            ShadeWall[GE['ShadingIdKey']] = Shadingsfile[ii].properties[GE['ShadingIdKey']]
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
def findBuildId(Id, Buildingsfile):
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
        self.name = name
        self.RefCoord = self.getRefCoord(DB)
        self.nbfloor = self.getnbfloor(DB)
        self.nbBasefloor = self.getnbBasefloor(DB)
        self.footprint = self.getfootprint(DB)
        self.surface = self.getsurface(DB)
        self.year = self.getyear(DB)
        self.EPCMeters = self.getEPCMeters(DB)
        self.nbAppartments = self.getnbAppartments(DB)
        self.height = self.getheight(DB)
        self.MaxShadingDist = GE['MaxShadingDist']
        self.shades = self.getshade(DB,Shadingsfile,Buildingsfile)
        self.VentSyst = self.getVentSyst(DB)
        self.AreaBasedFlowRate = self.getAreaBasedFlowRate(DB)
        self.OccupType = self.getOccupType(DB)
        self.EnvLeak = SCD['EnvLeak']
        self.OccupHeatRate = SCD['OccupHeatRate']
        self.BasementAirLeak= SCD['BasementAirLeak']
        self.nbStairwell = self.getnbStairwell(DB)
        self.Officehours = [SCD['Office_Open'],SCD['Office_Close']]
        self.DCV = SCD['DemandControlledVentilation']
        self.OccupBasedFlowRate = SCD['OccupBasedFlowRate'] / 1000  # the flow rate is thus in m3/s/person
        self.EPHeatedArea = self.getEPHeatedArea()
        self.wwr = SCD['wwr']
        self.ExternalInsulation = SCD['ExternalInsulation']
        self.OffOccRandom = SCD['OffOccRandom']
        self.setTempUpL =  SCD['setTempUpL']
        self.setTempLoL = SCD['setTempLoL']
        self.Materials = DB_Data.BaseMaterial
        self.WeatherDataFile = DB_Data.WeatherFile['Loc']
        self.InternalMass = DB_Data.InternalMass
        self.IntLoad = self.getIntLoad(MainPath)
        self.ACH_freecool = SCD['ACH_freecool']
        self.intT_freecool = SCD['intT_freecool']
        self.dT_freeCool = SCD['dT_freeCool']
        #if there are no cooling comsumption, lets considerer a set point at 50deg max
        for key in self.EPCMeters['Cooling']:
            if self.EPCMeters['Cooling'][key]>0:
                self.setTempUpL = SCD['setTempUpL']
            else:
                self.setTempUpL = 50

    def getRefCoord(self,DB):
        x = DB.geometry.coordinates[0][0][0]
        y = DB.geometry.coordinates[0][0][1]
        ref = (x, y)
        return ref

    def getfootprint(self,DB):
        coord = []
        for i, j in enumerate(DB.geometry.coordinates[0]):
            x = DB.geometry.coordinates[0][i][0]
            y = DB.geometry.coordinates[0][i][1]
            new = (x, y)
            new_coor = []
            for ii in range(len(self.RefCoord)):
                new_coor.append((new[ii] - self.RefCoord[ii]))
            coord.append(tuple(new_coor))
        return coord

    def getEPHeatedArea(self):
        EPHeatedArea = Polygon(self.footprint).area * self.nbfloor
        return EPHeatedArea

    def getsurface(self,DB):
        "Get the surface from the input file"
        try:
            surf = int(DB.properties[DBL['surface_key'] ])
        except:
            surf = 100
        surf = checkLim(surf,DBL['surface_lim'][0],DBL['surface_lim'][1])
        return surf

    def getnbfloor(self,DB):
        "Get the number of floor above ground"
        try:
            nbfloor = int(DB.properties[DBL['nbfloor_key']])
        except:
            nbfloor = 1
        nbfloor = checkLim(nbfloor,DBL['nbfloor_lim'][0],DBL['nbfloor_lim'][1])
        return nbfloor

    def getnbStairwell(self,DB):
        "Get the number of floor above ground"
        try:
            nbStairwell = int(DB.properties[DBL['Stairwell_key']])
        except:
            nbStairwell = 0
        nbStairwell = checkLim(nbStairwell,DBL['nbStairwell_lim'][0],DBL['nbStairwell_lim'][1])
        return nbStairwell


    def getnbBasefloor(self,DB):
        "Get the number of floor below ground"
        try:
            nbBasefloor = int(DB.properties[DBL['nbBasefloor_key']])
        except:
            nbBasefloor = 0
        nbBasefloor = checkLim(nbBasefloor,DBL['nbBasefloor_lim'][0],DBL['nbBasefloor_lim'][1])
        return nbBasefloor

    def getyear(self,DB):
        "Get the surface from the input file"
        try:
            year = int(DB.properties[DBL['year_key']])
        except:
            year = 1900
        year = checkLim(year,DBL['year_lim'][0],DBL['year_lim'][1])
        return year

    def getEPCMeters(self,DB):
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

    def getnbAppartments(self, DB):
        "Get the Thermal energy consumptiom"
        try:
            nbApp = int(DB.properties[DBL['nbAppartments_key']])
        except:
            nbApp = 0
        nbApp = checkLim(nbApp,DBL['nbAppartments_lim'][0],DBL['nbAppartments_lim'][1])
        return nbApp

    def getheight(self, DB):
        "Get the Thermal energy consumptiom"
        try:
            height = int(DB.properties[DBL['height_key']])
        except:
            height = 0
        height = checkLim(height,DBL['height_lim'][0],DBL['height_lim'][1])
        return height

    def getshade(self, DB,Shadingsfile,Buildingsfile):
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

            ShadeWall = findWallId(wallId, Shadingsfile, ref)
            ShadeWall['height'] = findBuildId(ShadeWall[GE['BuildingIdKey']], Buildingsfile)
            meanPx = ShadeWall[GE['VertexKey']][0][0] + ShadeWall[GE['VertexKey']][1][0]
            meanPy = ShadeWall[GE['VertexKey']][0][1] + ShadeWall[GE['VertexKey']][1][1]
            coordx = []
            coordy = []
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
                    # print('error on Building ', ShadeWall['byggnadsid'], 'for shading constructions, current building height will be applied')
                    ShadeWall['height'] = self.height
                shades[wallId] = {}
                shades[wallId]['Vertex'] = ShadeWall[GE['VertexKey']]
                shades[wallId]['height'] = ShadeWall['height']
        return shades

    def getVentSyst(self, DB):
        VentSyst = {}
        for key in DB_Data.VentSyst:
            try:
                VentSyst[key] = [True if 'Ja' in DB.properties[DB_Data.VentSyst[key]] else False]
            except:
                VentSyst[key] = False
        return VentSyst

    def getAreaBasedFlowRate(self, DB):
        try:
            AreaBasedFlowRate = float(DB.properties[DBL['AreaBasedFlowRate_key']])
        except:
            AreaBasedFlowRate = 0  #l/s/m2, minimum flowrate
        AreaBasedFlowRate = checkLim(AreaBasedFlowRate,DBL['AreaBasedFlowRate_lim'][0],DBL['AreaBasedFlowRate_lim'][1])
        return AreaBasedFlowRate/1000 #in order to have it in m3/s/m2

    def getOccupType(self,DB):
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
        #we should integrate the loads depending on the number of appartemnent in the building
        Input_path = os.path.join(MainPath,'InputFiles')
        IntLoad = os.path.join(Input_path,'P_Mean_over_10.txt')
        eleval = 0
        for x in self.EPCMeters['ElecLoad']:
            if self.EPCMeters['ElecLoad'][x]:
                eleval += self.EPCMeters['ElecLoad'][x]*1000 #division by number of hours to convert Wh into W
        IntLoad = eleval/self.EPHeatedArea/8760 #this value is thus in W/m2
        # if eleval>0:
        #     IntLoad = os.path.join(Input_path, self.name + '_Winter.txt')
        #     ProbGenerator.SigmoFile('Summer', 5, eleval/self.EPHeatedArea*100, IntLoad) #the *100 is because we have considered 100m2 for the previous file
        return IntLoad


