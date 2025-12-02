# @Author  : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

"""
This file prepares the required inputs for the Energy Management System (EMS).

The "Unique Component Name", "Component Type", and "Control Type" are automatically extracted
from the .edd file.

To generate the .edd file, an initial short simulation run is performed. After that, the identified
actuator parameters are implemented into the final model.
"""

import os
from subprocess import check_call
import platform

from sympy.codegen import Print


def EMS_Actuator_Handling_Module(nbRun, config, epluspath, CurrentSimDir, file2run):
    for i in range(len(file2run)):
    # If we have calibration or parametric study, we have more than one simulation for each building. Therefore, the .edd file would be the same for the building in different run.
    # So we run a short dynamic simulation for one idf and use the .edd file for the other idfs.
        if nbRun > 1:
            if not int(file2run[0][:file2run[0].find('.idf')][-1]) >= nbRun:
                if i == 0:
                    WeatherFile = config['3_SIM']['1_WeatherData']['WeatherDataFile']
                    EDD_Data = GenerateEDD(CurrentSimDir, epluspath, WeatherFile, file2run[i])
                    Add_Actuator(nbRun, CurrentSimDir, file2run[i], EDD_Data)
    # If nbRun is less than 2, then it means that in every run it is a new building. Therefore, we need short run for every one of them.
        else:
            WeatherFile = config['3_SIM']['1_WeatherData']['WeatherDataFile']
            EDD_Data = GenerateEDD(CurrentSimDir, epluspath, WeatherFile, file2run[i])
            Add_Actuator(nbRun, CurrentSimDir, file2run[i], EDD_Data)

def GenerateEDD(SimDir, epluspath, WeatherFile, file2run):
    Runfile = os.path.join(SimDir, file2run)
    RunDir = os.path.join(SimDir, file2run[:-4] + '_Temp')
    CaseName = 'Run'
    #the process is launched on external terminal window
    if platform.system() == "Windows":
        eplus_exe = os.path.join(epluspath, "energyplus.exe")
    else:
        eplus_exe = os.path.join(epluspath, "energyplus")
    weatherpath = os.path.join(epluspath, WeatherFile)
    cmd_Temp = [eplus_exe, '--weather',os.path.normcase(weatherpath),'--output-directory',RunDir, \
           '--idd',os.path.join(epluspath,'Energy+.idd'),'--expandobjects','-r','--output-prefix',CaseName,Runfile]

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

def Add_Actuator(nbRun, SimDir, file2run, EDD_Data):
    Actuators = EDD_Data.get('Actuators')
    for act in Actuators:
        try:
            if 'Heating Setpoint' in act.values():
                UniqueComponentName = act.get('Unique Component Name')
                ComponentType = act.get('Component Type')
                ControlType = act.get('Control Type')
                Name = 'Zone_' + UniqueComponentName + '_Override'
            # This object applies the defined program on HVAC template
                idfObject = (f"\n\nENERGYMANAGEMENTSYSTEM:ACTUATOR,\n \t {Name}, \t\t !- Name\n \t {UniqueComponentName}, \t\t !- Actuated Component Unique Name\n"
                     f" \t {ComponentType}, \t\t !- Actuated Component Type\n \t {ControlType}; \t\t !- Actuated Component Control Type \n\n")
                if nbRun > 1:
                    idf_files = [f for f in os.listdir(SimDir) if f.endswith('.idf')]
                    for idf_curr in idf_files:
                        with open(os.path.join(SimDir, idf_curr), "a", encoding="utf-8") as f:
                                        f.write(idfObject)
                else:
                    with open(os.path.join(SimDir, file2run), "a", encoding="utf-8") as f:
                        f.write(idfObject)
        except:
            msg = 'No component found to be controlled by actuator'
            Print(msg)

def setEMS4MeanTemp(idf,zonelist,Freq,name):
    """
    lets create the temperature sensors for each zones and catch their volume
    """
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
    #lets create the prgm callingManager (Define when EMS programs run during simulation)
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




