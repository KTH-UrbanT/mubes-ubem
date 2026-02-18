# @Author  : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

import os
import numpy as np
import pickle
import sys
from pathlib import Path
import matplotlib.pyplot as plt


PROJECT_ROOT = Path().resolve()
BIN_PATH = '/Users/alizad/PycharmProjects/NewWorking-MUBES'
from bin.outputs import output_utilities
import core.GeneralFunctions as GrlFct
import building_geometry.BuildingObject as BuildingObject

sys.path.insert(0, str(BIN_PATH))

def Calc_COP_SCOP(OutTemp, SuppSpaceTemp, SuppDHWTemp, Eff1, Eff2, LowBound, UppBound):
    """
    lets create the temperature sensors for each zones and catch their volume
    """

    OutTemp = OutTemp + 273.15
    SuppSpaceTemp = SuppSpaceTemp + 273.15
    SuppDHWTemp = SuppDHWTemp + 273.15
    # --- Space ---
    deltaT_space = SuppSpaceTemp - OutTemp
    deltaT_space = np.maximum(deltaT_space, 5.0)  # minimum 5 K lift
    COP_Space = Eff1 * SuppSpaceTemp / deltaT_space
    COP_Space = np.clip(COP_Space, LowBound, UppBound)
    # --- DHW ---
    deltaT_dhw = SuppDHWTemp - OutTemp
    deltaT_dhw = np.maximum(deltaT_dhw, 5.0)  # minimum 5 K lift

    COP_DHW = Eff2 * SuppDHWTemp / deltaT_dhw
    COP_DHW = np.clip(COP_DHW, LowBound, UppBound)

    return COP_Space, COP_DHW


def HeatPumpHeat2Elec(SimDir, HP_Space_Share, HP_DHW_Share):
    results_by_building = {}
    path = SimDir
    files = os.listdir(os.path.join(path, 'Sim_Results'))
    for bld in files:
        if bld.endswith('.pickle'):
            with open(os.path.join(os.path.join(path, 'Sim_Results'), bld), 'rb') as f:
                results_by_building[bld] = pickle.load(f)

    assert isinstance(results_by_building, dict)
    for idx, BldRes in results_by_building.items():
        # COP = BldRes['Other']['Data_HeatPumpCOP']
        Q_Space = BldRes['Other']['Data_Total Building Heating Power']
        Q_DHW = BldRes['Other']['Data_Total DHW Heating Power']
        OutTemp = BldRes['Other']['Data_Site Outdoor Air Drybulb Temperature']
        SuppDHWTemp = BldRes['Other']['Data_Water Use Equipment Hot Water Temperature']
        SuppSpaceTemp = BldRes['HeatedArea']['Data_Zone Ideal Loads Supply Air Temperature']
        OutTemp = np.array(OutTemp)
        Q_Space = np.array(Q_Space)
        Q_DHW = np.array(Q_DHW)
        SuppDHWTemp = np.array(SuppDHWTemp)
        SuppSpaceTemp = np.array(SuppSpaceTemp)
        COP_Space, COP_DHW = Calc_COP_SCOP(OutTemp, SuppSpaceTemp, SuppDHWTemp, Eff1=0.4, Eff2=0.4,
                                           LowBound=0.5, UppBound=5)
        E_Space = Q_Space/COP_Space
        E_DHW = Q_DHW/COP_DHW
        # 2) Peak heat demand
        QpeakDHW = np.max(Q_DHW)
        QpeakSpace = np.max(Q_Space)
        # 3) Heat pump capacity (70% sizing)
        Cap_Space_HP = HP_Space_Share * QpeakSpace
        Cap_DHW_HP = HP_DHW_Share * QpeakDHW
        # 4) Heat supplied by HP each timestep
        Q_Space_HP = np.minimum(Q_Space, Cap_Space_HP)
        Q_DHW_HP = np.minimum(Q_DHW, Cap_DHW_HP)
        E_Space_HP = Q_Space_HP/COP_Space
        E_DHW_HP = Q_DHW_HP / COP_DHW
        # 1) Total heat demand
        Q_tot = Q_Space + Q_DHW
        Q_tot_HP = Q_Space_HP + Q_DHW_HP
        # 5) Backup heat
        Q_backup = Q_tot - Q_tot_HP

        Plot_QvsOutTemp(OutTemp, Q_DHW_HP, Q_Space_HP, Q_backup, idx)
        Plot_COPvsTemp(OutTemp, COP_Space, COP_DHW, idx)
        SCOP(Q_Space_HP, Q_DHW_HP, E_Space_HP, E_DHW_HP)

def SCOP(Q_Space_HP, Q_DHW_HP, E_Space_HP, E_DHW_HP):

    SCOP_space = np.sum(Q_Space_HP) / np.sum(E_Space_HP)
    SCOP_dhw = np.sum(Q_DHW_HP) / np.sum(E_DHW_HP)
    SCOP_Total = np.sum(Q_Space_HP + Q_DHW_HP)/ np.sum(E_DHW_HP + E_Space_HP)
    print('SCOP of space heating: ', SCOP_space)
    print('SCOP of DHW heating: ', SCOP_dhw)
    print('SCOP total: ', SCOP_Total)


def Plot_QvsOutTemp(OutTemp, Q_DHW_HP, Q_Space_HP, Q_backup, idx):
    # Sort by outdoor temperature
    idx_sort = np.argsort(OutTemp)
    T_sorted = OutTemp[idx_sort]
    Q_DHW_sorted = Q_DHW_HP[idx_sort]
    Q_Space_sorted = Q_Space_HP[idx_sort]
    Q_backup_sorted = Q_backup[idx_sort]

    plt.figure(figsize=(10, 6))
    plt.stackplot(
        T_sorted,
        Q_DHW_sorted,
        Q_Space_sorted,
        Q_backup_sorted,
        labels=["DHW (HP)", "Space (HP)", "Backup"],
        alpha=0.85)

    plt.xlabel("Outdoor Temperature (°C)")
    plt.ylabel("Heat Power")
    plt.title(f"Heat Distribution vs Outdoor Temperature - {idx}")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.show()

def Plot_COPvsTemp(OutTemp, COP_Space, COP_DHW , idx):
    import matplotlib.pyplot as plt
    import numpy as np
    # Sort by temperature
    idx_sort = np.argsort(OutTemp)
    T_sorted = OutTemp[idx_sort]
    COP_Space_sorted = COP_Space[idx_sort]
    COP_DHW_sorted = COP_DHW[idx_sort]

    plt.figure(figsize=(10, 6))

    plt.scatter(T_sorted, COP_Space_sorted, label="COP Space", linewidth=2)
    plt.scatter(T_sorted, COP_DHW_sorted, label="COP DHW", linewidth=2)

    plt.xlabel("Outdoor Temperature (°C)")
    plt.ylabel("COP")
    plt.title(f"COP vs Outdoor Temperature - {idx}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    SimDir = '/Users/alizad/PycharmProjects/NewWorking-MUBES/examples/NUS'
    HeatPumpHeat2Elec(SimDir, 0.7, 0.7)
