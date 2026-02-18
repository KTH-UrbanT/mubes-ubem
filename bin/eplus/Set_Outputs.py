# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

# @Modified by : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

from eppy.results import readhtml
import esoreader
import matplotlib.pyplot as plt
import numpy as np
from eplus.EnergyManagementSystem import * #setEMS4MeanTemp, setEMS4TotHeatPow, setEMS4TotDHWPow

def getOutputList(path,idf,OutputsFile):
    OutputsVar = {}
    OutputsVar['Var'] = []
    outputs = open(os.path.join(path,'outputs',OutputsFile), 'r')
    Lines = outputs.readlines()
    for line in Lines:
        tofind = 'Reporting_Frequency ='
        if tofind in line:
            OutputsVar['Reportedfrequency'] = line[line.index(tofind)+len(tofind)+1:-1]
        if '## ' in line[:3]:
            var = line[3:][::-1]
            var2add = var[var.index('[')+2:var.index(',')][::-1]
            keep = True
            if 'People' in var2add and len(idf.idfobjects["PEOPLE"])==0: # TODO: What is it for?
                keep = False
            if keep:
                OutputsVar['Var'].append(var2add)
    return OutputsVar

def AddOutputs(idf,building,path, SimDir, CurrentBld2Run, EMSOutputs,OutputsFile):
    OutputsVar = getOutputList(path,idf,OutputsFile)
    #we shall start by removing all predclared outputes from the template
    predef = idf.idfobjects["OUTPUT:VARIABLE"]
    for i in reversed(predef):
        idf.removeidfobject(i)
    idf.newidfobject(
        "OUTPUT:DIAGNOSTICS",
        Key_1="DISPLAYEXTRAWARNINGS",
        Key_2 ="DisplayAdvancedReportVariables",
    )
    for var in OutputsVar['Var']:
        idf.newidfobject(
            "OUTPUT:VARIABLE",
            Variable_Name=var,
            Reporting_Frequency=OutputsVar['Reportedfrequency'],
        )
    idf.newidfobject(
        "OUTPUT:METER",
        Key_Name="Electricity:Facility",
        Reporting_Frequency="Hourly",
    )
    #
    idf.newidfobject(
        "OUTPUT:METER",
        Key_Name="ElectricityPurchased:Facility",
        Reporting_Frequency="Hourly",
    )
    #
    idf.newidfobject(
        "OUTPUT:METER",
        Key_Name="ElectricitySurplusSold:Facility",
        Reporting_Frequency="Hourly",
    )

    zonelist = getHeatedZones(idf)
    if EMSOutputs:
        # ActuatedComponentName = Component_Name_4_Actuator(os.path.join(SimDir, CurrentBld2Run, 'Runout.edd'))
        setEMS4MeanTemp(idf, zonelist, OutputsVar['Reportedfrequency'],EMSOutputs[0])
        setEMS4TotHeatPow(idf, building,zonelist, OutputsVar['Reportedfrequency'], EMSOutputs[1])
        if len(EMSOutputs)>2:
            setEMS4TotDHWPow(idf, building, zonelist, OutputsVar['Reportedfrequency'], EMSOutputs[2])
    # idf.newidfobject("OUTPUT:SQLITE",
    #                  Option_Type = 'SimpleAndTabular') # could be 'Simple' as well
    return idf, OutputsVar

def getHeatedZones(idf):
    #returns the zone names that are above ground levels, which means heated zones
    zoneName = []
    AllZone = idf.idfobjects["ZONE"]
    for idx, zone in enumerate(AllZone):
        if int(zone.Name[zone.Name.find('Storey_')+7:]) >= 0: #the name ends with Storey # so lets get the storey number this way
            zoneName.append(zone.Name)
    return zoneName

def Read_OutputsEso(CaseName,ExtSurfNames, PerBlockResult, ZoneOutput):
    #visualization of the results
    eso = esoreader.read_from_path(CaseName)
    ZoneAgregRes = {}
    BuildAgregRes = {}
    #We agregate results per storey
    res ={}
    for idx in eso.dd.variables.keys():
        currentData = eso.dd.variables[idx]
        if 'Surface' in currentData[2]:
            if currentData[1] not in ExtSurfNames:
                continue
            else:
                if 'ROOF' in currentData[1]:
                    currentData[2] += ' On Roofs'
                else:
                    currentData[2] += ' On Vertical Walls'
        if currentData[1] is not None and currentData[1].find('STOREY')>0:
            try:
                # The results will be aggregated at each storey which means if we have two blocks or more in one building,
                # the results of each storey are summed if PerBlockResult is False
                if PerBlockResult:
                    BldBlckStry = currentData[1][:currentData[1].find('STOREY_') + 12:]
                else:
                    nb = int(currentData[1][currentData[1].find('STOREY_')+7:])

            except:
                test = 1
                finished = 0
                while finished == 0:
                    try:
                        nb = int(currentData[1][currentData[1].find('STOREY_')+7:-test])
                        # blck_nd = int(currentData[1][currentData[1].find('BUILD') + 5])
                        finished = 1
                    except:
                        test += 1
            Firstkey = BldBlckStry if PerBlockResult else 'STOREY ' + str(nb)
        elif currentData[1] is not None:
            Firstkey = currentData[1]
        else:
            Firstkey = 'Meter'
            currentData[1] = 'Metering'
        if not res:
            res[Firstkey] = {}
            ZoneAgregRes[Firstkey] = {}
        if not currentData[1] in res.keys():
            findsame = 0

            for key in res.keys():
                if currentData[1] in key or key in currentData[1]:
                    Firstkey = key
                    findsame = 1

            if not findsame:
                res[Firstkey] = {}
                ZoneAgregRes[Firstkey] = {}
        if not currentData[2] in res[Firstkey].keys():
            res[Firstkey][currentData[2]] = {}
            ZoneAgregRes[Firstkey][currentData[2]] = {}
            res[Firstkey][currentData[2]]['Data'] = []
        res[Firstkey][currentData[2]]['Data'].append(eso.data[idx])
        res[Firstkey][currentData[2]]['TimeStep'] = currentData[0]
        res[Firstkey][currentData[2]]['Unit'] = currentData[3]
    BuildAgregRes['HeatedArea']= {}
    BuildAgregRes['NonHeatedArea'] = {}
    BuildAgregRes['Other']= {}
    for nb, key in enumerate(res):
        KeyArea = 'Other'
        if 'STOREY' in key:
            if PerBlockResult:
                numstor = int(key[key.find('STOREY_') + 7:])
            else:
                numstor= int(key[6:])
            KeyArea= 'NonHeatedArea' if numstor<0 else 'HeatedArea'
        for j, i in enumerate(res[key]):
            ZoneAgregRes[key][i]['GlobData'] = []
            ZoneAgregRes[key][i]['TimeStep'] = res[key][i]['TimeStep']
            ZoneAgregRes[key][i]['Unit'] = res[key][i]['Unit']
            ZoneAgregRes[key][i]['NbNode'] = len(res[key][i]['Data'])
            #here I need to introduce some filtering in order to catch only outside facing surfaces (to compare core/perimeter thermal zoning woth other kind
            if res[key][i]['Unit'] in {'C','W/m2-K','W/m2'}: #then lets compute the mean, if not lets sum it
                for ii in zip(*res[key][i]['Data']):
                    ZoneAgregRes[key][i]['GlobData'].append(sum(ii)/len(res[key][i]['Data']))
            else:
                for ii in zip(*res[key][i]['Data']):
                    ZoneAgregRes[key][i]['GlobData'].append(sum(ii))
            #lets deal with data now at the building level
            if not i in BuildAgregRes[KeyArea].keys():
                BuildAgregRes[KeyArea][i] = {}
                BuildAgregRes[KeyArea][i]['GlobData'] = ZoneAgregRes[key][i]['GlobData']
                BuildAgregRes[KeyArea][i]['TimeStep'] = ZoneAgregRes[key][i]['TimeStep']
                BuildAgregRes[KeyArea][i]['Unit'] = ZoneAgregRes[key][i]['Unit']
                BuildAgregRes[KeyArea][i]['NbNode'] = ZoneAgregRes[key][i]['NbNode']
            else:
                if res[key][i]['Unit'] in {'C','W/m2-K','W/m2'}:
                    BuildAgregRes[KeyArea][i]['GlobData'] = [sum(x)/2 for x in zip(BuildAgregRes[KeyArea][i]['GlobData'], ZoneAgregRes[key][i]['GlobData'])]
                else:
                    BuildAgregRes[KeyArea][i]['GlobData'] = [sum(x) for x in zip(BuildAgregRes[KeyArea][i]['GlobData'], ZoneAgregRes[key][i]['GlobData'])]
    if PerBlockResult and not ZoneOutput:
        msg = '[Output Info] Per-block and per-zone results were not generated because "PerZoneResult" is disabled in the configuration.'
        print(msg)
    elif PerBlockResult and ZoneOutput:
        msg = '[Output Info] Results have been generated for each block and zone.'
        print(msg)
    elif not PerBlockResult and ZoneOutput:
        msg = '[Output Info] Results have been aggregated and reported at the zone level.'
        print(msg)
    elif not PerBlockResult and not ZoneOutput:
        msg = '[Output Info] Results have been aggregated and reported at the building level.'
        print(msg)

    return ZoneAgregRes if ZoneOutput else BuildAgregRes

def Plot_Outputs(res,idf):
    # visualization of the results
    timestp = idf.idfobjects['TIMESTEP'][0].Number_of_Timesteps_per_Hour
    endtime = int(len(res['Environment']['Site Outdoor Air Drybulb Temperature']['GlobData']) / timestp)
    for nb,key in enumerate(res):
        plt.figure(nb)
        for j,i in enumerate(res[key]):
            plt.subplot(2,int((len(res[key])-1)/2+1),j+1)
            if not res[key][i]['TimeStep'] in 'TimeStep':
                timestp = 1
            plt.plot(np.linspace(0, endtime, endtime * timestp), res[key][i]['GlobData'])
            plt.title(i+'('+res[key][i]['Unit']+')')

    plt.show()

def Read_Outputhtml(CaseName):
    #compairons of surfaces
    fname = CaseName
    filehandle = open(fname, 'r',encoding='latin-1').read() # get a file handle to the html file
    htables = readhtml.titletable(filehandle)
    #this few lines below is just to grab the names of outdoor facing surfaces and windows
    for i in range(len(htables)):
        if htables[i][0] in 'Opaque Exterior':
            Opaque_exterior = htables[i][1][1:]
        elif htables[i][0] in 'Exterior Fenestration':
            Windows_exterior = htables[i][1][1:]
        elif htables[i][0] in 'Window-Wall Ratio':
            Envelope_idx = i
        elif htables[i][0] in 'Zone Summary':
            Zone_Summary_idx = i
    EndUsesIdx = 3
    ExtSurf = [name[0] for name in Opaque_exterior if 'WALL' in name[1]]
    ExtWin = [name[0] for name in Windows_exterior]
    ExtNames = ExtSurf+ExtWin
    Res = {}
    # #grab the building Shape FActor
    #the index table has changed so some further development should be done to consider all cases to grab external envelope and volume
    # Envelope = htables[Envelope_idx][1][2][1]
    # gotit = False
    # ii = 0
    # while not gotit:
    #     if 'Conditioned Total' in htables[Zone_Summary_idx][1][ii][0]:
    #         Volume = htables[Zone_Summary_idx][1][ii][4]
    #         gotit = True
    #     else:
    #         ii += 1
    # ShapeFactor= Envelope / Volume
    Envelope = 0
    Volume = 0

    for key in range(len(htables[EndUsesIdx][1][1:-2])):
        Res[htables[EndUsesIdx][1][key+1][0]] = {}
        for val in range(len(htables[EndUsesIdx][1][0][1:])):
            Res[htables[EndUsesIdx][1][key+1][0]][htables[EndUsesIdx][1][0][val+1]] = htables[EndUsesIdx][1][key+1][val+1]
    return {'GlobRes':Res, 'OutdoorSurfacesNames' : ExtNames, 'ExtEnvSurf' : Envelope, 'IntVolume': Volume}

def Read_OutputError(CaseName):
    fname = CaseName
    Endsinfo = open(fname, 'r', encoding='latin-1').read()
    Endsinfo


if __name__ == '__main__' :
    print('Set_Outputs Main')

