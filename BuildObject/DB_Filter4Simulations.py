# @Author  : Xavier Faure
# @Email   : xavierf@kth.se


def checkBldFilter(building):
    CaseOk = len(building.BlocHeight) if building.Multipolygon else building.height
    # if the building have bloc with no Height or if the hiegh is below 1m (shouldn't be as corrected in the Building class now)
    if len(building.BlocHeight) > 0 and min(building.BlocHeight) < 1:
        CaseOk = 0
    # is heated area is below 50m2, we just drop the building
    if building.EPHeatedArea < 50:
        CaseOk = 0
    # is no floor is present...(shouldn't be as corrected in the Building class now)
    if 0 in building.BlocNbFloor:
        CaseOk = 0
    return CaseOk