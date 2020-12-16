
def setSimparam(idf):
    #changing the running period
    simctrl = idf.idfobjects['SIMULATIONCONTROL'][0]
    simctrl.Run_Simulation_for_Sizing_Periods= 'No'
    simctrl.Run_Simulation_for_Weather_File_Run_Periods = 'Yes'
    #chqnging the Solar calculation because of complex surface (non convexe)
    build_param = idf.idfobjects['BUILDING'][0]
    build_param.Solar_Distribution = 'FullExteriorWithReflections' #'FullExterior' #'MinimalShadowing' # FullExterior is the most detailed option possible in our case.
    #it computes exteriori shading bu not internal. all the radiation that enters the zones is allocated to the floor
    # https://bigladdersoftware.com/epx/docs/9-1/engineering-reference/shading-module.html#solar-distribution

    runperiod = idf.idfobjects['RUNPERIOD'][0]
    runperiod.Begin_Day_of_Month = 1
    runperiod.Begin_Month = 1
    runperiod.End_Day_of_Month = 31
    runperiod.End_Month = 12


    timestepobj = idf.idfobjects['TIMESTEP'][0]
    timestepobj.Number_of_Timesteps_per_Hour = 4
    return idf

def Location_and_weather(idf):
    #Weather_file = "USA_CO_Golden-NREL.724666_TMY3.epw"
    Weather_file = "SWE_Stockholm.Arlanda.024600_IWEC"
    idf.epw = Weather_file+'.epw'
    location = idf.idfobjects['SITE:LOCATION'][0]   #there might be some way of taking the information from the weather file directly in the idf object...
    location.Name = Weather_file
    location.Latitude = 59.65
    location.Longitude = 17.95
    location.Time_Zone = +1
    location.Elevation = 61
    ground_Temp = idf.newidfobject('SITE:GROUNDTEMPERATURE:BUILDINGSURFACE')
    ground_Temp.January_Ground_Temperature = 15
    ground_Temp.February_Ground_Temperature = 15
    ground_Temp.March_Ground_Temperature = 15
    ground_Temp.April_Ground_Temperature = 15
    ground_Temp.May_Ground_Temperature = 15
    ground_Temp.June_Ground_Temperature = 15
    ground_Temp.August_Ground_Temperature = 15
    ground_Temp.September_Ground_Temperature = 15
    ground_Temp.October_Ground_Temperature = 15
    ground_Temp.November_Ground_Temperature = 15
    ground_Temp.December_Ground_Temperature = 15
    return idf
