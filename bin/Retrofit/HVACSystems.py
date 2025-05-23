def ZoneCtrl(idf,zone,building,PeopleDensity,ThermostatName, Multiplier,Correctdeff,FloorArea, ECM = ''):
    #add to all zones an ideal load element driven by the above thermostat
    #DCV stands for Demand Controlled Ventilation, the airflow is in m3/s/m2 thus divded by 1000 from yml
    # try:
    AreaBasedFlowRate = Correctdeff['AreaBasedFlowRate']
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=zone.Name,
        Template_Thermostat_Name=ThermostatName,
        # Heat_Recovery_Type='Sensible' if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 'None',
        # Sensible_Heat_Recovery_Effectiveness= 0.9,#Correctdeff['HReff']*building.AirRecovEff if building.VentSyst['BalX'] or building.VentSyst['ExhX'] else 0,
        Latent_Heat_Recovery_Effectiveness= 0,
        #Design_Specification_Outdoor_Air_Object_Name = AirNode,
        Outdoor_Air_Method='Sum' if PeopleDensity>0 and building.DemandControlledVentilation else 'Flow/Area',
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area=Multiplier*AreaBasedFlowRate/1000 + Multiplier*building.OccupBasedFlowRate/1000*PeopleDensity*(1-building.DemandControlledVentilation),
        Outdoor_Air_Flow_Rate_per_Person=building.OccupBasedFlowRate/1000,
        Demand_Controlled_Ventilation_Type = 'OccupancySchedule' if PeopleDensity>0 and building.DemandControlledVentilation else 'None',
        Heating_Limit = building.HVACLimitMode,
        Maximum_Sensible_Heating_Capacity =  FloorArea*building.HVACPowLimit, #the floor area already takes into account the zone multiplier
        #Outdoor_Air_Inlet_Node_Name = 'OutdoorAirNode'
        )
    idf.newidfobject(
        "OUTDOORAIR:NODE",
        Name=zone.Name+' IDEAL LOADS OUTDOOR AIR INLET',  # quite weird but it seems to work....the name does not referer to the otherone,
    )
    return id