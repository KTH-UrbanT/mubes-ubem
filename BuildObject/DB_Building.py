# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

from shapely.geometry import Polygon, Point
import CoreFiles.GeneralFunctions as GrlFct
from geomeppy.geom.polygons import Polygon2D, Polygon3D,break_polygons
from shapely.geometry import Polygon as SPoly
from geomeppy import IDF
from geomeppy.geom import core_perim
import os
import shutil
import BuildObject.DB_Data as DB_Data
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

    def addBuilding(self,name,DataBaseInput,nbcase,MainPath,epluspath,LogFile,PlotOnly):
        #idf object is created here
        IDF.setiddname(os.path.join(epluspath,"Energy+.idd"))
        idf = IDF(os.path.normcase(os.path.join(epluspath,"ExampleFiles/Minimal.idf")))
        idf.idfname = name
        #building object is created here
        building = Building(name, DataBaseInput, nbcase, MainPath,LogFile,PlotOnly)
        #both are append as dict in the globa studied case list
        self.building.append({
            'BuildData' : building,
            'BuildIDF' : idf,
        }
        )

class Building:

    def __init__(self,name,DataBaseInput,nbcase,MainPath,LogFile,PlotOnly):
        Buildingsfile = DataBaseInput['Build']
        Shadingsfile = DataBaseInput['Shades']
        DB = Buildingsfile[nbcase]
        DBL = DB_Data.DBLimits
        BE = DB_Data.BasisElement
        GE = DB_Data.GeomElement
        EPC = DB_Data.EPCMeters
        SD = DB_Data.SimuData
        ExEn = DB_Data.ExtraEnergy
        self.getBEData(BE)
        self.getSimData(SD)
        self.name = name
        self.BuildID = self.getBuildID(DB, GE,LogFile)
        self.Multipolygon = self.getMultipolygon(DB)
        self.RefCoord = self.getRefCoord(DB)
        self.nbfloor = self.getnbfloor(DB, DBL,LogFile)
        self.nbBasefloor = self.getnbBasefloor(DB, DBL)
        self.height = self.getheight(DB, DBL)
        self.footprint,  self.BlocHeight, self.BlocNbFloor = self.getfootprint(DB,LogFile,self.RefCoord,self.nbfloor)
        self.ATemp = self.getsurface(DB, DBL,LogFile)
        self.SharedBld, self.VolumeCorRatio = self.IsSameFormularIdBuilding(Buildingsfile, nbcase, LogFile, DBL)
        self.BlocHeight, self.BlocNbFloor, self.StoreyHeigth = self.EvenFloorCorrection(self.BlocHeight, self.nbfloor, self.BlocNbFloor, self.footprint, LogFile)
        self.year = self.getyear(DB, DBL)
        self.EPCMeters = self.getEPCMeters(DB,EPC,LogFile)
        if len(self.SharedBld)>0:
            self.CheckAndCorrEPCs(Buildingsfile,LogFile,nbcase,EPC)
        self.nbAppartments = self.getnbAppartments(DB, DBL)
        self.MaxShadingDist = GE['MaxShadingDist']
        self.shades = self.getshade(DB,Shadingsfile,Buildingsfile,GE,LogFile)
        self.VentSyst = self.getVentSyst(DB,LogFile)
        self.AreaBasedFlowRate = self.getAreaBasedFlowRate(DB,DBL, BE)
        self.OccupType = self.getOccupType(DB,LogFile)
        self.nbStairwell = self.getnbStairwell(DB, DBL)
        self.EPHeatedArea = self.getEPHeatedArea(LogFile)
        self.Materials = DB_Data.BaseMaterial
        self.WeatherDataFile = DB_Data.WeatherFile['Loc']
        self.InternalMass = DB_Data.InternalMass
        if not PlotOnly:
            self.IntLoad = self.getIntLoad(MainPath,LogFile)
            self.DHWInfos = self.getExtraEnergy(ExEn, MainPath)
        #if there are no cooling comsumption, lets considerer a set point at 50deg max
        for key in self.EPCMeters['Cooling']:
            if self.EPCMeters['Cooling'][key]>0:
                self.setTempUpL = BE['setTempUpL']
            else:
                self.setTempUpL = [50]*len(BE['setTempUpL'])

    def CheckAndCorrEPCs(self,Buildingsfile,LogFile,nbcase,EPC):
        totHeat = []
        tocheck = [nbcase]+self.SharedBld
        for share in tocheck:
            val = 0
            Meas = self.getEPCMeters(Buildingsfile[share],EPC,[])
            for key in Meas['Heating'].keys():
                val += Meas['Heating'][key]
            totHeat.append(val)
        # correction on the ATemp if it is the same on all (should be)
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
            GrlFct.Write2LogFile(msg, LogFile)
            msg = '[EPCs correction] All EPCs metrix will be modified by the Volume ratio as for ATemp\n'
            GrlFct.Write2LogFile(msg, LogFile)
            msg = '[EPCs correction] For example, the Heat needs is corrected from : '+ str(totHeat[0])+ ' to : '+ str(newval)+'\n'
            GrlFct.Write2LogFile(msg, LogFile)

    def IsSameFormularIdBuilding(self,Buildingsfile,nbcase,LogFile,DBL):
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
        ATemp = [self.ATemp]
        Volume = [sum([Polygon(foot).area * self.BlocHeight[idx] for idx,foot in enumerate(self.footprint)])]
        for nb in SharedBld:
            ATemp.append(self.getsurface(Buildingsfile[nb], DBL,[]))
            BldRefCoord = self.getRefCoord(Buildingsfile[nb])
            floors.append(self.getnbfloor(Buildingsfile[nb],DBL,LogFile))
            Bldfootprint,  BldBlocHeight, BldBlocNbFloor = self.getfootprint(Buildingsfile[nb],[],BldRefCoord,floors[-1])
            maxHeight.append(max(BldBlocHeight))
            Volume.append(sum([Polygon(foot).area * BldBlocHeight[idx] for idx,foot in enumerate(Bldfootprint)]))
        if Correction:
            #some correction is needed on the nb of floor because a higher one, with the same FormularId is higher
            newfloor = max(int(floors[maxHeight.index(max(maxHeight))] / (max(maxHeight) / maxHeight[0])),1)
            msg = '[Shared EPC] Buildings are found with same FormularId: '+str(SharedBld)+'\n'
            GrlFct.Write2LogFile(msg, LogFile)
            msg = '[Nb Floor Cor] The nb of floors will be corrected by the height ratio of this building with the highests one with same FormularId (but cannot be lower than 1)\n'
            GrlFct.Write2LogFile(msg, LogFile)
            msg = '[Nb Floor Cor] nb of floors is thus corrected from : '+ str(self.nbfloor)+ ' to : '+ str(newfloor)+'\n'
            GrlFct.Write2LogFile(msg, LogFile)
            self.nbfloor = newfloor
            #correction on the ATemp if it is the same on all (should be)
            Adiff = [ATemp[idx+1]-A for idx,A in enumerate(ATemp[:-1])]
            if all(v == 0 for v in Adiff):
                VolumeCorRatio = Volume[0] / sum(Volume)
                newATemp = self.ATemp * VolumeCorRatio
                msg = '[ATemp Cor] The ATemp will also be modified by the volume ratio of this building over the volume sum of all concerned building \n'
                GrlFct.Write2LogFile(msg, LogFile)
                msg = '[ATemp Cor] The ATemp is thus corrected from : '+ str(self.ATemp)+ ' to : '+ str(newATemp)+'\n'
                GrlFct.Write2LogFile(msg, LogFile)
                self.ATemp  = newATemp
        return SharedBld, VolumeCorRatio


    def getBEData(self,BE):
        for key in BE.keys():
            setattr(self, key, BE[key])

    def getExtraEnergy(self,ExEn,MaintPath):
        output={}
        for key in ExEn.keys():
            try:
                ifFile = os.path.join(os.path.dirname(MaintPath),os.path.normcase(ExEn[key]))
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

    def getBuildID(self,DB,GE,LogFile):
        BuildID={}
        for key in GE['BuildIDKey']:
            try:
                BuildID[key] = DB.properties[key]
            except:
                BuildID[key] = None
        msg = '[Bld ID] 50A_UUID : ' + str(BuildID['50A_UUID']) + '\n'
        GrlFct.Write2LogFile(msg, LogFile)
        msg = '[Bld ID] FormularId : ' + str(BuildID['FormularId']) + '\n'
        GrlFct.Write2LogFile(msg, LogFile)
        return BuildID

    def getMultipolygon(self,DB):
        test = DB.geometry.coordinates[0][0][0]
        if type(test) is list:
            Multipolygon = True
        else:
            Multipolygon = False
        return Multipolygon

    def getRefCoord(self,DB):
        "get the reference coodinates for visualisation afterward"
        #check for Multipolygon first
        test = DB.geometry.coordinates[0][0][0]
        if type(test) is list:
            centroide = [list(Polygon(DB.geometry.coordinates[i][0]).centroid.coords) for i in range(len(DB.geometry.coordinates))]
            x = sum([centroide[i][0][0] for i in range(len(centroide))])/len(centroide)
            y = sum([centroide[i][0][1] for i in range(len(centroide))])/len(centroide)
        else:
            centroide = list(Polygon(DB.geometry.coordinates[0]).centroid.coords)
            x = centroide[0][0]
            y = centroide[0][1]
        ref = (round(x,2), round(y,2))
        return ref

    def getfootprint(self,DB,LogFile=[],RefCoord=[],nbfloor=0):
        "get the footprint coordinate and the height of each building bloc"
        coord = []
        node2remove =[]
        BlocHeight = []
        BlocNbFloor = []
        #we first need to check if it is Multipolygon
        if self.Multipolygon:
            #then we append all the floor and roof fottprints into one with associate height
            for idx1,poly1 in enumerate(DB.geometry.coordinates[:-1]):
                for idx2,poly2 in enumerate(DB.geometry.coordinates[idx1+1:]):
                    if poly1 == poly2:
                        polycoor = []
                        for j in poly1[0]:
                            new = (j[0], j[1])
                            new_coor = new#[]
                            # for ii in range(len(RefCoord)):
                            #     new_coor.append((new[ii] - RefCoord[ii]))
                            polycoor.append(tuple(new_coor))
                        if polycoor[0]==polycoor[-1]:
                            polycoor = polycoor[:-1]
                        newpolycoor, node = core_perim.CheckFootprintNodes(polycoor,5)
                        node2remove.append(node)
                        #polycoor.reverse()
                        coord.append(polycoor)
                        BlocHeight.append(round(abs(DB.geometry.poly3rdcoord[idx1]-DB.geometry.poly3rdcoord[idx2+idx1+1]),1))
            #these following lines are here to highlight holes in footprint and split it into two blocs...
            #it may appear some errors for other building with several blocs and some with holes (these cases havn't been checked)
            poly2merge = []
            for idx, coor in enumerate(coord):
                for i in range(len(coord)-idx-1):
                    if SPoly(coor).contains(SPoly(coord[idx+i+1])):
                        poly2merge.append([idx,idx+i+1])
            try:
                for i,idx in enumerate(poly2merge):
                    new_surfaces = break_polygons(Polygon3D(coord[idx[0]]), Polygon3D(coord[idx[1]]))
                    xs,ys,zs = zip(*list(new_surfaces[0]))
                    coord[idx[0]] = [(xs[nbv],ys[nbv]) for nbv in range(len(xs))]
                    xs,ys,zs = zip(*list(new_surfaces[1]))
                    coord[idx[1]] = [(xs[nbv],ys[nbv]) for nbv in range(len(xs))]
                    BlocHeight[idx[1]] = BlocHeight[idx[0]]
                    msg ='[Geom Cor] There is a hole that will split the main surface in two blocs \n'
                    GrlFct.Write2LogFile(msg, LogFile)
            except:
                msg = '[Poly Error] Some error are present in the polygon parts. Some are identified as being inside others...\n'
                print(msg[:-1])
                GrlFct.Write2LogFile(msg, LogFile)
                import matplotlib.pyplot as plt
                fig = plt.figure(0)
                for i in coord:
                    xs,ys = zip(*i)
                    plt.plot(xs,ys,'-.')
                #titre = 'FormularId : '+str(DB.properties['FormularId'])+'\n 50A_UUID : '+str(DB.properties['50A_UUID'])
                # plt.title(titre)
                # plt.savefig(self.name+ '.png')
                # plt.close(fig)

            #we need to clean the foot print from the node2remove but not if there are part of another bloc
            newbloccoor= []
            for idx,coor in enumerate(coord):
                newcoor = []
                FilteredNode2remove = []
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
                new_coor = new#[]
                # for ii in range(len(self.RefCoord)):
                #     new_coor.append((new[ii] - self.RefCoord[ii]))
                coord.append(tuple(new_coor))
            BlocNbFloor.append(nbfloor)
            BlocHeight.append(self.height)
            coord= [coord]
        return coord, BlocHeight, BlocNbFloor

    def EvenFloorCorrection(self,BlocHeight,nbfloor,BlocNbFloor,coord,LogFile):
        # we compute a storey height as well to choosen the one that correspond to the highest part of the building afterward
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
        GrlFct.Write2LogFile(msg, LogFile)
        msg = '[Geom Cor] A ratio of ' + str(storeyRatio) + ' will be applied on each bloc height\n'
        GrlFct.Write2LogFile(msg, LogFile)

        for height in range(len(BlocHeight)):
            BlocHeight[height] *= storeyRatio
        for idx, Height in enumerate(BlocHeight):
            val = int(round(Height, 1) / StoreyHeigth)
            BlocNbFloor.append(max(1, val))  # the height is ed to the closest 10cm
            BlocHeight[idx] = BlocNbFloor[-1] * StoreyHeigth
            msg = '[Geom Info] Bloc height : ' + str(BlocHeight[idx]) + ' with ' + str(BlocNbFloor[-1]) + ' nb of floors\n'
            GrlFct.Write2LogFile(msg, LogFile)
            msg = '[Geom Info] This bloc has a footprint with : ' + str(len(coord[idx])) + ' vertexes\n'
            GrlFct.Write2LogFile(msg, LogFile)
            if val == 0:
                try:
                    LogFile.write(
                        '[WARNING] /!\ This bloc as a height below 3m, it has been raized to 3m to enable construction /!\ \n')
                except:
                    pass
        return BlocHeight, BlocNbFloor, StoreyHeigth

    def getEPHeatedArea(self,LogFile):
        "get the heated area based on the footprint and the number of floors"
        self.BlocFootprintArea=[]
#        if self.Multipolygon:
        EPHeatedArea = 0
        for i,foot in enumerate(self.footprint):
            EPHeatedArea += Polygon(foot).area*self.BlocNbFloor[i]
            self.BlocFootprintArea.append(Polygon(foot).area)
        msg = '[Geom Info] Blocs footprint areas : '+ str(self.BlocFootprintArea)+'\n'
        GrlFct.Write2LogFile(msg, LogFile)
        msg = '[Geom Info] The total heated area is : ' + str(EPHeatedArea)+' for a declared ATemp of : '+str(self.ATemp)+' --> discrepancy of : '+str(round((self.ATemp-EPHeatedArea)/self.ATemp*100,2))+'\n'
        GrlFct.Write2LogFile(msg, LogFile)
        # else:
        #     EPHeatedArea = Polygon(self.footprint).area * self.nbfloor
        #     self.BlocFootprintArea.append(Polygon(self.footprint).area)
        return EPHeatedArea

    def getsurface(self,DB, DBL,LogFile):
        "Get the surface from the input file, ATemp"
        try:
            ATemp = int(DB.properties[DBL['surface_key'] ])
            if self.BuildID['50A_UUID']=='e653799c-c19c-4ab8-a110-836b5ec1253c':
                ATemp /= 100
                msg = '[WARNING] This buildings ATemp is divided by 100\n'
                GrlFct.Write2LogFile(msg, LogFile)
        except:
            ATemp = 1
            msg = '[Geom ERROR] Atemp not recognized as number, fixed to 1\n'
            GrlFct.Write2LogFile(msg, LogFile)
        ATemp = checkLim(ATemp,DBL['surface_lim'][0],DBL['surface_lim'][1])
        self.ATempOr= ATemp
        return ATemp

    def getnbfloor(self,DB, DBL,LogFile):
        "Get the number of floor above ground"
        try:
            nbfloor = int(DB.properties[DBL['nbfloor_key']])
        except:
            nbfloor = 0
            msg = '[EPCs Warning] The nb of floors is 0. It will be defined using the max bloc height and a storey height of 3m\n'
            GrlFct.Write2LogFile(msg, LogFile)
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

    def getEPCMeters(self,DB,EPC,LogFile):
        "Get the EPC meters values"
        Meters = {}
        if self.BuildID['50A_UUID'] == 'e653799c-c19c-4ab8-a110-836b5ec1253c':
            cor = 100
            msg = '[WARNING] This buildings EPCs is divided by 100\n'
            GrlFct.Write2LogFile(msg, LogFile)
        else:
            cor = 1
        for key1 in EPC:
            Meters[key1] = {}
            for key2 in EPC[key1]:
                if '_key' in key2:
                    try:
                        Meters[key1][key2[:-4]] = DB.properties[EPC[key1][key2]]
                        Meters[key1][key2[:-4]] = int(DB.properties[EPC[key1][key2]])*EPC[key1][key2[:-4]+'COP']/cor
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

    def getshade(self, DB,Shadingsfile,Buildingsfile,GE,LogFile):
        "Get all the shading surfaces to be build for surrounding building effect"
        shades = {}
        shadesID = DB.properties[GE['ShadingIdKey']]
        ref = (0,0) #self.RefCoord
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
            meanPx = (ShadeWall[GE['VertexKey']][0][0] + ShadeWall[GE['VertexKey']][1][0])/2
            meanPy = (ShadeWall[GE['VertexKey']][0][1] + ShadeWall[GE['VertexKey']][1][1])/2
            coordx = []
            coordy = []
            for j in self.footprint:
                for i in j:
                    coordx.append(i[0])
                    coordy.append(i[1])
            AgregFootprint= []
            for i in range(len(coordx)):
                AgregFootprint.append((coordx[i],coordy[i]))
            #check if some shadingssurfaces are too closeto the building
            if ShadeWall[GE['VertexKey']][0] in AgregFootprint and ShadeWall[GE['VertexKey']][1] in AgregFootprint:
                msg = '[Shading Removed] This Shading wall is ON the building (same vertexes), shading Id : '+ ShadeWall[GE['ShadingIdKey']]+'\n'
                GrlFct.Write2LogFile(msg, LogFile)
                print('[Shading Info] This Shading wall is ON the building (same vertexes), shading Id : '+ ShadeWall[GE['ShadingIdKey']])
                break
            Meancoordx = sum(coordx) / len(coordx)
            Meancoordy = sum(coordy) / len(coordx)
            dist = (abs(meanPx - Meancoordx) ** 2 + abs(meanPy - Meancoordy) ** 2) ** 0.5
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
                    msg = '[Shading Removed] This Shading wall is shorter than 0.1m, shading Id : ' +ShadeWall[GE['ShadingIdKey']] + '\n'
                    GrlFct.Write2LogFile(msg, LogFile)
                    print('Avoid one shade : '+ ShadeWall[GE['ShadingIdKey']])
                if keepit:
                    shades[wallId] = {}
                    shades[wallId]['Vertex'] = ShadeWall[GE['VertexKey']]
                    shades[wallId]['height'] = ShadeWall['height']
        return shades

    def getVentSyst(self, DB,LogFile):
        "Get ventilation system type"
        VentSyst = {}
        for key in DB_Data.VentSyst:
            try:
                VentSyst[key] = True if 'Ja' in DB.properties[DB_Data.VentSyst[key]] else False
            except:
                VentSyst[key] = False
        nbVentSyst = [idx for idx, key in enumerate(VentSyst) if VentSyst[key]]
        nbVentSystWithHR = [idx for idx, key in enumerate(VentSyst) if
                            VentSyst[key] and key[-1] == 'X']
        if len(nbVentSyst) > 1:
            msg = '[Vent Warning] This building has '+str(len(nbVentSyst))+' ventilation systems declared\n'
            GrlFct.Write2LogFile(msg, LogFile)
        if len(nbVentSystWithHR)>1:
            msg = '[Vent Warning] This building has '+str(len(nbVentSystWithHR))+' ventilation systems with heat recovery\n'
            GrlFct.Write2LogFile(msg, LogFile)
        return VentSyst

    def getAreaBasedFlowRate(self, DB, DBL, BE):
        "Get the airflow rates based on the floor area"
        try:
            AreaBasedFlowRate = float(DB.properties[DBL['AreaBasedFlowRate_key']])
        except:
            AreaBasedFlowRate = BE['AreaBasedFlowRate']  #l/s/m2, minimum flowrate
        AreaBasedFlowRate = checkLim(AreaBasedFlowRate,DBL['AreaBasedFlowRate_lim'][0],DBL['AreaBasedFlowRate_lim'][1])
        return AreaBasedFlowRate

    def getOccupType(self,DB,LogFile):
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
        msg = '[Usage Info] This building has ' + str(1 - OccupType['Residential']) + ' % of none residential occupancy type\n'
        GrlFct.Write2LogFile(msg, LogFile)
        return OccupType

    def isInputDir(self):
        InputFileDir = 'InputFiles'
        AbsInputFileDir = os.path.join(os.getcwd(),InputFileDir)
        if not os.path.exists(AbsInputFileDir):
            os.mkdir(AbsInputFileDir)
        return AbsInputFileDir,AbsInputFileDir #both values are identicial since the relative path was still creating issues with FMUs afterward...

    def getIntLoad(self, MainPath,LogFile):
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
                print(msg[:-1])
                GrlFct.Write2LogFile(msg, LogFile)
        return IntLoad


