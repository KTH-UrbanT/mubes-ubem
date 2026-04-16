# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import eplus.Load_and_occupancy as Load_and_occupancy
import os

def createWaterEqpt(idf,building):
    if not (idf.getobject('SCHEDULETYPELIMITS', 'Any Number')):
        Load_and_occupancy.Schedule_Type(idf)
    #lets first create the schedule files for the water taps and the hot water (even if constant)
    Load_and_occupancy.create_ScheduleFile(idf, 'Watertaps', building.DHWInfos['WatertapsFile'])
    Load_and_occupancy.create_ScheduleFile(idf, 'ColdWaterTemp', building.DHWInfos['ColdWaterTempFile'])
    Load_and_occupancy.ScheduleCompact(idf, 'HotWaterTemp', building.DHWInfos['HotWaterSetTemp'])
    Load_and_occupancy.ScheduleCompact(idf, 'TargetWaterTemp', building.DHWInfos['TargetWaterTapTemp'])
    #now lets create the water equipment object
    try: multiplier = eval(building.DHWInfos['WaterTapsMultiplier'])
    except: multiplier = building.DHWInfos['WaterTapsMultiplier']
    idf.newidfobject(
        'WATERUSE:EQUIPMENT',
        Name = building.DHWInfos['Name'],
        Peak_Flow_Rate = building.nbAppartments*multiplier*CallCorrectionFactor(building),
        Flow_Rate_Fraction_Schedule_Name = 'WaterTaps',
        Target_Temperature_Schedule_Name='TargetWaterTemp',
        Hot_Water_Supply_Temperature_Schedule_Name = 'HotWaterTemp',
        Cold_Water_Supply_Temperature_Schedule_Name='ColdWaterTemp',
        )
    return idf

def CallCorrectionFactor(building):
    try:
        Cp = 4200 #J/Kg/K water specific heat
        Waterdensity = 1000 #kg/m3
        try: multiplier = eval(building.DHWInfos['WaterTapsMultiplier'])
        except: multiplier = building.DHWInfos['WaterTapsMultiplier']
        #lets comput the cumulative value and make it match with thr EPC data of DHW consumption
        watertaps, waterList = getVal(building.DHWInfos['WatertapsFile'])
        coldTemp, coldTempList = getVal(building.DHWInfos['ColdWaterTempFile'])
        targetTemp, TargetTempList = getVal(building.DHWInfos['TargetWaterTapTemp'])
        DHWfromEPC = getDHW_EPC(building.EPCMeters['DHW'])
        targetTemp = [targetTemp]*len(watertaps)
        #from now we know that water taps and cold temp are from file, so in the futur there should be some check to make the floowing operation !
        TotalDHW = sum([val * Waterdensity * building.nbAppartments * multiplier * Cp * (targetTemp[idx]-coldTemp[idx]) for idx,val in enumerate(watertaps)])
        return DHWfromEPC/TotalDHW
    except:
        return 1

def getVal(var):
    if os.path.isfile(var):
        with open(var, 'r') as f:
            Lines = f.readlines()
        return [float(val) for val in Lines], True
    else:
        return float(var), False

def getDHW_EPC(DHW_Meas):
    TotDHW = 0
    for key in DHW_Meas.keys():
        TotDHW += DHW_Meas[key]
    return TotDHW

def CallCorrectionFactorMade4Calib(building):
    BuildName = building.name
    #all this below was done for the calibration study using the calibrated values to make Strobe package comply with measurements
    #cf paper on the calibration study
    BuildNumber = int(BuildName[BuildName.index('_')+1:BuildName.index('v')])
    # Lets read the correction factors
    import os
    pth2corfactors  = os.path.normcase('C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration\\')
    CorFactPath = os.path.normcase(os.path.join(pth2corfactors, 'DHWCorFact.txt'))
    with open(CorFactPath, 'r') as handle:
        FileLines = handle.readlines()
    CorFact = {}
    for line in FileLines:
        CorFact[int(line[:line.index('\t')])] = float(line[line.index('\t')+1:line.index('\n')])

    # #the following lines are added to apply an extra correction factor for year 2014 and 2015 compared to 2012
    CorFactPath = os.path.normcase(os.path.join(pth2corfactors, 'DHWCorFact2014.txt'))
    with open(CorFactPath, 'r') as handle:
        FileLines = handle.readlines()
    ExtraCorFact = {}
    for line in FileLines:
        ExtraCorFact[int(line[:line.index('\t')])] = float(line[line.index('\t') + 1:line.index('\n')])

    return CorFact[BuildNumber] #* ExtraCorFact[BuildNumber]