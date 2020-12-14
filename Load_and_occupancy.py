import ProbGenerator
import os
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
        Field_3='Until: '+building.Officehours[0],
        Field_4=0,
        Field_5='Until: '+building.Officehours[1],
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

# def CreateVentFlowRate(idf,Name, ScheduleName, building):
#     idf.newidfobject(
#         'DESIGNSPECIFICATION:OUTDOORAIR',
#         Name=Name,
#         Outdoor_Air_Method='Sum',
#         Outdoor_Air_Flow_per_Person=building.AreaBasedFlowRate,
#         Outdoor_Air_Flow_per_Zone_Floor_Area=building.OccupBasedFlowRate,
#         Outdoor_Air_Flow_per_Zone=0,
#         Outdoor_Air_Schedule_Name = ScheduleName,
#     )


def ZoneLoad(idf, zone, LoadSchedule):

    floors_surf = [s for s in zone.zonesurfaces if s.Surface_Type in 'floor']
    floor_area = floors_surf[0].area
    #the profil are considered as for 100m2. thus the designlevel is considering this
    #create the equipement tha will apply the load to the zone
    idf.newidfobject(
        'ELECTRICEQUIPMENT',
        Name = zone.Name+'Load',
        Zone_or_ZoneList_Name = zone.Name,
        Schedule_Name = LoadSchedule,
        Design_Level = floor_area/100, #is a multiplier. this means that the file value will be the full zone's load in W
        )
    return idf

def CreateThermostat(idf,name):
    #adding a Thermostat setting
    idf.newidfobject(
        "HVACTEMPLATE:THERMOSTAT",
        Name=name,
        Constant_Heating_Setpoint=20,
        Constant_Cooling_Setpoint=25,
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

def ZoneCtrl(idf,zone,building,PeopleDensity,ThermostatName):
    #to all zones adding an ideal load element driven by the above thermostat
    #DCV stands for Demand Controlled Ventilation
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=zone.Name,
        Template_Thermostat_Name=ThermostatName,
        Heat_Recovery_Type='Sensible' if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 'None',
        Sensible_Heat_Recovery_Effectiveness= 0.7 if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 0,
        #Design_Specification_Outdoor_Air_Object_Name = AirNode,
        Outdoor_Air_Method='Sum' if PeopleDensity>0 and building.DCV else 'Flow/Area',
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area=building.AreaBasedFlowRate + building.OccupBasedFlowRate*PeopleDensity*(1-building.DCV),
        Outdoor_Air_Flow_Rate_per_Person=building.OccupBasedFlowRate,
        Demand_Controlled_Ventilation_Type = 'OccupancySchedule' if PeopleDensity>0 and building.DCV else 'None',
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
        Schedule_Name='EnvLeakage',
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
        Schedule_Name='EnvLeakage',
        Design_Flow_Rate_Calculation_Method = 'AirChanges/Hour',
        Air_Changes_per_Hour = ACH,
    )
    return idf



def CreateZoneLoadAndCtrl(idf,building):
    # create the schedule type if not created before
    if not (idf.getobject('SCHEDULETYPELIMITS', 'Any Number')):
        Schedule_Type(idf)
    # create the Schedule with the input file for the Load (same for all zones(as function of zone area afterard
    create_ScheduleFile(idf, 'LoadSchedule', building.IntLoad)
    # we need a schedule for the infiltration rates in each zone. there will a unique one
    ScheduleCompact(idf, 'EnvLeakage', 1)
    # we need to define the occupancy activity level in order to avoid a warning and maybe leter, compute the heat generated !
    ScheduleCompact(idf, 'OccupActivity', 70)
    # # we need to creat the outoddr air node for ventilation definition
    # CreateVentFlowRate(idf, 'VentFlowNode', 'Occupancy', building)
    #Create a unique thermostat set points for all the zone (might need some other if different ste points desired)
    CreateThermostat(idf,'ResidZone')
    # to all zones adding an ideal load element driven by the above thermostat
    #we need a flag the cjheck if Office occupancy has been analysed or not
    Officechek = 0 #it will be turned to 1 when finished to be considered depensing on the occupancy rate
    OfficeOcc = 1 - building.OccupType['Residential'] #all occupancy but residential are taken for the extra airflow of 7l/s/pers
    #we need to compute how many people are concerned by other acctivities than Residential
    PeopleDensity = 0
    FloorSumArea = 0
    if OfficeOcc != 0:
        for key in building.OccupType.keys():
            if not key in ['Residential']:
                PeopleDensity += building.OccupType[key] / OfficeOcc * building.OccupRate[key] #this is the mean number of people per m2

    #lest go through all the zones but we need to sort them from the lowest ones to the highest one....
    zonelist =[]
    for idx, zone in enumerate(idf.idfobjects["ZONE"]):
        storey = int(zone.Name[zone.Name.find('Storey')+6:]) #the name ends with Storey # so lest get the storey number this way
        zonelist.append(storey)
    SortedZoneOrder = sorted(range(len(zonelist)), key=lambda k: zonelist[k])
    AllZone = idf.idfobjects["ZONE"]
    for idx in SortedZoneOrder:
        zone = AllZone[idx]
        #we need to create envelope infiltration for each zone facing outside
        #we need to compute the enveloppe area facing outside as well as the floor area (for HVAC)
        ExtWallArea = 0
        FloorArea = 0
        if zonelist[idx]<0: #means that we are in the basement
            CreateBasementLeakage(idf, zone, ACH=0.1)
        else:
            for s in zone.zonesurfaces:
                if s.Outside_Boundary_Condition in 'outdoors': # or s.Outside_Boundary_Condition in 'ground':# for basement we need another model....like the deignflowrate
                    ExtWallArea += s.area
                if s.Surface_Type in 'floor':
                    FloorArea  = s.area
                    FloorSumArea += FloorArea
            if ExtWallArea != 0 and building.EnvLeak !=0 :
                CreateEnvLeakage(idf, zone, building, ExtWallArea)
            # check if Residential occupancy is not a 100% of the building, we shall take into account the ventilation for
            # office hours as well as heat generation from occupancy rates (defined in the DB_Data)
            OfficeTypeZone = min(1, OfficeOcc / (FloorSumArea/building.EPHeatedArea)) if Officechek == 0 else 0
            Officechek = 1 if OfficeTypeZone < 1 else 0
            # We need to define the number of occupant in each zone for heat release and HVAC extra airflow rate
            PeopleDensity = PeopleDensity*OfficeTypeZone
            if OfficeTypeZone>0:
                # for each zone : one occupant and the number is defined through a schedule
                create_Occupant(idf, zone, 'OccuSchedule'+str(idx), 'OccupActivity', 1)
                if building.OffOccRandom:
                    #lets create a beta distribution random file for the number of ccupant
                    pathname = os.path.dirname(os.getcwd()) + '\\InputFiles\\nbUsers.txt'
                    ProbGenerator.BuildData('nbUsers.txt',round(FloorArea*PeopleDensity)/20,round(FloorArea*PeopleDensity))
                    # lets create a schedule file for occupant and the associated file
                    create_ScheduleFile(idf, 'OccuSchedule'+str(idx), pathname)
                    pathname = os.path.dirname(os.getcwd()) + '\\InputFiles\\SetPointUp.txt'
                    create_ScheduleFile(idf, 'OffTsetUp' + str(idx), pathname)
                    pathname = os.path.dirname(os.getcwd()) + '\\InputFiles\\SetPointLo.txt'
                    create_ScheduleFile(idf, 'OffTsetLo' + str(idx), pathname)
                    CreateThermostatFile(idf, 'OfficeZone'+ str(idx),'OffTsetUp' + str(idx),'OffTsetLo' + str(idx))
                else:
                    ## here is the scedule that define the number of occupant with fixed number of occupants (same all the time but sitlll linked to shedule).
                    ScheduleCompactOccup(idf, 'OccuSchedule'+str(idx), building, SetPoint=round(FloorArea*PeopleDensity))
                    OfficeTypeZone = 0
            # Internal load profil taken from the number of appartement. see building.IntLoad in DB_Building
            ZoneLoad(idf, zone, 'LoadSchedule')
            # HVAC equipment for each zone including ventilation systems (exhaust, balanced with or not heat recovery)
            ThermostatType = 'ResidZone'  if OfficeTypeZone==0 else 'OfficeZone'+ str(idx)
            ZoneCtrl(idf, zone, building, PeopleDensity,ThermostatType)