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
    #now lets create the water equipment object
    idf.newidfobject(
        'WATERUSE:EQUIPMENT',
        Name = building.DHWInfos['Name'],
        Peak_Flow_Rate = building.nbAppartments*building.DHWInfos['WaterTapsMultiplier'],#the flow rate should be in m3/s and we are using schedul file in l/min, thus we need this transformation,
        Flow_Rate_Fraction_Schedule_Name = 'WaterTaps',
        Hot_Water_Supply_Temperature_Schedule_Name = 'HotWaterTemp',
        Cold_Water_Supply_Temperature_Schedule_Name='ColdWaterTemp',
        )
    return idf

