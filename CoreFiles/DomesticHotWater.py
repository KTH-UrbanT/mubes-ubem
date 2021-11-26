# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import CoreFiles.Load_and_occupancy as Load_and_occupancy

def createWaterEqpt(idf,building):
    if not (idf.getobject('SCHEDULETYPELIMITS', 'Any Number')):
        Load_and_occupancy.Schedule_Type(idf)
    #lets first create the schedule files for the water taps and the hot water (even if constant)
    Load_and_occupancy.create_ScheduleFile(idf, 'Watertaps', building.DHWInfos['WatertapsFile'])
    Load_and_occupancy.create_ScheduleFile(idf, 'ColdWaterTemp', building.DHWInfos['ColdWaterTempFile'])
    Load_and_occupancy.ScheduleCompact(idf, 'HotWaterTemp', building.DHWInfos['HotWaterSetTemp'])
    Load_and_occupancy.ScheduleCompact(idf, 'TargetWaterTemp', building.DHWInfos['TargetWaterTapTemp'])
    #now lets create the water equipment object
    idf.newidfobject(
        'WATERUSE:EQUIPMENT',
        Name = building.DHWInfos['Name'],
        Peak_Flow_Rate = building.nbAppartments*building.DHWInfos['WaterTapsMultiplier']*CallCorrectionFactor(building.name),#the flow rate should be in m3/s and we are using schedul file in l/min, thus we need this transformation,
        Flow_Rate_Fraction_Schedule_Name = 'WaterTaps',
        Target_Temperature_Schedule_Name='TargetWaterTemp',
        Hot_Water_Supply_Temperature_Schedule_Name = 'HotWaterTemp',
        Cold_Water_Supply_Temperature_Schedule_Name='ColdWaterTemp',
        )
    return idf

def CallCorrectionFactor(BuildName):
    return 1
    #all this below was done for the calibration study using the calibrated values to make Strobe package comply with measurements
    #cf paper on the calibration study
    # BuildNumber = int(BuildName[BuildName.index('_')+1:BuildName.index('v')])
    # # Lets read the correction factors
    # import os
    # pth2corfactors  = os.path.normcase('C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_SimResults\\ComputedElem4Calibration\\')
    # CorFactPath = os.path.normcase(os.path.join(pth2corfactors, 'DHWCorFact.txt'))
    # with open(CorFactPath, 'r') as handle:
    #     FileLines = handle.readlines()
    # CorFact = {}
    # for line in FileLines:
    #     CorFact[int(line[:line.index('\t')])] = float(line[line.index('\t')+1:line.index('\n')])
    # return CorFact[BuildNumber]