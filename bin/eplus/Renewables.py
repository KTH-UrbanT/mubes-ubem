import os.path
import math

import numpy as np
from shapely.geometry import Polygon
from pvlib.iotools import read_epw
from pvlib.location import Location
from pvlib.irradiance import get_total_irradiance
from shapely.geometry.polygon import Polygon


def Photovoltaic(idf, building, keyPath):
    PV_Gen_Names_List = []
    roof_surfaces = [s for s in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if s.Surface_Type.upper() == "ROOF"]
    model = getattr(building, 'PVPerformanceModel', 'Simple')
    if model == 'Simple':
        PV_Performance(idf)
        PV_perfnce_Name = idf.idfobjects["PHOTOVOLTAICPERFORMANCE:SIMPLE"][0].Name
        arrays = [(roof, 1, 10000) for roof in roof_surfaces]
    elif model == 'EquivalentOneDiode':
        settings = getattr(building, 'PVEquivalentOneDiode', {})
        arrays = SizeOneDiodeArrays(roof_surfaces, settings)
        if not arrays:
            return
        PV_EquivalentOneDiode_Performance(idf, settings)
        PV_perfnce_Name = idf.idfobjects["PHOTOVOLTAICPERFORMANCE:EQUIVALENTONE-DIODE"][0].Name
    else:
        raise ValueError('PVPerformanceModel must be Simple or EquivalentOneDiode, got ' + str(model))
    idf = Schedule4PV(idf, 'Always On PV')
    for idx, (roof, parallel_strings, rated_power) in enumerate(arrays):
        if model == 'Simple':
            idf, PV_Gen_Names = PV_Genrator(idf, idx, roof, PV_perfnce_Name)
        else:
            idf, PV_Gen_Names = PV_Generator_EquivalentOneDiode(
                idf, roof, PV_perfnce_Name, parallel_strings, settings['ModulesInSeries'])
        PV_Gen_Names_List.append(PV_Gen_Names)
    if model == 'Simple':
        idf, LoadCenterName = LoadCenter(idf, PV_Gen_Names_List)
    else:
        idf, LoadCenterName = LoadCenter_EquivalentOneDiode(
            idf, PV_Gen_Names_List, [array[2] for array in arrays])
    if model == 'Simple':
        idf, Inverter_Name = Inverter(idf)
        Distribution(idf, LoadCenterName, Inverter_Name)
    else:
        idf, Inverter_Name = Inverter_EquivalentOneDiode(idf, settings['InverterEfficiency'])
        Distribution_EquivalentOneDiode(idf, LoadCenterName, Inverter_Name)
    poa = Solar_Irradiance(building, keyPath)


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
        Fraction_of_Surface_Area_with_Active_Solar_Cells=0.6285,
        Conversion_Efficiency_Input_Mode="Fixed",  # case-insensitive
        Value_for_Cell_Efficiency_if_Fixed=0.16,
        Efficiency_Schedule_Name="",  # empty = no schedule
    )
    return idf


def SizeOneDiodeArrays(roof_surfaces, settings):
    coverage = settings['RoofCoverageFraction']
    module_area = settings['ModuleArea']
    active_area = settings['ActiveArea']
    modules_in_series = settings['ModulesInSeries']
    if not 0 < coverage <= 1:
        raise ValueError('PVEquivalentOneDiode.RoofCoverageFraction must be in (0, 1]')
    if module_area <= 0 or not 0 < active_area <= module_area:
        raise ValueError('PVEquivalentOneDiode requires 0 < ActiveArea <= ModuleArea')
    if not isinstance(modules_in_series, int) or modules_in_series < 1:
        raise ValueError('PVEquivalentOneDiode.ModulesInSeries must be a positive integer')
    if not 0 < settings['ModuleCurrentAtMaximumPower'] < settings['ShortCircuitCurrent']:
        raise ValueError('PVEquivalentOneDiode requires 0 < Imp < Isc')
    if not 0 < settings['ModuleVoltageAtMaximumPower'] < settings['OpenCircuitVoltage']:
        raise ValueError('PVEquivalentOneDiode requires 0 < Vmp < Voc')
    if not 0 < settings['InverterEfficiency'] <= 1:
        raise ValueError('PVEquivalentOneDiode.InverterEfficiency must be in (0, 1]')

    arrays = []
    for roof in roof_surfaces:
        parallel_strings = math.floor(roof.area * coverage / (module_area * modules_in_series))
        if parallel_strings < 1:
            continue
        rated_power = (parallel_strings * modules_in_series *
                       settings['ModuleCurrentAtMaximumPower'] * settings['ModuleVoltageAtMaximumPower'])
        arrays.append((roof, parallel_strings, rated_power))
    return arrays


def PV_EquivalentOneDiode_Performance(idf, settings):
    idf.newidfobject(
        'PHOTOVOLTAICPERFORMANCE:EQUIVALENTONE-DIODE',
        Name='Equivalent One-Diode PV',
        Cell_type=settings['CellType'],
        Number_of_Cells_in_Series=settings['NumberOfCellsInSeries'],
        Active_Area=settings['ActiveArea'],
        Transmittance_Absorptance_Product=settings['TransmittanceAbsorptanceProduct'],
        Semiconductor_Bandgap=settings['SemiconductorBandgap'],
        Shunt_Resistance=settings['ShuntResistance'],
        Short_Circuit_Current=settings['ShortCircuitCurrent'],
        Open_Circuit_Voltage=settings['OpenCircuitVoltage'],
        Reference_Temperature=settings['ReferenceTemperature'],
        Reference_Insolation=settings['ReferenceInsolation'],
        Module_Current_at_Maximum_Power=settings['ModuleCurrentAtMaximumPower'],
        Module_Voltage_at_Maximum_Power=settings['ModuleVoltageAtMaximumPower'],
        Temperature_Coefficient_of_Short_Circuit_Current=settings['TemperatureCoefficientOfShortCircuitCurrent'],
        Temperature_Coefficient_of_Open_Circuit_Voltage=settings['TemperatureCoefficientOfOpenCircuitVoltage'],
        Nominal_Operating_Cell_Temperature_Test_Ambient_Temperature=settings['NOCTAmbientTemperature'],
        Nominal_Operating_Cell_Temperature_Test_Cell_Temperature=settings['NOCTCellTemperature'],
        Nominal_Operating_Cell_Temperature_Test_Insolation=settings['NOCTInsolation'],
        Module_Heat_Loss_Coefficient=settings['ModuleHeatLossCoefficient'],
        Total_Heat_Capacity=settings['TotalHeatCapacity'],
    )
    return idf


def PV_Generator_EquivalentOneDiode(idf, roof, performance_name, parallel_strings, modules_in_series):
    generator = idf.newidfobject(
        'GENERATOR:PHOTOVOLTAIC',
        Name='PV_On_' + roof.Name,
        Surface_Name=roof.Name,
        Photovoltaic_Performance_Object_Type='PhotovoltaicPerformance:EquivalentOne-Diode',
        Module_Performance_Name=performance_name,
        Heat_Transfer_Integration_Mode='Decoupled',
        Number_of_Series_Strings_in_Parallel=parallel_strings,
        Number_of_Modules_in_Series=modules_in_series,
    )
    return idf, generator.Name


def LoadCenter_EquivalentOneDiode(idf, generator_names, rated_powers):
    load_center = idf.newidfobject('ELECTRICLOADCENTER:GENERATORS', Name='PV_Generators_FlatRoofs')
    for index, (name, rated_power) in enumerate(zip(generator_names, rated_powers), start=1):
        setattr(load_center, f'Generator_{index}_Name', name)
        setattr(load_center, f'Generator_{index}_Object_Type', 'Generator:Photovoltaic')
        setattr(load_center, f'Generator_{index}_Rated_Electric_Power_Output', rated_power)
    return idf, load_center.Name


def Inverter_EquivalentOneDiode(idf, efficiency):
    inverter = idf.newidfobject(
        'ELECTRICLOADCENTER:INVERTER:SIMPLE',
        Name='PV_Inverter',
        Availability_Schedule_Name='Always On PV',
        Zone_Name='',
        Radiative_Fraction=0.0,
        Inverter_Efficiency=efficiency,
    )
    return idf, inverter.Name


def Distribution_EquivalentOneDiode(idf, load_center_name, inverter_name):
    idf.newidfobject(
        'ELECTRICLOADCENTER:DISTRIBUTION',
        Name='PV_Distribution',
        Generator_List_Name=load_center_name,
        Generator_Operation_Scheme_Type='Baseload',
        Electrical_Buss_Type='DirectCurrentWithInverter',
        Inverter_Name=inverter_name,
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
        # setattr(idf.idfobjects["ELECTRICLOADCENTER:GENERATORS"][0], f"Generator_{i}_Availability_Schedule_Name", "Always On PV")

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
        Nominal_Efficiency=0.90,
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
        Electrical_Bus_Type="DirectCurrentWithInverter",
        Inverter_Name=Inverter_Name,
        Electrical_Storage_Object_Name="",
        Transformer_Object_Name="",
    )
    return idf


def Solar_Irradiance(building, keypath):
    Weather_path = os.path.join(keypath['epluspath'], building.WeatherDataFile)
    weather, meta = read_epw(Weather_path)
    poa = []
    wh = []
    site = Location(
        latitude=meta["latitude"],
        longitude=meta["longitude"],
        altitude=meta["altitude"],
        tz=meta["TZ"]
    )

    times = weather.index
    # Solar position
    solar_pos = site.get_solarposition(times)
    # IRRADIANCE FROM EPW
    dni = weather["dni"]
    ghi = weather["ghi"]
    dhi = weather["dhi"]
    tilt = 0
    azimuths = [azimuth_from_polygon_coords(p) for p in building.footprint]

    for azimuth in azimuths:
        # computes how much solar radiation actually hits your roof surface (Plane-Of-Array irradiance)
        poa.append(get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            dni=dni,
            ghi=ghi,
            dhi=dhi,
            solar_zenith=solar_pos["zenith"],
            solar_azimuth=solar_pos["azimuth"]
        ))
    for k in poa:
        wh.append(k["poa_global"].sum())
    return wh


def azimuth_from_polygon_coords(coords):
    """
    coords: list of (x, y) tuples for one polygon ring
    returns: azimuth degrees from North, clockwise (0..360)
    """
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)  # fixes many self-intersections

    mrr = poly.minimum_rotated_rectangle
    pts = list(mrr.exterior.coords)

    # 4 rectangle edges (ignore last repeated point)
    edges = [(pts[i], pts[i+1]) for i in range(4)]

    longest = max(edges, key=length)
    (x1, y1), (x2, y2) = longest

    # azimuth: 0°=North, clockwise
    az = (np.degrees(np.arctan2(x2 - x1, y2 - y1)) + 360) % 360
    return az

def length(e):
    (x1, y1), (x2, y2) = e
    return np.hypot(x2 - x1, y2 - y1)





