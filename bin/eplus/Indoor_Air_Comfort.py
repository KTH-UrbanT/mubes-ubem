# @Author  : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

def ZoneAirContaminantBalance(idf, Outdoor_CO2_Schedule, Generic_Contaminant_Schedule):
    idf.newidfobject(
        "ZONEAIRCONTAMINANTBALANCE",
        Carbon_Dioxide_Concentration = 'Yes',
        Outdoor_Carbon_Dioxide_Schedule_Name = Outdoor_CO2_Schedule,
        Generic_Contaminant_Concentration = 'Yes',
        Outdoor_Generic_Contaminant_Schedule_Name = Generic_Contaminant_Schedule
    )
    return idf

def ScheduleCompact_cloth(idf, Name):
    idf.newidfobject(
        "SCHEDULE:COMPACT",
        Name=Name,
        Schedule_Type_Limits_Name="Any Number",
        Field_1="Through: 05/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00, 2",
        Field_4="Through: 09/30",
        Field_5="For: AllDays",
        Field_6="Until: 24:00, 2",
        Field_7="Through: 12/31",
        Field_8="For: AllDays",
        Field_9="Until: 24:00, 2;"
    )
    return idf

def ScheduleCompact_WorkEfficiency(idf, Name, SetPoint):
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


def ScheduleCompact_Airvelocity(idf, Name, SetPoint):
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


def ScheduleCompact_CO2(idf, Name, SetPoint):
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

def ScheduleCompact_Contaminant(idf, Name, SetPoint):
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