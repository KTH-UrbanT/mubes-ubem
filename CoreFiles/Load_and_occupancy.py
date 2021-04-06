# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import CoreFiles.ProbGenerator as ProbGenerator
import os
import CoreFiles.Envelope_Param as Envelope_Param
#script to define the loads for each zones
# import os
# import numpy as np
#loads are applied through electric equipments in each zone
#the equipments are steerds by schedules that are related to a file
# the file contains the Power that needs to be applied to the zone

#pre-simulated file were generated with StROBe package (Stochastic Residential Occupancy Behavior) for Beatens (2015)
#the resultats are minute times based results, thus 525601 lines (not 525600 because 0 and 8760th hours of the year) !


def Schedule_Type(idf):
    #Schedule type creation to refer to for each associated zone's schedule
    #needs to be done ones for all
    idf.newidfobject(
        'SCHEDULETYPELIMITS',
        Name = 'Any Number'
        )
    return idf

def ScheduleCompact(idf, Name, SetPoint):
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
        Number_of_People_Schedule_Name = OccScheduleName,
        Number_of_People = NbPeople,
        Activity_Level_Schedule_Name = ActScheduleName,
        )
    return idf

def ZoneLoad(idf, zone, LoadSchedule, building, isfile, ZoningMultiplier):
    #floors_surf = [s for s in zone.zonesurfaces if s.Surface_Type in 'floor']
    #floor_area = floors_surf[0].area
    Multiplier = building.IntLoadMultiplier*ZoningMultiplier
    #the profil are considered as for 100m2. thus the designlevel is considering this
    #create the equipement tha will apply the load to the zone
    idf.newidfobject(
        'ELECTRICEQUIPMENT',
        Name = zone.Name+'Load',
        Zone_or_ZoneList_Name = zone.Name,
        Schedule_Name = LoadSchedule,
        Design_Level_Calculation_Method = 'Watts/Area',
        #Design_Level = floor_area/100 if isfile else building.IntLoad, #is a multiplier. this means that the file value will be the full zone's load in W
        Watts_per_Zone_Floor_Area = 1/100*Multiplier if isfile else building.IntLoad*Multiplier
        )
    return idf

def CreateThermostat(idf,name,setUp, setLo):
    #adding a Thermostat setting
    idf.newidfobject(
        "HVACTEMPLATE:THERMOSTAT",
        Name=name,
        Constant_Heating_Setpoint=setLo,
        Constant_Cooling_Setpoint=setUp,
        )
    return idf

def CreateThermostatFile(idf,name,namesetUp,namesetLo):
    #adding a Thermostat setting
    idf.newidfobject(
        "HVACTEMPLATE:THERMOSTAT",
        Name=name,
        Heating_Setpoint_Schedule_Name =namesetLo,
        Cooling_Setpoint_Schedule_Name =namesetUp,
        )
    return idf


def ZoneCtrl(idf,zone,building,PeopleDensity,ThermostatName, Multiplier,Correctdeff,FloorArea):
    #to all zones adding an ideal load element driven by the above thermostat
    #DCV stands for Demand Controlled Ventilation, the airflow is in m#/s/m2 thus divded by 1000 from DB_Data
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=zone.Name,
        Template_Thermostat_Name=ThermostatName,
        Heat_Recovery_Type='Sensible' if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 'None',
        Sensible_Heat_Recovery_Effectiveness= Correctdeff*building.AirRecovEff if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 0,
        Latent_Heat_Recovery_Effectiveness= 0,
        #Design_Specification_Outdoor_Air_Object_Name = AirNode,
        Outdoor_Air_Method='Sum' if PeopleDensity>0 and building.DemandControlledVentilation else 'Flow/Area',
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area=Multiplier*building.AreaBasedFlowRate/1000 + Multiplier*building.OccupBasedFlowRate/1000*PeopleDensity*(1-building.DemandControlledVentilation),
        Outdoor_Air_Flow_Rate_per_Person=building.OccupBasedFlowRate/1000,
        Demand_Controlled_Ventilation_Type = 'OccupancySchedule' if PeopleDensity>0 and building.DemandControlledVentilation else 'None',
        Heating_Limit = building.HVACLimitMode,
        Maximum_Sensible_Heating_Capacity =  FloorArea*Multiplier*building.HVACPowLimit,
        #Outdoor_Air_Inlet_Node_Name = 'OutdoorAirNode'
        )
    idf.newidfobject(
        "OUTDOORAIR:NODE",
        Name=zone.Name+' IDEAL LOADS OUTDOOR AIR INLET',  # quite weird but it seems to work....the name does not referer to the otherone,
    )
    return idf

def CreateEnvLeakage(idf, zone, building, ExtWallArea):

    # the envelope leake is modeled using a value from BBR standard in l/s/m2 at 50Pa
    # the flow coefficient model enable to deal with this by converting it equivalent cm2 at 4Pa
    # it also take into account the presence of stairwerlles (flue) that enhances leakage thourgh stack effect
    # enable to precise the flow exponent of 0,67 as well as a wind coeffient and shelter factor ( urban density)
    #coefficient given in the documentation
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
        Schedule_Name='AlwaysON',
        Flow_Coefficient= FlowCoef,
        Stack_Coefficient= StackCoefVal,
        Pressure_Exponent = PressureExp,
        Wind_Coefficient= WindCoefVal,
        Shelter_Factor = ShelterFactorVal,
    )
    return idf

def CreateBasementLeakage(idf, zone, ACH):
    idf.newidfobject(
        "ZONEINFILTRATION:DESIGNFLOWRATE",
        Name=zone.Name+'Leak',
        Zone_or_ZoneList_Name = zone.Name,
        Schedule_Name='AlwaysON',
        Design_Flow_Rate_Calculation_Method = 'AirChanges/Hour',
        Air_Changes_per_Hour = ACH,
    )
    return idf

def CreateInternalMass(idf,zone,FloorArea,name,Material):
    surf = 2*Material['WeightperZoneArea']*FloorArea/Material['Density']/Material['Thickness']
    if idf.idd_version[1] == 1:
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
        Schedule_Name=schedule,
        Design_Flow_Rate_Calculation_Method = 'AirChanges/Hour',
        Air_Changes_per_Hour = building.ACH_freecool,
        Ventilation_Type = 'Natural',
        Minimum_Indoor_Temperature = building.intT_freecool,
        Delta_Temperature = building.dT_freeCool
    )
    return idf

def getEfficiencyCor(OfficeTypeZone,ZoningMultiplier,building,PeopleDensity):
    #several assumptions are considered here : if there is two ventilation systems, it means that one if with heatrecovery and not the other one
    #it also mean that tha heat recoveray is applied to non residential type of areas.
    #the efficiency of the full zone is thus corrected by the ratio of airflows dedicated to non residential over the total for this floors
    #this correction factor will be applied to the efficiency of the heat recovery define with th HVAC system aand for wich value by default is given in the DB_Data file : AirRecovEff
    nbVentSyst = [idx for idx,key in enumerate(building.VentSyst) if building.VentSyst[key]]
    nbVentSystWithHR = [idx for idx, key in enumerate(building.VentSyst) if building.VentSyst[key]and key[-1] == 'X']
    if len(nbVentSyst)>1 and len(nbVentSystWithHR)==1:
        # we need to consider the over whole efficency if there is heat recoveray in the ventilation system and part of the floor it occupied by non residentials type.
        # we are conservative has only the minimun occupation rate is considered for the airflows
        OfficeAreaAirFlow = OfficeTypeZone * (
                    ZoningMultiplier * building.AreaBasedFlowRate / 1000) + ZoningMultiplier * building.OccupBasedFlowRate / 1000 * PeopleDensity
        TotalAreaAirFlow = ZoningMultiplier * building.AreaBasedFlowRate / 1000 + ZoningMultiplier * building.OccupBasedFlowRate / 1000 * PeopleDensity
        Correctdeff = OfficeAreaAirFlow / TotalAreaAirFlow
    else:
        Correctdeff = 1
    return Correctdeff


def CreateZoneLoadAndCtrl(idf,building,MainPath):
    # create the schedule type if not created before
    if not (idf.getobject('SCHEDULETYPELIMITS', 'Any Number')):
        Schedule_Type(idf)
    # create the Schedule with the input file for the Load (same for all zones) as function of zone area afterward
    #if the building.Intload is a path to a file, then the schedule file needs to be define, but if some constant value
    # is needed, then there is no need for this schedule and a constant unity schedule instead (let us use the leakcge schedule defined below)
    # the constant load will be dealed afterward in the ZoneLoad function with isfile variable
    try:
        os.path.isfile(building.IntLoad)
        create_ScheduleFile(idf, 'LoadSchedule', building.IntLoad)
        isfile = True
    except TypeError:
        isfile = False
    # we need a schedule for the infiltration rates in each zone. there will a unique one
    # the set point is 1 (multiplayer)
    ScheduleCompact(idf, 'AlwaysON', 1)
    # we need to define the occupancy activity level in order to avoid a warning and maybe later, compute the heat generated !
    # the set point is defined in DB_data
    ScheduleCompact(idf, 'OccupActivity', building.OccupHeatRate)
    #Create a single thermostat set points for all the zone (might need some other if different set points desired)
    CreateThermostat(idf,'ResidZone',building.setTempUpL, building.setTempLoL)
    # to all zones adding an ideal load element driven by the above thermostat

    #############################################################################################################
    ##this could be part of the building class
    ############################################################################################################
    OfficeOcc = 1 - building.OccupType['Residential'] #all occupancy but residential are taken for the extra airflow of 7l/s/pers
    # extra variable used below to compute the number of people to be considered in each zone
    PeopleDensity = [0, 0]
    if OfficeOcc != 0:
        for key in building.OccupType.keys():
            if not key in ['Residential']:
                PeopleDensity[0] += building.OccupType[key] / OfficeOcc * min(
                    building.OccupRate[key])  # this is the mean number of people per m2
                PeopleDensity[1] += building.OccupType[key] / OfficeOcc * max(building.OccupRate[key])
    #we need to spread this in all existing blocs based on tha area ratio
    BlocOfficeOcc = [] #if building.Multipolygon else OfficeOcc
    BlocHeatedArea = []
    BlocOfficechek = []
    BlocPeopleDensity = []
    for i,BlocArea in enumerate(building.BlocFootprintArea):
        BlocOfficeOcc.append(OfficeOcc) #because it is already a ratio, no need to add extra for floor areas  *BlocArea/sum(building.BlocFootprintArea))
        BlocHeatedArea.append(BlocArea*building.BlocNbFloor[i])
        BlocOfficechek.append(0) #it will be turned to 1 when finished to be considered depending on the occupancy rate
        BlocPeopleDensity.append(PeopleDensity)

    #############################################################################################################
    #let us go through all the zones but we need to sort them from the lowest ones to the highest one....to have different settings for the basement ones
    zoneStoreylist =[]
    bloclist = []
    AllZone = idf.idfobjects["ZONE"]
    for idx, zone in enumerate(AllZone):
        bloclist.append(int(zone.Name[zone.Name.rfind('Build')+5:zone.Name.find('Storey')]))
        zoneStoreylist.append(int(zone.Name[zone.Name.find('Storey')+6:])) #the name ends with Storey # so lets get the storey number this way
    SortedZoneIdx = sorted(range(len(zoneStoreylist)), key=lambda k: zoneStoreylist[k])
    for idx in SortedZoneIdx:
        zone = AllZone[idx]
        bloc = bloclist[idx]
        # we need to compute the enveloppe area facing outside as well as the floor area (for HVAC)
        ExtWallArea = 0
        for s in zone.zonesurfaces:
            if s.Outside_Boundary_Condition in 'outdoors':
                ExtWallArea += s.area
            if s.Surface_Type in 'floor':
                FloorArea = s.area
        #we need to create envelope infiltration for each zone facing outside and specific ones for the basement
        if zoneStoreylist[idx]<0: #means that we are in the basement
            # Lets modify the floor area depending on the zoning level
            FloorMultiplier = 1 if building.FloorZoningLevel else building.nbBasefloor
            FloorArea = FloorArea * FloorMultiplier

            CreateBasementLeakage(idf, zone, ACH=building.BasementAirLeak)
            #creating the internalMass element if the dict is not empty
            if building.InternalMass['NonHeatedZoneIntMass']:
                CreateInternalMass(idf, zone, FloorArea, 'NonHeatedZoneIntMassObj', building.InternalMass['NonHeatedZoneIntMass'])
        else:
            # Lets modify the floor area depending on the zoning level
            FloorMultiplier = 1 if building.FloorZoningLevel else building.BlocNbFloor[bloc]
            FloorArea = FloorArea * FloorMultiplier
            #creating the internalMass element if the dict is not empty
            if building.InternalMass['HeatedZoneIntMass']:
                CreateInternalMass(idf, zone, FloorArea, 'HeatedZoneIntMassObj', building.InternalMass['HeatedZoneIntMass'])
            if ExtWallArea != 0 and building.EnvLeak !=0 :
                CreateEnvLeakage(idf, zone, building, ExtWallArea)
            # check if Residential occupancy is not a 100% of the building, we shall take into account the ventilation for
            # office hours as well as heat generation from occupancy rates (defined in the DB_Data)
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
                if building.OffOccRandom:   #if random occupancy is wished (in DB_data)
                    #lets create a beta distribution random file for the number of ccupant
                    pathfile = os.path.join(MainPath,'InputFiles')
                    name = idf.idfname + '.txt' #building.name + 'nbUsers.txt'
                    #from now, random value are taken from 20 to 100% of the people density (the min value id DB_Data is not considered yet)
                    ProbGenerator.BuildData(name,pathfile,round(FloorArea*min(BlocPeopleDensity[bloc]),2),round(FloorArea*max(BlocPeopleDensity[bloc]),2), building)
                    # lets create a schedule file for occupant and the associated file
                    create_ScheduleFile(idf, 'OccuSchedule'+str(idx), pathfile+name)   #we should be careful because of varaition with multiproc
                    create_ScheduleFile(idf, 'OffTsetUp' + str(idx), pathfile+'SetPointUp.txt')
                    create_ScheduleFile(idf, 'OffTsetLo' + str(idx), pathfile+'SetPointLo.txt')
                    CreateThermostatFile(idf, 'OfficeZone'+ str(idx),'OffTsetUp' + str(idx),'OffTsetLo' + str(idx))
                else:
                    ## here is the scedule that define the number of occupant with fixed number of occupants (same all the time but still linked to shedule).
                    ScheduleCompactOccup(idf, 'OccuSchedule'+str(idx), building, SetPoint= round(FloorArea*max(BlocPeopleDensity[bloc]),2))
            # computation of the zonning level multiplier
            ZoningMultiplier = 1 if building.FloorZoningLevel else building.BlocNbFloor[bloc]
            # Internal load profile could be taken from the number of appartement. see building.IntLoad in DB_Building
            ZoneLoad(idf, zone,'LoadSchedule' if isfile else 'AlwaysON' ,building, isfile, ZoningMultiplier)
            # HVAC equipment for each zone including ventilation systems (exhaust, balanced with or not heat recovery)
            ThermostatType = 'OfficeZone'+ str(idx) if building.OffOccRandom and OfficeTypeZone>0 else 'ResidZone'#  if OfficeTypeZone==0 else
            #we need to catch some correction on the efficiency, see the function for more details
            CorrectdEff = getEfficiencyCor(OfficeTypeZone,ZoningMultiplier,building,min(BlocPeopleDensity[bloc]))
            #now the HVAC system is created for this zone
            ZoneCtrl(idf, zone, building, max(BlocPeopleDensity[bloc]),ThermostatType, ZoningMultiplier,CorrectdEff,FloorArea)
            #lets add freecooling to consider that peaopl just open windows when there're too hot !
            ZoneFreeCooling(idf,zone,building,'AlwaysON')

if __name__ == '__main__' :
    print('LoadAndOccupancy Main')