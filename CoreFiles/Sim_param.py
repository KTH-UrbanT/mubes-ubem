# @Author  : Xavier Faure
# @Email   : xavierf@kth.se


def setSimparam(idf,building):
    #changing the running period
    simctrl = idf.idfobjects['SIMULATIONCONTROL'][0]
    simctrl.Run_Simulation_for_Sizing_Periods= 'No'
    simctrl.Run_Simulation_for_Weather_File_Run_Periods = 'Yes'
    #changing the Solar calculation because of complex surface (non convexe for inside floors)
    build_param = idf.idfobjects['BUILDING'][0]
    build_param.Solar_Distribution = 'FullExterior' #'FullInteriorAndExterior' #'FullExteriorWithReflections' #'FullExterior' #'MinimalShadowing' # FullExterior is the most detailed option possible in our case.
    #it computes exteriori shading bu not internal. all the radiation that enters the zones is allocated to the floor
    # https://bigladdersoftware.com/epx/docs/9-1/engineering-reference/shading-module.html#solar-distribution
    #the one with reflection might not be needed and takes more cumputational time (it worth it for specific radiation propreties of the surroundings surfaces
    #but these are tekan from default value from now

    shadow_param = idf.newidfobject('SHADOWCALCULATION')
    #ShadowCalculation options for energyPlus v9.1.0
    if idf.idd_version in [(9, 1, 0),(9, 2, 0)]:
        shadow_param.Calculation_Frequency = 20  #number of days acounted for the method. not used if TimestepFrequency is choosen in Calculation_Method
        shadow_param.Calculation_Method = 'AverageOverDaysInFrequency'     #or TimestepFrequency
        shadow_param.Sky_Diffuse_Modeling_Algorithm = 'SimpleSkyDiffuseModeling' #unless there is changes in the transmittance of shadings along the year (DetailedSkyDiffuseModeling)
        shadow_param.External_Shading_Calculation_Method  = 'InternalCalculation' #can be ImportedShading is it has been computed before (with yes on the option below)
    else:
        # ShadowCalculation options for energyPlus v9.4.0 and above(maybe)
        shadow_param.Shading_Calculation_Method = 'PolygonClipping' #can be PixelCounting for the use of GPU or Imported if earlier saved in a file
        shadow_param.Shading_Calculation_Update_Frequency_Method = 'Periodic' # Can be Timestep
        shadow_param.Shading_Calculation_Update_Frequency = 20  #number of days acounted for the method. not used if TimestepFrequency is choosen in Calculation_Method
        shadow_param.Pixel_Counting_Resolution = 512 #default value, increasing it can incerease the time of computation, but I don't know if used if not pixelcounting method used"
    #the following should be commun to all version (above 9.1.0)
    shadow_param.Maximum_Figures_in_Shadow_Overlap_Calculations = 25000  # it's 15000 by default but raised here because of UBEM and large surrounding
    shadow_param.Polygon_Clipping_Algorithm = 'SutherlandHodgman'
    shadow_param.Sky_Diffuse_Modeling_Algorithm = 'SimpleSkyDiffuseModeling'  # unless there is changes in the transmittance of shadings along the year (DetailedSkyDiffuseModeling)
    shadow_param.Output_External_Shading_Calculation_Results = 'No'  # if Yes,the calculated external shading fraction results will be saved to an external CSV file with surface names as the column headers (for further used in parametric simulation and gain time


    runperiod = idf.idfobjects['RUNPERIOD'][0]
    runperiod.Begin_Day_of_Month = building.Begin_Day_of_Month
    runperiod.Begin_Month = building.Begin_Month
    runperiod.End_Day_of_Month = building.End_Day_of_Month
    runperiod.End_Month = building.End_Month
    #set the heat algorithm
    # idf.newidfobject(
    #     'HEATBALANCEALGORITHM',
    #     Algorithm = 'ConductionTransferFunction',#'ConductionFiniteDifference', #
    # )
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
    idf.epw = Weather_file if '.epw' in Weather_file[:-4] else Weather_file+'.epw'
    location = idf.idfobjects['SITE:LOCATION'][0]   #there might be some way of taking the information from the weather file directly in the idf object...
    location.Name = Weather_file
    location.Latitude = building.Latitude
    location.Longitude = building.Longitude
    location.Time_Zone = building.Time_Zone
    location.Elevation = building.Elevation
    ground_Temp = idf.newidfobject('SITE:GROUNDTEMPERATURE:BUILDINGSURFACE')
    ground_Temp.January_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.February_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.March_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.April_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.May_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.June_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.July_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.August_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.September_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.October_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.November_Ground_Temperature = building.YearRoundGroundTemp
    ground_Temp.December_Ground_Temperature = building.YearRoundGroundTemp

    DesignDay= idf.idfobjects['SIZINGPERIOD:DESIGNDAY']
    for Obj in DesignDay:
        Obj.Barometric_Pressure = 100594

    return idf

if __name__ == '__main__' :
    print('Sim_Param Main')