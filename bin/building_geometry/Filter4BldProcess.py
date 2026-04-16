# @Author  : Xavier Faure
# @Email   : xavierf@kth.se
import core.GeneralFunctions as GrlFct

def checkBldFilter(building,LogFile = [],DebugMode = False):
    CaseOk = len(building.BlocHeight) if building.Multipolygon else building.height
    msg =''
    # if the building have bloc with no Height or if the heigh is below 1m (shouldn't be as it is corrected in the Building class now)
    if len(building.BlocHeight) > 0 and min(building.BlocHeight) < 1:
        CaseOk = 0
        msg = '[Error] The building has a given height below 1m...\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    # is heated area is below 50m2, we just drop the building
    if building.EPHeatedArea < 50:
        CaseOk = 0
        msg = '[Error] The building has a given heated area below 50m2...\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    # is no floor is present...(shouldn't be as corrected in the Building class now)
    if 0 in building.BlocNbFloor:
        CaseOk = 0
        msg = '[Error] The building has a given number of floor equal to 0...\n'
        if DebugMode: GrlFct.Write2LogFile(msg, LogFile)
    return CaseOk,msg