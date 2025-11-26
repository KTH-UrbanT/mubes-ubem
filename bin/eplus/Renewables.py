
def Photovoltaic(idf, building):
    PV_Gen_Names_List = []
    roof_surfaces = [s for s in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if s.Surface_Type.upper() == "ROOF"]
    PV_Performance(idf)
    PV_perfnce_Name = idf.idfobjects["PHOTOVOLTAICPERFORMANCE:SIMPLE"][0].Name
    idf = Schedule4PV(idf, 'Always On PV')
    for idx, roof in enumerate(roof_surfaces):
        idf, PV_Gen_Names = PV_Genrator(idf, idx, roof, PV_perfnce_Name)
        PV_Gen_Names_List.append(PV_Gen_Names)
    idf, LoadCenterName = LoadCenter(idf, PV_Gen_Names_List)
    idf, Inverter_Name = Inverter(idf)
    Distribution(idf, LoadCenterName, Inverter_Name)


def Schedule4PV(idf, Name):
    idf.newidfobject(
        "SCHEDULE:COMPACT",
        Name=Name,
        Schedule_Type_Limits_Name='Any Number',
        Field_1='Through: 12/31',
        Field_2='For: AllDays',
        Field_3='Until: 24:00',
        Field_4='1.0',      # always on
    )
    return idf

def PV_Performance(idf):
    idf.newidfobject(
        "PHOTOVOLTAICPERFORMANCE:SIMPLE",
        Name="Simple PV Flat",
        Fraction_of_Surface_Area_with_Active_Solar_Cells=0.2044,
        Conversion_Efficiency_Input_Mode="Fixed",  # case-insensitive
        Value_for_Cell_Efficiency_if_Fixed=0.12,
        Efficiency_Schedule_Name="",  # empty = no schedule
    )
    return idf

def PV_Genrator(idf, idx, roof, PV_perfnce_Name):
    idf.newidfobject(
        "GENERATOR:PHOTOVOLTAIC",
        Name="PV_On_" + roof.Name,
        Surface_Name=roof.Name,
        Photovoltaic_Performance_Object_Type="PhotovoltaicPerformance:Simple",
        Module_Performance_Name=PV_perfnce_Name,
        Heat_Transfer_Integration_Mode="Decoupled",
        Number_of_Series_Strings_in_Parallel=1,
        Number_of_Modules_in_Series=1,
    )
    return idf, idf.idfobjects["GENERATOR:PHOTOVOLTAIC"][idx].Name


def LoadCenter(idf, PV_Gen_Names):
    idf.newidfobject(
        "ELECTRICLOADCENTER:GENERATORS",
        Name="PV_Generators_FlatRoofs",
    )

    for i, gen in enumerate(PV_Gen_Names, start=1):
        setattr(idf.idfobjects["ELECTRICLOADCENTER:GENERATORS"][0], f"Generator_{i}_Name", gen)
        setattr(idf.idfobjects["ELECTRICLOADCENTER:GENERATORS"][0], f"Generator_{i}_Object_Type", "Generator:Photovoltaic")
        setattr(idf.idfobjects["ELECTRICLOADCENTER:GENERATORS"][0], f"Generator_{i}_Rated_Electric_Power_Output", 10000)  # W, rough peak
        setattr(idf.idfobjects["ELECTRICLOADCENTER:GENERATORS"][0], f"Generator_{i}_Availability_Schedule_Name", "Always On PV")

    return idf, idf.idfobjects["ELECTRICLOADCENTER:GENERATORS"][0].Name


def Inverter(idf):
    idf.newidfobject(
        "ELECTRICLOADCENTER:INVERTER:SIMPLE",
        Name="PV_Inverter",
        Availability_Schedule_Name="Always On PV",
        Zone_Name="",  # no thermal coupling
        Radiative_Fraction=0.0,
        Rated_Maximum_Output_Power=0,  # 0 often means "big enough"; check EP docs if you want explicit
        Night_Tare_Loss_Power=0.0,
        Nominal_Efficiency=0.96,
    )
    return idf, idf.idfobjects["ELECTRICLOADCENTER:INVERTER:SIMPLE"][0].Name


def Distribution(idf, LoadCenterName, Inverter_Name):
    idf.newidfobject(
        "ELECTRICLOADCENTER:DISTRIBUTION",
        Name="PV_Distribution",
        Generator_List_Name=LoadCenterName,
        Generator_Operation_Scheme_Type="Baseload",
        Demand_Limit_Scheme_Purchased_Electric_Demand_Limit=0.0,
        Track_Schedule_Name="",
        Generator_Track_Follow_Schedule_Name="",
        Electrical_Bus_Type="AlternatingCurrent",
        Inverter_Name=Inverter_Name,
        Electrical_Storage_Object_Name="",
        Transformer_Object_Name="",
    )
    return idf
