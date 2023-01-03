# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

from eppy.results import readhtml
import esoreader
import os
import matplotlib.pyplot as plt
import numpy as np

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
            if 'People' in var2add and len(idf.idfobjects["PEOPLE"])==0:
                keep = False
            if keep:
                OutputsVar['Var'].append(var2add)
    return OutputsVar

def AddOutputs(idf,building,path,EMSOutputs,OutputsFile):
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
    zonelist = getHeatedZones(idf)
    if EMSOutputs:
        setEMS4MeanTemp(idf, zonelist, OutputsVar['Reportedfrequency'],EMSOutputs[0])
        setEMS4TotHeatPow(idf, building,zonelist, OutputsVar['Reportedfrequency'], EMSOutputs[1])
        if len(EMSOutputs)>2:
            setEMS4TotDHWPow(idf, building, zonelist, OutputsVar['Reportedfrequency'], EMSOutputs[2])
    # idf.newidfobject("OUTPUT:SQLITE",
    #                  Option_Type = 'SimpleAndTabular') # could be 'Simple' as well
    return idf

def getHeatedZones(idf):
    #returns the zone names that are above ground levels, which means heated zones
    zoneName = []
    AllZone = idf.idfobjects["ZONE"]
    for idx, zone in enumerate(AllZone):
        if int(zone.Name[zone.Name.find('Storey')+6:]) >= 0: #the name ends with Storey # so lets get the storey number this way
            zoneName.append(zone.Name)
    return zoneName

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

def Read_OutputsEso(CaseName,ExtSurfNames, ZoneOutput):
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
        if currentData[1].find('STOREY')>0:
            try:
                nb = int(currentData[1][currentData[1].find('STOREY')+6:])
            except:
                test = 1
                finished = 0
                while finished == 0:
                    try:
                        nb = int(currentData[1][currentData[1].find('STOREY')+6:-test])
                        finished = 1
                    except:
                        test += 1
            Firstkey = 'STOREY '+str(nb)
        else:
            Firstkey = currentData[1]
        if not res:
            res[Firstkey] = {}
            ZoneAgregRes[Firstkey] = {} #currentData[1]
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

