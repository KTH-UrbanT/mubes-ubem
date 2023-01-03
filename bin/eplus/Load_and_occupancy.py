# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import utilities.ProbGenerator as ProbGenerator
import os

def Schedule_Type(idf):
    #Schedule type creation to refer to for each associated zone's schedule
    #needs to be done once and for all
    idf.newidfobject(
        'SCHEDULETYPELIMITS',
        Name = 'Any Number'
        )
    return idf

def ScheduleCompact(idf, Name, SetPoint):
    #compact schedule object, used when no external file are needed for the set points
    idf.newidfobject(
        "SCHEDULE:COMPACT",
        Name=Name,
        Schedule_Type_Limits_Name='Any Number',
        Field_1='Through: 12/31',
        Field_2='For: AllDays',
        Field_3='Until: 24:00',
        Field_4=SetPoint,
    )
    return idf

def ScheduleCompactOccup(idf,Name,building,SetPoint):
    #schedule for occupant in all but residential areas
    idf.newidfobject(
        "SCHEDULE:COMPACT",
        Name=Name,
        Schedule_Type_Limits_Name='Any Number',
        Field_1='Through: 12/31',
        Field_2='For: AllDays',
        Field_3='Until: '+building.Office_Open,
        Field_4=0,
        Field_5='Until: '+building.Office_Close,
        Field_6=SetPoint,
        Field_7='Until: 24:00',
        Field_8=0,
    )
    return idf


def create_ScheduleFile(idf, Name, fileName):
    #create schedule file, used as soon as specific patterns are required
    idf.newidfobject(
        'SCHEDULE:FILE',
        Name = Name,
        Schedule_Type_Limits_Name = 'Any Number',
        File_Name = fileName,
        Column_Number = 1,
        Rows_to_Skip_at_Top = 0,
        #Minutes_per_Item = 60
        #Column_Separator = 'Space',
        )
    return idf

def create_Occupant(idf, zone, OccScheduleName, ActScheduleName,NbPeople):
    idf.newidfobject(
        'PEOPLE',
        Name = zone.Name+' Occ',
        Zone_or_ZoneList_Name = zone.Name,
        Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name, # this is because E+ changed the above input name by this one in new versions
        Number_of_People_Schedule_Name = OccScheduleName,
        Number_of_People = NbPeople,
        Activity_Level_Schedule_Name = ActScheduleName,
        )
    return idf

def ZoneLoad(idf, zone, LoadSchedule, building, isfile, ZoningMultiplier):
    # the internal loads are emulated by electric equipment as all consumption is released to heat in the zone
    Multiplier = building.IntLoadMultiplier*ZoningMultiplier #if one or several heated floors in the zone
    idf.newidfobject(
        'ELECTRICEQUIPMENT',
        Name = zone.Name+'Load',
        Zone_or_ZoneList_Name = zone.Name,
        Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone.Name, #this is because E+ changed the above input name by this one in new versions
        Schedule_Name = LoadSchedule,
        Design_Level_Calculation_Method = 'Watts/Area',
        #Design_Level = floor_area/100 if isfile else building.IntLoad, #is a multiplier. this means that the file value will be the full zone's load in W
        Watts_per_Zone_Floor_Area = 1/100*Multiplier if isfile else building.IntLoad*Multiplier #the /100 comes from the strobePackage but could be removed now (but see internal load in building class, before)
        )
    return idf

def CreateThermostat(idf,name,setUp, setLo):
    #adding a Thermostat setting
    Therm = idf.newidfobject("HVACTEMPLATE:THERMOSTAT", Name=name)
    if type(setUp) == str:
        Therm.Cooling_Setpoint_Schedule_Name=setUp
    else:
        Therm.Constant_Cooling_Setpoint = max(setLo+4,setUp)
    if type(setLo) == str:
        Therm.Heating_Setpoint_Schedule_Name = setLo
    else:
        Therm.Constant_Heating_Setpoint = setLo
    return idf

def ZoneCtrl(idf,zone,building,PeopleDensity,ThermostatName, Multiplier,Correctdeff,FloorArea):
    #add to all zones an ideal load element driven by the above thermostat
    #DCV stands for Demand Controlled Ventilation, the airflow is in m3/s/m2 thus divded by 1000 from yml
    AreaBasedFlowRate = Correctdeff['AreaBasedFlowRate']
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=zone.Name,
        Template_Thermostat_Name=ThermostatName,
        Heat_Recovery_Type='Sensible' if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 'None',
        Sensible_Heat_Recovery_Effectiveness= Correctdeff['HReff']*building.AirRecovEff if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 0,
        Latent_Heat_Recovery_Effectiveness= 0,
        #Design_Specification_Outdoor_Air_Object_Name = AirNode,
        Outdoor_Air_Method='Sum' if PeopleDensity>0 and building.DemandControlledVentilation else 'Flow/Area',
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area=Multiplier*AreaBasedFlowRate/1000 + Multiplier*building.OccupBasedFlowRate/1000*PeopleDensity*(1-building.DemandControlledVentilation),
        Outdoor_Air_Flow_Rate_per_Person=building.OccupBasedFlowRate/1000,
        Demand_Controlled_Ventilation_Type = 'OccupancySchedule' if PeopleDensity>0 and building.DemandControlledVentilation else 'None',
        Heating_Limit = building.HVACLimitMode,
        Maximum_Sensible_Heating_Capacity =  FloorArea*building.HVACPowLimit, #the floor area already takes into account the zone multiplier
        #Outdoor_Air_Inlet_Node_Name = 'OutdoorAirNode'
        )
    idf.newidfobject(
        "OUTDOORAIR:NODE",
        Name=zone.Name+' IDEAL LOADS OUTDOOR AIR INLET',  # quite weird but it seems to work....the name does not referer to the otherone,
    )
    return idf

def CreateEnvLeakage(idf, zone, building, ExtWallArea):
    # the envelope leak is modeled using a value from BBR standard in l/s/m2 at 50Pa
    # the flow coefficient model enable to deal with this by converting it equivalent cm2 at 4Pa
    # it also take into account the presence of stairwells (flue) that enhances leakage through stack effect
    # enable to precise the flow exponent of 0,67 as well as a wind coefficient and shelter factor ( urban density)
    #coefficient given in the documentation:
    StackCoef = {'WithFlue': [0.069, 0.089, 0.107],
                     'NoFlue': [0.054, 0.078, 0.098]}  # coef for 1,2 and 3 or more storey
    WindCoef = {'WithFlue': [0.142, 0.156, 0.167],
                    'NoFlue': [0.156, 0.170, 0.170]}  # only for basement\slab, no crawlspace
    ShelterFactor = {'WithFlue': [0.7, 0.64, 0.61], 'NoFlue': [0.5, 0.5,0.5]}  # only density 4 is reported here (Typical shelter for urban buildings on larger lots)
    #the stairwell will be considered as flues
    Key = 'WithFlue' if building.nbStairwell>0 else 'NoFlue'
    nbstorey = building.nbfloor if building.nbfloor<4 else 3
    StackCoefVal =StackCoef[Key][nbstorey-1]
    WindCoefVal = WindCoef[Key][nbstorey - 1]
    ShelterFactorVal = ShelterFactor[Key][nbstorey - 1]
    PressureExp = 0.667  # typical exponent for leakage
    #for the flow coefficient : E+ requires a value in m3/s/Pa^n
    #the database gives a value in l/s/m2 under 50Pa
    FlowCoef = building.EnvLeak*ExtWallArea/1000/(50**PressureExp)

    idf.newidfobject(
        "ZONEINFILTRATION:FLOWCOEFFICIENT",
        Name=zone.Name+'Leak',
        Zone_Name = zone.Name,
        Zone_or_Space_Name = zone.Name,# this is because E+ changed the above input name by this one in new versions
        Schedule_Name='AlwaysON',
        Flow_Coefficient= FlowCoef,
        Stack_Coefficient= StackCoefVal,
        Pressure_Exponent = PressureExp,
        Wind_Coefficient= WindCoefVal,
        Shelter_Factor = ShelterFactorVal,
    )
    return idf

def CreateBasementLeakage(idf, zone, ACH):
    #the basement leakage, as not linked to outside, has a constant airchange rate of fresh air
    idf.newidfobject(
        "ZONEINFILTRATION:DESIGNFLOWRATE",
        Name=zone.Name+'Leak',
        Zone_or_ZoneList_Name = zone.Name,
        Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,# this is because E+ changed the above input name by this one in new versions
        Schedule_Name='AlwaysON',
        Design_Flow_Rate_Calculation_Method = 'AirChanges/Hour',
        Air_Changes_per_Hour = ACH,
    )
    return idf

def CreateInternalMass(idf,zone,FloorArea,name,Material):
    #buffering effect of internal mass, taking into account version issues from 9.1.0 and 9.4.0
    surf = 2*Material['WeightperZoneArea']*FloorArea/Material['Density']/Material['Thickness']
    surf = 2 *  FloorArea #as used in https://www.sciencedirect.com/science/article/pii/S036013231930160X?via%3Dihub
    if idf.idd_version == (9,1,0):
        idf.newidfobject(
            "INTERNALMASS",
            Name=zone.Name + 'IntMass',
            Zone_Name=zone.Name,
            Construction_Name=name,
            Surface_Area=round(surf),
        )
    else:
        idf.newidfobject(
            "INTERNALMASS",
            Name=zone.Name + 'IntMass',
            Zone_or_ZoneList_Name=zone.Name,
            Construction_Name=name,
            Surface_Area=round(surf),
        )
    return idf

def ZoneFreeCooling(idf,zone,building,schedule):
    #this function defines a flow rate when ext. temp gives potential for extra cooling
    idf.newidfobject(
        "ZONEVENTILATION:DESIGNFLOWRATE",
        Name=zone.Name + 'FreeCool',
        Zone_or_ZoneList_Name=zone.Name,
        Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,# this is because E+ changed the above input name by this one in new versions
        Schedule_Name=schedule,
        Design_Flow_Rate_Calculation_Method = 'AirChanges/Hour',
        Air_Changes_per_Hour = building.ACH_freecool,
        Ventilation_Type = 'Natural',
        Minimum_Indoor_Temperature = building.intT_freecool,
        Delta_Temperature = building.dT_freeCool
    )
    return idf

def getEfficiencyCor(OfficeTypeZone,ZoningMultiplier,building,PeopleDensity):
    #several assumptions are considered here : if there is two ventilation systems, it means that one is with heat recovery and not the other one
    #it also means that the heat recovery is applied to non residential type of areas.
    #the efficiency of the full zone is thus corrected by the ratio of airflows dedicated to non residential over the total airflow for this floor
    #this correction factor will be applied to the efficiency of the heat recovery define with the HVAC system and for wich value by default is given in the yml file : AirRecovEff
    nbVentSyst = [idx for idx,key in enumerate(building.VentSyst) if building.VentSyst[key]]
    nbVentSystWithHR = [idx for idx, key in enumerate(building.VentSyst) if building.VentSyst[key]and key[-1] == 'X']
    if len(nbVentSyst)>1 and len(nbVentSystWithHR)==1:
        # we need to consider the overall efficency if there is heat recovery in the ventilation system and part of the floor that is occupied by non residential type.
        # we are conservative has only the minimun occupation rate is considered for the airflows
        OfficeAreaAirFlow = OfficeTypeZone * (
                    ZoningMultiplier * building.AreaBasedFlowRate / 1000) + ZoningMultiplier * building.OccupBasedFlowRate / 1000 * PeopleDensity
        TotalAreaAirFlow = ZoningMultiplier * building.AreaBasedFlowRate / 1000 + ZoningMultiplier * building.OccupBasedFlowRate / 1000 * PeopleDensity#this is changed by the 2 lines below on the 6th of October 2021
        MeanBuildingFlowRate = OfficeTypeZone*building.AreaBasedFlowRate+(1-OfficeTypeZone)*building.AreaBasedFlowRateDefault
        TotalAreaAirFlow = ZoningMultiplier * MeanBuildingFlowRate / 1000 + ZoningMultiplier * building.OccupBasedFlowRate / 1000 * PeopleDensity
        Correctdeff = OfficeAreaAirFlow / TotalAreaAirFlow
        ZoneAreaBasedFlowRate = Correctdeff*building.AreaBasedFlowRate + (1-Correctdeff)*building.AreaBasedFlowRateDefault #this is changed by the line below on the 6th of October 2021
        ZoneAreaBasedFlowRate = MeanBuildingFlowRate
    else:
        Correctdeff = 1
        ZoneAreaBasedFlowRate = building.AreaBasedFlowRate
    return {'HReff' : Correctdeff, 'AreaBasedFlowRate' : ZoneAreaBasedFlowRate}

def setWindowShagingControl(idf,Name,ZoneName,surfName):
    #this is to add shadings to window, but not used (used to try things...)
    Details = {'Name': Name,
    'Zone_Name' : ZoneName,
    'Shading_Type' : 'InteriorShade',
    'Shading_Control_Type' : 'AlwaysOn',
    'Shading_Device_Material_Name' : 'Interior_Shade',
               }
    for id,name in enumerate(surfName):
        Details['Fenestration_Surface_'+str(id+1)+'_Name'] = name
    idf.newidfobject('WINDOWSHADINGCONTROL',**Details)


def CreateZoneLoadAndCtrl(idf,building,FloorZoning):
    #this is the main function that calls all the above ones !!
    # create the schedule type if not created before
    if not (idf.getobject('SCHEDULETYPELIMITS', 'Any Number')):
        Schedule_Type(idf)
    # create the Schedule with the input file for the Load (same for all zones) as function of zone area afterward
    #if the building.Intload is a path to a file, then the schedule file needs to be defined, but if some constant value
    # is needed, then there is no need for this schedule and a constant unity schedule instead (lets use the leackage schedule defined below)
    # the constant load will be dealt afterward in the ZoneLoad function with isfile variable
    isfile = False
    try:
        if os.path.isfile(building.IntLoad):
            create_ScheduleFile(idf, 'LoadSchedule', building.IntLoad)
            isfile = True
    except TypeError:
        pass
    # we need a schedule for the infiltration rates in each zone. there will a unique one
    # the set point is 1 (multiplayer)
    ScheduleCompact(idf, 'AlwaysON', 1)
    # we need to define the occupancy activity level in order to avoid a warning and maybe later, compute the heat generated !
    # the set point is defined in yml
    ScheduleCompact(idf, 'OccupActivity', building.OccupHeatRate)
    #for the thermostat of each zone lets first define if there is a need for external file
    if building.setTempLoL[1]-building.setTempLoL[0] == 0:
        HeatSetPoint = building.setTempLoL[0]
    else:
        #this means that we need to create a file for the set points
        pathfile = os.path.join(os.getcwd(), 'InputFiles')
        HeatSetPoint = idf.idfname + '_LoLTempSetPoints.txt'
        create_ScheduleFile(idf, 'HeatSetPointFile', os.path.join(pathfile,HeatSetPoint))
        ProbGenerator.BuildTempSetPoints(HeatSetPoint,pathfile,building.setTempLoL,[building.ComfortTempOn,building.ComfortTempOff])
        HeatSetPoint = 'HeatSetPointFile'
    if building.setTempUpL[1]-building.setTempUpL[0] == 0:
        CoolSetPoint = building.setTempUpL[0]
    else:
        #this means that we need to create a file for the set points
        pathfile = os.path.join(os.getcwd(), 'InputFiles')
        CoolSetPoint = idf.idfname + '_UpLTempSetPoints.txt'
        create_ScheduleFile(idf, 'CoolSetPointFile', os.path.join(pathfile,CoolSetPoint))
        ProbGenerator.BuildTempSetPoints(CoolSetPoint,pathfile,building.setTempUpL,[building.ComfortTempOn,building.ComfortTempOff])
        CoolSetPoint = 'CoolSetPointFile'
    # Create a single thermostat set points for all the zones (might need some other if different set points desired)
    CreateThermostat(idf, 'ResidZone', CoolSetPoint, HeatSetPoint)
    # to all zones adding an ideal load element driven by the above thermostat
    # but how much of non residential areas is to be considered in each zone, it depends on the overall building values
    OfficeOcc = 1 - building.OccupType['Residential'] #all occupancy but residential are taken for the extra airflow of 7 l/s/pers
    # extra variable used below to compute the number of people to be considered in each zone
    PeopleDensity = [0, 0]
    if OfficeOcc != 0:
        for key in building.OccupType.keys():
            if not key in ['Residential']:
                PeopleDensity[0] += building.OccupType[key] / OfficeOcc * min(
                    building.OccupRate[key])  # this is the mean number of people per m2
                PeopleDensity[1] += building.OccupType[key] / OfficeOcc * max(building.OccupRate[key])
    #we need to spread this in all existing blocs based on the area ratio
    BlocOfficeOcc = []
    BlocHeatedArea = []
    BlocOfficechek = []
    BlocPeopleDensity = []
    for i,BlocArea in enumerate(building.BlocFootprintArea):
        BlocOfficeOcc.append(OfficeOcc) #because it is already a ratio, no need to add extra for floor areas  *BlocArea/sum(building.BlocFootprintArea))
        BlocHeatedArea.append(BlocArea*building.BlocNbFloor[i])
        BlocOfficechek.append(0) #it will be turned to 1 when finished to be considered depending on the occupancy rate
        BlocPeopleDensity.append(PeopleDensity)

    #let us go through all the zones but we need to sort them from the lowest ones to the highest one....to have different settings for the basement ones
    # and to put non residential occupation type on the lowest floors first.
    zoneStoreylist =[]
    bloclist = []
    AllZone = idf.idfobjects["ZONE"]
    for idx, zone in enumerate(AllZone):
        try: bloclist.append(int(zone.Name[zone.Name.rfind('Build')+5:zone.Name.find('_Alt')]))
        except: bloclist.append(int(zone.Name[zone.Name.rfind('Build')+5:zone.Name.find('Storey')]))
        zoneStoreylist.append(int(zone.Name[zone.Name.find('Storey')+6:])) #the name ends with Storey # so lets get the storey number this way
    SortedZoneIdx = sorted(range(len(zoneStoreylist)), key=lambda k: zoneStoreylist[k])
    for idx in SortedZoneIdx:
        zone = AllZone[idx]
        bloc = bloclist[idx]
        # we need to compute the envelop area facing outside as well as the floor area (for HVAC)
        ExtWallArea = 0
        sur2lookat = (s for s in zone.zonesurfaces if s.key not in ['INTERNALMASS'])
        # fen2append = []               #this is for having shading on the indoor face of each window
        # fen = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"] #this is for having shading on the indoor face of each window
        for s in sur2lookat:
            if s.Outside_Boundary_Condition in 'outdoors':
                ExtWallArea += s.area
            if s.Surface_Type in 'floor':
                FloorArea = s.area
            # #lets add interior shadings inside the building for each windows
            # for nbfen in fen:
            #     if nbfen.Building_Surface_Name in s.Name:
            #         fen2append.append(nbfen.Name)
        # if fen2append:
        #     setWindowShagingControl(idf, 'ShadingCtrl' + str(idx), zone.Name, fen2append) #this is for having shading on the indoor face of each window

        #we need to create envelope infiltration for each zone facing outside and specific ones for the basement
        if zoneStoreylist[idx]<0: #means that we are in the basement
            # Lets modify the floor area depending on the zoning level
            FloorMultiplier = 1 if FloorZoning else building.nbBasefloor
            FloorArea = FloorArea * FloorMultiplier
            CreateBasementLeakage(idf, zone, ACH=building.BasementAirLeak)
            #creating the internalMass element if the dict is not empty
            if building.InternalMass['NonHeatedZoneIntMass']:
                CreateInternalMass(idf, zone, FloorArea, 'NonHeatedZoneIntMassObj', building.InternalMass['NonHeatedZoneIntMass'])
        else:
            # Lets modify the floor area depending on the zoning level
            FloorMultiplier = 1 if FloorZoning else building.BlocNbFloor[bloc]
            FloorArea = FloorArea * FloorMultiplier
            #creating the internalMass element if the dict is not empty
            if building.InternalMass['HeatedZoneIntMass']:
                CreateInternalMass(idf, zone, FloorArea, 'HeatedZoneIntMassObj', building.InternalMass['HeatedZoneIntMass'])
            if ExtWallArea != 0 and building.EnvLeak !=0 :
                CreateEnvLeakage(idf, zone, building, ExtWallArea)
            # check if Residential occupancy is not a 100% of the building, we shall take into account the ventilation for
            # office hours as well as heat generation from occupancy rates (defined in the yml)
            #as we go along the zones, we should know how much is left (this is done through the 2 lines below)
            #it computes the ratio of the current zone area concerned by office occupation (1 or below for each zone)
            OfficeTypeZone = min(1, BlocOfficeOcc[bloc]/(FloorArea/BlocHeatedArea[bloc])) if BlocOfficechek[bloc] == 0 else 0
            BlocOfficeOcc[bloc] = BlocOfficeOcc[bloc]-(FloorArea/BlocHeatedArea[bloc]) if OfficeTypeZone==1 else BlocOfficeOcc[bloc]
            BlocOfficechek[bloc] = 1 if OfficeTypeZone < 1 else 0 #if 1, it means that this is the last round with office occupancy, the next one will be fully residential
            # We need to define the number of occupant in the current zone depending on the ratio left
            BlocPeopleDensity[bloc] = [i*OfficeTypeZone for i in BlocPeopleDensity[bloc]]
            if OfficeTypeZone>0:
                # for each zone concerned by occupancy : one occupant is defined and the number is controlled  with a schedule
                create_Occupant(idf, zone, 'OccuSchedule'+str(idx), 'OccupActivity', 1)
                if building.OffOccRandom:   #if random occupancy is wished (in yml)
                    #lets create a beta distribution random file for the number of ccupant
                    pathfile = os.path.join(os.getcwd(),'InputFiles')
                    name = idf.idfname + str(idx)+'_OfficeOccu.txt' #building.name + 'nbUsers.txt'
                    ProbGenerator.BuildOccupancyFile(name,pathfile,round(FloorArea*min(BlocPeopleDensity[bloc]),2),round(FloorArea*max(BlocPeopleDensity[bloc]),2), building)
                    create_ScheduleFile(idf, 'OccuSchedule' + str(idx), os.path.join(pathfile, name))
                    if building.setTempUpL[1] - building.setTempUpL[0] == 0:
                        CoolSetPoint = building.setTempUpL[0]
                    else:
                        name = idf.idfname + str(idx) + '_OfficeSetPointUp.txt'  # building.name + 'nbUsers.txt'
                        ProbGenerator.BuildTempSetPoints(name,pathfile,building.setTempUpL,[building.Office_Open,building.Office_Close])
                        create_ScheduleFile(idf, 'OffTsetUp' + str(idx), os.path.join(pathfile, name))
                        CoolSetPoint = 'OffTsetUp' + str(idx)
                    if building.setTempLoL[1] - building.setTempLoL[0] == 0:
                        HeatSetPoint = building.setTempUpL[0]
                    else:
                        name = idf.idfname + str(idx) + '_OfficeSetPointLo.txt'  # building.name + 'nbUsers.txt'
                        ProbGenerator.BuildTempSetPoints(name, pathfile, building.setTempLoL,[building.Office_Open,building.Office_Close])
                        create_ScheduleFile(idf, 'OffTsetLo' + str(idx), os.path.join(pathfile, name))
                        HeatSetPoint = 'OffTsetLo' + str(idx)
                    CreateThermostat(idf, 'OfficeZone'+ str(idx),CoolSetPoint,HeatSetPoint)
                else:
                    ## here is the schedule that defines the number of occupant with fixed number of occupants (same all the time but still linked to shedule).
                    ScheduleCompactOccup(idf, 'OccuSchedule'+str(idx), building, SetPoint= round(FloorArea*max(BlocPeopleDensity[bloc]),2))
            # computation of the zoning level multiplier
            ZoningMultiplier = 1 if FloorZoning else building.BlocNbFloor[bloc]
            # Internal load profile could be taken from the number of apartment. see building.IntLoad in BuildingObject
            ZoneLoad(idf, zone,'LoadSchedule' if isfile else 'AlwaysON' ,building, isfile, ZoningMultiplier)
            # HVAC equipment for each zone including ventilation systems (exhaust, balanced with or not heat recovery)
            ThermostatType = 'OfficeZone'+ str(idx) if building.OffOccRandom and OfficeTypeZone>0 else 'ResidZone'#  if OfficeTypeZone==0 else
            #we need to catch some correction on the efficiency, see the function for more details
            CorrectdEff = getEfficiencyCor(OfficeTypeZone,ZoningMultiplier,building,sum(BlocPeopleDensity[bloc])/2)
            #now the HVAC system is created for this zone
            ZoneCtrl(idf, zone, building, max(BlocPeopleDensity[bloc]),ThermostatType, ZoningMultiplier,CorrectdEff,FloorArea)
            #lets add freecooling to consider that people just open windows when there're too hot !
            ZoneFreeCooling(idf,zone,building,'AlwaysON')

if __name__ == '__main__' :
    print('LoadAndOccupancy Main')