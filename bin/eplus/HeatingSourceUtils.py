# @Author  : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

import os
import numpy as np
import pickle


def findCOP(idf,Freq):
    """
    lets create the temperature sensors for each zones and catch their volume
    """
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:GLOBALVARIABLE',
        Erl_Variable_1_Name='COPvalue',
    )

    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAM',
        Name='CalculateCOP',

        # realistic supply temperature (40°C example)
        Program_Line_1='SET T_hot = 40 + 273.15',

        Program_Line_2='SET T_cold = OutDryBulb + 273.15',

        Program_Line_3='SET DeltaT = T_hot - T_cold',

        # protect against very small ΔT
        Program_Line_4='IF DeltaT < 5',
        Program_Line_5='  SET DeltaT = 5',
        Program_Line_6='ENDIF',

        # Carnot-based COP
        Program_Line_7='SET COPvalue = 0.45 * (T_hot / DeltaT)',

        # upper limit (realistic cap)
        Program_Line_8='IF COPvalue > 6',
        Program_Line_9='  SET COPvalue = 6',
        Program_Line_10='ENDIF',

        # lower limit
        Program_Line_11='IF COPvalue < 1',
        Program_Line_12='  SET COPvalue = 1',
        Program_Line_13='ENDIF',
    )

    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAMCALLINGMANAGER',
        Name='COP_Manager',
        EnergyPlus_Model_Calling_Point='EndOfZoneTimestepBeforeZoneReporting',
        Program_Name_1='CalculateCOP',
    )

    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:OUTPUTVARIABLE',
        Name='HeatPumpCOP',
        EMS_Variable_Name='COPvalue',
        Type_of_Data_in_Variable='Averaged',
        Update_Frequency='ZoneTimestep',
    )
    idf.newidfobject(
        'OUTPUT:VARIABLE',
        Variable_Name='HeatPumpCOP',
        Reporting_Frequency=Freq,
    )


def HeatPumpHeat2Elec(SimDir):

    results_by_building = {}

    path = SimDir
    files = os.listdir(os.path.join(path, 'Sim_Results'))

    for bld in files:
        if bld.endswith('.pickle'):
            with open(os.path.join(os.path.join(path, 'Sim_Results'), bld), 'rb') as f:
                results_by_building[bld] = pickle.load(f)

    assert isinstance(results_by_building, dict)


    # Q_space and Q_dhw must be arrays of 8760 values
    # (kW or kWh per hour — same unit for both)
    for idx, BldRes in results_by_building.items():
        COP = BldRes['Other']['Data_HeatPumpCOP']
        Q_Space = BldRes['Other']['Data_Total Building Heating Power']
        Q_DHW = BldRes['Other']['Data_Total DHW Heating Power']

        Q_Space = np.array(Q_Space)
        Q_DHW = np.array(Q_DHW)

        # 1) Total heat demand
        Q_tot = Q_Space + Q_DHW

        # 2) Peak heat demand
        Q_peak = np.max(Q_tot)

        # 3) Heat pump capacity (70% sizing)
        P_HP = 0.7 * Q_peak

        # 4) Heat supplied by HP each timestep
        Q_HP = np.minimum(Q_tot, P_HP)

        # 5) Backup heat
        Q_backup = Q_tot - Q_HP

