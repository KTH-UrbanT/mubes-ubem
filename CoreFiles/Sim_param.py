# @Author  : Xavier Faure
# @Email   : xavierf@kth.se


def setSimparam(idf,building):
    #changing the running period
    simctrl = idf.idfobjects['SIMULATIONCONTROL'][0]
    simctrl.Run_Simulation_for_Sizing_Periods= 'No'
    simctrl.Run_Simulation_for_Weather_File_Run_Periods = 'Yes'
    #chqnging the Solar calculation because of complex surface (non convexe)
    build_param = idf.idfobjects['BUILDING'][0]
    build_param.Solar_Distribution = 'FullExterior' #'FullExteriorWithReflections' #'FullExterior' #'MinimalShadowing' # FullExterior is the most detailed option possible in our case.
    #it computes exteriori shading bu not internal. all the radiation that enters the zones is allocated to the floor
    # https://bigladdersoftware.com/epx/docs/9-1/engineering-reference/shading-module.html#solar-distribution
    #the one with reflection might not be needed and takes more cumputational time (it worth it for specific radiation propreties of the surroundings surfaces
    #but these are tekan from default value from now

    runperiod = idf.idfobjects['RUNPERIOD'][0]
    runperiod.Begin_Day_of_Month = building.Begin_Day_of_Month
    runperiod.Begin_Month = building.Begin_Month
    runperiod.End_Day_of_Month = building.End_Day_of_Month
    runperiod.End_Month = building.End_Month
    #set the heat algorithm
    idf.newidfobject(
        'HEATBALANCEALGORITHM',
        Algorithm = 'ConductionTransferFunction',#'ConductionFiniteDifference', #
    )
    #time step
    timestepobj = idf.idfobjects['TIMESTEP'][0]
    timestepobj.Number_of_Timesteps_per_Hour = 4

    # idf.newidfobject(
    #     'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME',
    #     Start_Date = 'April 7',
    #     End_Date = 'October 26',
    # )

    return idf

def Location_and_weather(idf,building):
    #Weather_file = "USA_CO_Golden-NREL.724666_TMY3.epw"
    Weather_file = building.WeatherDataFile
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
    ground_Temp.July_Ground_Temperature = 15
    ground_Temp.August_Ground_Temperature = 15
    ground_Temp.September_Ground_Temperature = 15
    ground_Temp.October_Ground_Temperature = 15
    ground_Temp.November_Ground_Temperature = 15
    ground_Temp.December_Ground_Temperature = 15

    DesignDay= idf.idfobjects['SIZINGPERIOD:DESIGNDAY']
    for Obj in DesignDay:
        Obj.Barometric_Pressure = 100594

    return idf

if __name__ == '__main__' :
    print('Sim_Param Main')