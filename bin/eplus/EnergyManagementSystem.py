# @Author  : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

import os
from subprocess import check_call

def GenerateEDD():
    cmd_Temp = [
        '/Applications/EnergyPlus-9-5-0/energyplus',
        '--weather', '/Applications/EnergyPlus-9-5-0/WeatherData/SWE_ST_Stockholm.024850_TMYx.2009-2023.epw',
        '--output-directory',
        '/Users/alizad/PycharmProjects/NewWorking-MUBES/examples/Ex4-ParametricStudy/Building_1v0_Temp',
        '--idd', '/Applications/EnergyPlus-9-5-0/Energy+.idd',
        '--expandobjects',
        '--design-day',  #
        '--output-prefix', 'Run',
        '/Users/alizad/PycharmProjects/NewWorking-MUBES/examples/Ex4-ParametricStudy/Building_1v0.idf'
    ]

    # IDF.setiddname(cmd[6])
    # Temp_idf = IDF(os.path.join(filepath, file))
    # RunPeriodObject = Temp_idf.idfobjects['RUNPERIOD'][0]
    # End_Month_main = RunPeriodObject.End_Month
    # End_Day_of_Month_main = RunPeriodObject.End_Day_of_Month
    # Temp_idf.idfobjects['RUNPERIOD'][0] = 1
    # Temp_idf.idfobjects['RUNPERIOD'][0] = 1

    # Temp_idf.idfobjects['RUNPERIOD'][0].End_Month = 1
    # Temp_idf.idfobjects['RUNPERIOD'][0].End_Day_of_Month = 1
    # #
    # Temp_idf.idfobjects['SimulationControl'][0].Do_Zone_Sizing_Calculation = 'Yes'
    # Temp_idf.idfobjects['SimulationControl'][0].Do_System_Sizing_Calculation = 'Yes'
    # Temp_idf.idfobjects['SimulationControl'][0].Run_Simulation_for_Sizing_Periods = 'Yes'
    # Temp_idf.idfobjects['SimulationControl'][0].Run_Simulation_for_Weather_File_Run_Periods = 'No'
    # Temp_idf.idfobjects['building'][0].Maximum_Number_of_Warmup_Days = 2
    # Temp_idf.idfobjects['building'][0].Minimum_Number_of_Warmup_Days = 1
    # Temp_idf.idfobjects['building'][0].Loads_Convergence_Tolerance_Value = 100
    # Temp_idf.idfobjects['building'][0].Temperature_Convergence_Tolerance_Value = 100

    # subprocess.run(cmd, check=False)
    check_call(cmd_Temp, stdout=open(os.devnull, "w"), stderr=open(os.devnull, "w"))
    EDD_Data = Component_Name_4_Actuator(os.path.join(cmd_Temp[4], 'Runout.edd'))
    return EDD_Data

def Component_Name_4_Actuator(CurrentCase):
    edd_path = CurrentCase

    edd_data = {
        "Actuators": [],
        "Internal Variables": [],
    }

    with open(edd_path, "r") as f:
        for line in f:
            line = line.strip()
            parts = [p.strip().strip(';').strip('[]') for p in line.split(',')]

            # --- Actuators ---
            if line.startswith("EnergyManagementSystem:Actuator Available") and len(parts) >= 4:
                edd_data["Actuators"].append({
                    "Unique Component Name": parts[1],
                    "Component Type": parts[2],
                    "Control Type": parts[3]
                })

            # --- Internal Variables ---
            elif line.startswith("EnergyManagementSystem:InternalVariable Available") and len(parts) >= 4:
                edd_data["Internal Variables"].append({
                    "Unique Key Name": parts[1],
                    "Internal Variable Name": parts[2],
                    "Units": parts[3]
                })

    return edd_data

def Add_Actuator(idfPath, EDD_Data):

    Actuators = EDD_Data.get('Actuators')
    for act in Actuators:
        if 'Heating Setpoint' in act.values():
            UniqueComponentName = act.get('Unique Component Name')
            ComponentType = act.get('Component Type')
            ControlType = act.get('Control Type')
            Name = 'Zone_' + UniqueComponentName + '_Override'
        # This object applies the defined program on HVAC template
            idfObject = (f"\n\n ENERGYMANAGEMENTSYSTEM:ACTUATOR,\n \t {Name}, \t\t !- Name\n \t {UniqueComponentName}, \t\t !- Actuated Component Unique Name\n"
                 f" \t {ComponentType}, \t\t !- Actuated Component Type\n \t {ControlType}, \t\t !- Actuated Component Control Type \n\n")

            with open(idfPath, "a", encoding="utf-8") as f:
                        f.write(idfObject)

def setEMS4MeanTemp(idf,zonelist,Freq,name):
    #lets create the temperature sensors for each zones and catch their volume
    for idx,zone in enumerate(zonelist):
        idf.newidfobject(
            'ENERGYMANAGEMENTSYSTEM:SENSOR',
            Name = 'T'+str(idx),
            OutputVariable_or_OutputMeter_Index_Key_Name = zone,
            OutputVariable_or_OutputMeter_Name = 'Zone Mean Air Temperature',
            )
        idf.newidfobject(
            'ENERGYMANAGEMENTSYSTEM:INTERNALVARIABLE',
            Name = 'Vol'+str(idx),
            Internal_Data_Index_Key_Name = zone,
            Internal_Data_Type = 'Zone Air Volume'
            )
    #lets create the prgm callingManager
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAMCALLINGMANAGER',
        Name='Average Building Temperature',
        EnergyPlus_Model_Calling_Point='EndOfZoneTimestepBeforeZoneReporting' ,
        Program_Name_1='AverageZoneTemps'
    )
    #lets create the global Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:GLOBALVARIABLE',
        Erl_Variable_1_Name='AverageBuildingTemp' ,
    )
    #lets create the EMS Output Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:OUTPUTVARIABLE',
        Name=name,
        EMS_Variable_Name='AverageBuildingTemp' ,
        Type_of_Data_in_Variable='Averaged',
        Update_Frequency = 'ZoneTimeStep'
    )
    #lets create the program
    listofTemp = ['T'+str(i) for i in range(len(zonelist))]
    listofVol = ['Vol' + str(i) for i in range(len(zonelist))]
    SumNumerator = ''
    SumDenominator = ''
    for idx,Temp in enumerate(listofTemp):
        SumNumerator = SumNumerator+Temp+'*'+listofVol[idx]+'+'
        SumDenominator = SumDenominator + listofVol[idx] + '+'
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAM',
        Name='AverageZoneTemps',
        Program_Line_1='SET SumNumerator = '+SumNumerator[:-1],
        Program_Line_2='SET SumDenominator  = '+SumDenominator[:-1],
        Program_Line_3='SET AverageBuildingTemp  = SumNumerator / SumDenominator',
    )

    # This object applies the defined program on HVAC template
    # idf.newidfobject(
    #     "ENERGYMANAGEMENTSYSTEM:ACTUATOR",
    #     Name= "Zone1_HeatSetpoint_Override",
    #     Actuated_Component_Unique_Name= 'cool_sch',
    #     Actuated_Component_Type= "SCHEDULE:CONSTANT",
    #     Actuated_Component_Control_Type= "Schedule Value"
    # )
    #lets create now the ouputs of this EMS
    idf.newidfobject(
        'OUTPUT:ENERGYMANAGEMENTSYSTEM',
        Actuator_Availability_Dictionary_Reporting='Verbose',
        EMS_Runtime_Language_Debug_Output_Level='Verbose',
        Internal_Variable_Availability_Dictionary_Reporting='Verbose',
    )
    #lets create now the final outputs
    idf.newidfobject(
        'OUTPUT:VARIABLE',
        Variable_Name=name,
        Reporting_Frequency=Freq,
    )

def setEMS4TotHeatPow(idf,building,zonelist,Freq,name):
    #lets create the temperature sensors for each zones and catch their volume
    for idx,zone in enumerate(zonelist):
        idf.newidfobject(
            'ENERGYMANAGEMENTSYSTEM:SENSOR',
            Name = 'Pow'+str(idx),
            OutputVariable_or_OutputMeter_Index_Key_Name = zone+' IDEAL LOADS AIR SYSTEM',
            OutputVariable_or_OutputMeter_Name = 'Zone Ideal Loads Supply Air Total Heating Rate'
            )
    #lets create the prgm collingManager
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAMCALLINGMANAGER',
        Name='Compute Total Building Heat Pow',
        EnergyPlus_Model_Calling_Point='EndOfZoneTimestepBeforeZoneReporting' ,
        Program_Name_1='TotZonePow'
    )
    #lets create the global Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:GLOBALVARIABLE',
        Erl_Variable_1_Name='TotBuildPow' ,
    )
    #lets create the EMS Output Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:OUTPUTVARIABLE',
        Name=name,
        EMS_Variable_Name='TotBuildPow' ,
        Type_of_Data_in_Variable='Averaged',
        Update_Frequency = 'ZoneTimeStep'
    )
    #lets create the program
    listofPow = ['Pow'+str(i) for i in range(len(zonelist))]
    SumNumerator = ''
    for idx,Pow in enumerate(listofPow):
        SumNumerator = SumNumerator+Pow+'+'
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAM',
        Name='TotZonePow',
        Program_Line_1='SET TotBuildPow = '+ SumNumerator[:-1],
    )
    #to uncomment if the EMS is not created before for the mean air tempeatrue
    # #lets create now the ouputs of this EMS
    # idf.newidfobject(
    #     'OUTPUT:ENERGYMANAGEMENTSYSTEM',
    #     Actuator_Availability_Dictionary_Reporting='Verbose',
    #     EMS_Runtime_Language_Debug_Output_Level='Verbose',
    #     Internal_Variable_Availability_Dictionary_Reporting='Verbose',
    # )

    #lets create now the final outputs
    idf.newidfobject(
        'OUTPUT:VARIABLE',
        Variable_Name=name,
        Reporting_Frequency=Freq,
    )

def setEMS4TotDHWPow(idf,building,zonelist,Freq,name):
    #lets create the temperature sensors for each zones and catch their volume
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:SENSOR',
        Name = 'DHWPow',
        OutputVariable_or_OutputMeter_Index_Key_Name = 'DHW',
        OutputVariable_or_OutputMeter_Name = 'Water Use Equipment Heating Rate'
        )

    #lets create the prgm collingManager
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAMCALLINGMANAGER',
        Name='Compute Total DHW Heat Pow',
        EnergyPlus_Model_Calling_Point='EndOfZoneTimestepBeforeZoneReporting' ,
        Program_Name_1='prgmDHWPow'
    )
    #lets create the global Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:GLOBALVARIABLE',
        Erl_Variable_1_Name='TotDHWPow' ,
    )
    #lets create the EMS Output Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:OUTPUTVARIABLE',
        Name=name,
        EMS_Variable_Name='TotDHWPow' ,
        Type_of_Data_in_Variable='Averaged',
        Update_Frequency = 'ZoneTimeStep'
    )
    #lets create the program
    SumNumerator = 'DHWPow'
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAM',
        Name='prgmDHWPow',
        Program_Line_1='SET TotDHWPow = '+ SumNumerator,
    )
    #to uncomment if the EMS is not created before for the mean air tempeatrue
    # #lets create now the ouputs of this EMS
    # idf.newidfobject(
    #     'OUTPUT:ENERGYMANAGEMENTSYSTEM',
    #     Actuator_Availability_Dictionary_Reporting='Verbose',
    #     EMS_Runtime_Language_Debug_Output_Level='Verbose',
    #     Internal_Variable_Availability_Dictionary_Reporting='Verbose',
    # )

    #lets create now the final outputs
    idf.newidfobject(
        'OUTPUT:VARIABLE',
        Variable_Name=name,
        Reporting_Frequency=Freq,
    )




