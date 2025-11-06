import os
import shutil
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
        "Output Variables": [],
        "Global Variables": [],
        "Trend Variables": [],
        "Programs": [],
        "Program Calling Managers": [],
        "External Interfaces": []
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

            # --- Output Variables ---
            elif line.startswith("EnergyManagementSystem:OutputVariable Available") and len(parts) >= 4:
                edd_data["Output Variables"].append({
                    "Unique Key Name": parts[1],
                    "Output Variable Name": parts[2],
                    "Units": parts[3]
                })

            # --- Programs ---
            elif line.startswith("EnergyManagementSystem:Program,") and len(parts) >= 2:
                edd_data["Programs"].append({
                    "Program Name": parts[1]
                })

            # --- Program Calling Managers ---
            elif line.startswith("EnergyManagementSystem:ProgramCallingManager") and len(parts) >= 4:
                edd_data["Program Calling Managers"].append({
                    "Manager Name": parts[1],
                    "Calling Point": parts[2],
                    "Programs": parts[3:]
                })

            # --- External Interface Variables ---
            elif line.startswith("ExternalInterface:Variable") and len(parts) >= 3:
                edd_data["External Interfaces"].append({
                    "Type": "Variable",
                    "Variable Name": parts[1],
                    "Initial Value": parts[2]
                })

            # --- External Interface Actuators ---
            elif line.startswith("ExternalInterface:Actuator") and len(parts) >= 4:
                edd_data["External Interfaces"].append({
                    "Type": "Actuator",
                    "Component Type": parts[1],
                    "Control Type": parts[2],
                    "Unique Name": parts[3]
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


