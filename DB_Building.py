from shapely.geometry import Polygon
import os
import DB_Data
DBL = DB_Data.DBLimits
SCD = DB_Data.BasisElement
GE = DB_Data.GeomElement
import re
#this class defines the building characteristics regarding available data in the geojson file

#function that check if value is out of limits
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



class DB_Build:

    def __init__(self,name,Buildingsfile,Shadingsfile,nbcase):
        DB = Buildingsfile[nbcase]
        self.name = name
        self.RefCoord = self.getRefCoord(DB)
        self.nbfloor = self.getnbfloor(DB)
        self.nbBasefloor = self.getnbBasefloor(DB)
        self.footprint = self.getfootprint(DB)
        self.surface = self.getsurface(DB)
        self.year = self.getyear(DB)
        self.ConsEleTot = self.getConsEleTot(DB)
        self.ConsTheTot = self.getConsTheTot(DB)
        self.nbAppartments = self.getnbAppartments(DB)
        self.height = self.getheight(DB)
        self.shades = self.getshade(DB,Shadingsfile,Buildingsfile)
        self.VentSyst = self.getVentSyst(DB)
        self.AreaBasedFlowRate = self.getAreaBasedFlowRate(DB)
        self.OccupType = self.getOccupType(DB)
        self.EnvLeak = SCD['EnvLeak']
        self.IntLoad = self.getIntLoad(DB)
        self.nbStairwell = self.getnbStairwell(DB)
        self.Officehours = [SCD['Office_Open'],SCD['Office_Close']]
        self.DCV = SCD['DemandControlledVentilation']
        self.OccupBasedFlowRate = SCD['OccupBasedFlowRate'] / 1000  # the flow rate is thus in m3/s/person
        #self.StoreyBuildRatio = 1 / (self.nbfloor + self.nbBasefloor) #no more used as ratio is highlighted by each zone surfaces
        self.EPHeatedArea = self.getEPHeatedArea()
        self.OccupRate = DB_Data.OccupRate
        self.wwr = SCD['WindowWallRatio']
        self.OffOccRandom = SCD['OffOccRandom']

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

    def getConsEleTot(self,DB):
        "Get the Electric energy consumptiom"
        try:
            ConsEleTot = int(DB.properties['EgiSumma2'])
        except:
            ConsEleTot = 0
        return ConsEleTot

    def getConsTheTot(self,DB):
        "Get the Thermal energy consumptiom"
        try:
            ConsTheTot = int(DB.properties['EgiSumma1'])
        except:
            ConsTheTot = 0
        return ConsTheTot

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
            if dist <= GE['MaxShadingDist']:
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
        try :
            BalX = [True if 'ja' in DB.properties['VentTypFTX'] else False]
            Exh = [True if 'ja' in DB.properties['VentTypF'] else False]
            Bal = [True if 'ja' in DB.properties['VentTypFT'] else False]
            Nat = [True if 'ja' in DB.properties['VentTypSjalvdrag'] else False]
            ExhX = [True if 'ja' in DB.properties['VentTypFmed'] else False]
            VentSyst = {'BalX': BalX, 'Exh': Exh, 'Bal': Bal, 'Nat': Nat, 'ExhX': ExhX}
        except:
            VentSyst = {'BalX': False, 'Exh': False, 'Bal': False, 'Nat': False, 'ExhX': False}
        return VentSyst

    def getAreaBasedFlowRate(self, DB):
        try:
            AreaBasedFlowRate = float(DB.properties[DBL['AreaBasedFlowRate_key']])
        except:
            AreaBasedFlowRate = 0  #l/s/m2, minimum flowrate
        AreaBasedFlowRate = checkLim(AreaBasedFlowRate,DBL['AreaBasedFlowRate_lim'][0],DBL['AreaBasedFlowRate_lim'][1])
        return AreaBasedFlowRate/1000 #in order to have it in m3/s/m2

    def getOccupType(self, DB):



        try:
            Residential = DB.properties['EgenAtempBostad']
            Hotel = DB.properties['EgenAtempHotell']
            Restaurant = DB.properties['EgenAtempRestaurang']
            Office = DB.properties['EgenAtempKontor']
            FoodMarket = DB.properties['EgenAtempLivsmedel']
            GoodsMarket = DB.properties['EgenAtempButik']
            Shopping = DB.properties['EgenAtempKopcentrum'] #'I still wonder what is the difference with goods'
            Hospital24h = DB.properties['EgenAtempVard']
            Hospitalday = DB.properties['EgenAtempHotell']
            School = DB.properties['EgenAtempSkolor']
            IndoorSports = DB.properties['EgenAtempBad']
            Other = DB.properties['EgenAtempOvrig']
            AssmbPlace = DB.properties['EgenAtempTeater']
            #OccupRate = DB.properties['EgenAtempSumma']
            OccupType =  {'Residential': Residential,
                           'Hotel': Hotel, 'Restaurant': Restaurant,
                           'Office': Office, 'FoodMarket': FoodMarket,
                           'GoodsMarket': GoodsMarket, 'Shopping': Shopping,
                           'Hospital24h': Hospital24h, 'Hospitalday': Hospitalday,
                           'School': School, 'IndoorSports': IndoorSports,
                           'AssmbPlace' : AssmbPlace,'Other': Other,
                           #'OccupRate': OccupRate,
                           }
        except:
            OccupType = {}
        for key in OccupType.keys():
            try:
                OccupType[key] = int(OccupType[key])/100
            except:
                OccupType[key] = 0
        return OccupType


    def getIntLoad(self, DB):
        #we should integrate the loads depending on the number of appartemnent in the building
        files_path = os.path.dirname(os.getcwd()) + '\\InputFiles\\P_Mean_over_10.txt'
        IntLoad = files_path
        return IntLoad


#
# class DB_Shading:
#
#     def __init__(self,Shade):
#         self.buildID =
#     ShadeWall['byggnadsid'] = Shadingsfile[ii].properties['byggnadsid']
#     ShadeWall['vaggid'] = Shadingsfile[ii].properties['vaggid']
#     ShadeWall['geometries'] = []
#     for jj in Shadingsfile[ii].geometry.coordinates:
#         ShadeWall['geometries'].append(tuple([jj[0] - ref[0], jj[1] - ref[1]]))
#     finished = 1