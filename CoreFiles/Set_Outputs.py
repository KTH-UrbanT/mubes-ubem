from eppy.results import readhtml
import esoreader
import os
import matplotlib.pyplot as plt
import numpy as np

def getOutputList(path):
    OutputsVar = {}
    OutputsVar['Var'] = []
    outputs = open(os.path.join(path,'Outputs.txt'), 'r')
    Lines = outputs.readlines()
    for line in Lines:
        tofind = 'Reporting_Frequency ='
        if tofind in line:
            OutputsVar['Reportedfrequency'] = line[line.index(tofind)+len(tofind)+1:-1]
        if '## ' in line[:3]:
            var = line[3:][::-1]
            var2add = var[var.index('[')+2:var.index(',')][::-1]
            OutputsVar['Var'].append(var2add)
    return OutputsVar

def AddOutputs(idf,path):

    OutputsVar = getOutputList(path)
    #we shall start by removing all predclared outputes from the template
    predef = idf.idfobjects["OUTPUT:VARIABLE"]
    for i in reversed(predef):
        idf.removeidfobject(i)
    idf.newidfobject(
        "OUTPUT:DIAGNOSTICS",
        Key_1="DISPLAYEXTRAWARNINGS",
    )

    for var in OutputsVar['Var']:
        idf.newidfobject(
            "OUTPUT:VARIABLE",
            Variable_Name=var,
            Reporting_Frequency=OutputsVar['Reportedfrequency'],
        )
    return idf

def Read_OutputsEso(CaseName,ZoneOutput):
    #visualization of the results
    eso = esoreader.read_from_path(CaseName+'out.eso')
    ZoneAgregRes = {}
    BuildAgregRes = {}
    #We agregate results per storey
    res ={}
    for idx in eso.dd.variables.keys():
        currentData = eso.dd.variables[idx]
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
    BuildAgregRes['OutdoorSite']= {}
    for nb, key in enumerate(res):
        KeyArea = 'OutdoorSite'
        if 'STOREY' in key:
            numstor= int(key[6:])
            KeyArea= 'NonHeatedArea' if numstor<0 else 'HeatedArea'
        for j, i in enumerate(res[key]):
            ZoneAgregRes[key][i]['GlobData'] = []
            ZoneAgregRes[key][i]['TimeStep'] = res[key][i]['TimeStep']
            ZoneAgregRes[key][i]['Unit'] = res[key][i]['Unit']
            ZoneAgregRes[key][i]['NbNode'] = len(res[key][i]['Data'])
            if res[key][i]['Unit'] in {'C'}: #then lets compute the mean, if not lets sum it
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
                if res[key][i]['Unit'] in {'C'}:
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
    fname = CaseName+'tbl.htm'
    filehandle = open(fname, 'r',encoding='latin-1').read() # get a file handle to the html file
    htables = readhtml.titletable(filehandle)
    Res = {}
    # Res['EPlusTotArea'] = htables[2][1][1][1]
    # Res['EPlusHeatArea'] = htables[2][1][2][1]
    # Res['EPlusNonHeatArea'] = htables[2][1][3][1]
    #Res['EnergyConsKey'] = htables[3][1][0]
    Res['EnergyConsVal'] = htables[3][1][-1]
    fname = CaseName+'out.end'
    Endsinfo = open(fname, 'r', encoding='latin-1').read()
    return Res, Endsinfo

if __name__ == '__main__' :
    print('Set_Outputs Main')

