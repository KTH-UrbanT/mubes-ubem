# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import CoreFiles.Load_and_occupancy as Load_and_occupancy

def createWaterEqpt(idf,Element):
    if not (idf.getobject('SCHEDULETYPELIMITS', 'Any Number')):
        Load_and_occupancy.Schedule_Type(idf)
    #lets first create the schedul filesfor the water taps and the hot water (even if constant)
    Load_and_occupancy.create_ScheduleFile(idf, 'Watertaps', Element['WatertapsFile'])
    Load_and_occupancy.create_ScheduleFile(idf, 'ColdWaterTemp', Element['ColdWaterTempFile'])
    Load_and_occupancy.ScheduleCompact(idf, 'HotWaterTemp', Element['HotWaterSetTemp'])
    #now lets create the water equipment object
    idf.newidfobject(
        'WATERUSE:EQUIPMENT',
        Name = Element['Name'],
        Peak_Flow_Rate = 6e-4,#the flow rate should be in m3/s and we are using schedul file in l/min, thus we need this transformation,
        Flow_Rate_Fraction_Schedule_Name = 'WaterTaps',
        Hot_Water_Supply_Temperature_Schedule_Name = 'HotWaterTemp',
        Cold_Water_Supply_Temperature_Schedule_Name='ColdWaterTemp',
        )
    return idf

