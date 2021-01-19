import pickle
import matplotlib.pyplot as plt
from matplotlib import gridspec
import os, sys
#add the required path
path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)
from geomeppy import IDF

def GetData(path):
    os.chdir(path)
    liste = os.listdir()
    zone1 = {}
    SimNumb = []
    print('reading file...')
    for i in liste:
        if '.pickle' in i:
            with open(i, 'rb') as handle:
                SimNumb.append(int(i[i.index('v')+1:i.index('.')]))
                zone1[SimNumb[-1]] = pickle.load(handle)
    elec1 = []
    heat1 = []
    cool1 = []
    tot1 = []
    nbbuild = []
    EPC_elec = []
    EPC_Heat = []
    EPC_Cool = []
    EPC_Tot = []
    TotalPower = {}
    EPareas1 =[]
    DBareas = []
    EnergieTot = []
    EnvLeak = []
    Dist = []
    WWR = []
    print('organizing data...')
    for i,key in enumerate(zone1):
        elec1.append(zone1[key]['EnergyConsVal'][1]/3.6/zone1[key]['EPlusHeatArea']*1000) #convert GJ in kWh/m2
        cool1.append(zone1[key]['EnergyConsVal'][4]/3.6/zone1[key]['EPlusHeatArea']*1000)
        heat1.append(zone1[key]['EnergyConsVal'][5]/3.6/zone1[key]['EPlusHeatArea']*1000)
        tot1.append((zone1[key]['EnergyConsVal'][1]+zone1[key]['EnergyConsVal'][4]+zone1[key]['EnergyConsVal'][5])/3.6/zone1[key]['EPlusHeatArea']*1000) #to have GJ into kWh/m2
        eleval = 0
        val = zone1[key]['BuildDB']
        for x in val.EPCMeters['ElecLoad']:
            if val.EPCMeters['ElecLoad'][x]:
                eleval += val.EPCMeters['ElecLoad'][x]
        EPC_elec.append(eleval/zone1[key]['EPlusHeatArea'])
        heatval = 0
        for x in val.EPCMeters['Heating']:
            heatval += val.EPCMeters['Heating'][x]
        EPC_Heat.append(heatval/zone1[key]['EPlusHeatArea'])
        coolval = 0
        for x in val.EPCMeters['Cooling']:
            coolval += val.EPCMeters['Cooling'][x]
        EPC_Cool.append(coolval/zone1[key]['EPlusHeatArea'])
        EPC_Tot.append((eleval+heatval+coolval)/zone1[key]['EPlusHeatArea'])
        EPareas1.append(zone1[key]['EPlusHeatArea'])
        DBareas.append(val.surface)
        TotalPower[key] = [zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'][i] +
                          zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'][i] +
                          zone1[key]['HeatedArea']['Data_Electric Equipment Total Heating Rate'][i]
                          for i in range(len(zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate']))]
        EnergieTot.append(sum(TotalPower[key])/1000/zone1[key]['EPlusHeatArea'])
        nbbuild.append(key)
        EnvLeak.append(val.EnvLeak)
        WWR.append(val.wwr)
        Dist.append(val.MaxShadingDist)
    return {'elec1' : elec1,
            'heat1' : heat1,
            'cool1' : cool1,
            'tot1' : tot1,
            'nbbuild' : nbbuild,
            'EPC_elec' : EPC_elec,
            'EPC_Heat': EPC_Heat,
            'EPC_Cool': EPC_Cool,
            'EPC_Tot': EPC_Tot,
            'EnvLeak' : EnvLeak,
            'Dist' : Dist,
            'WWR' : WWR,
            'SimNumb' :SimNumb,
            }

def GetSingleSim(path,buildList=[]):
    os.chdir(path)
    if not buildList:
        liste = os.listdir()
    else:
        liste = [buildList]
    zone1 = {}
    SimNumb = []
    print('reading file...')
    for i in liste:
        if '.pickle' in i:
            with open(i, 'rb') as handle:
                try:
                    num = int(i[i.index('v') + 1:i.index('.')])
                except:
                    num = int(i[i.index('_') + 1:i.index('.')])
                SimNumb.append(num)
                zone1[SimNumb[-1]] = pickle.load(handle)
    print('organizing data...')
    if len(zone1)>1:
        print('Sorry, ti seems that there are at least 2 simulation results file in this path...')
    else:
        Res = {}
        toget = ['HeatedArea','NonHeatedArea','OutdoorSite']
        for key in zone1:
            for key1 in zone1[key]:
                if key1 in toget:
                    Res[key1] = zone1[key][key1]
    return Res

def createDualFig():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:-1, 0])
    ax0.grid()
    ax1 = plt.subplot(gs[-1, 0])
    ax1.grid()
    plt.tight_layout()
    return {'fig_name' : fig_name, 'ax0': ax0, 'ax1' : ax1}

def createSimpleFig():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:, 0])
    ax0.grid()
    plt.tight_layout()
    return {'fig_name' : fig_name, 'ax0': ax0}


def plotResBase(fig_name,ax0,varx,vary,varxname,varyname,title):
    plt.figure(fig_name)
    ax0.plot(varx, vary,'.',label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()
    plt.title(title)

def plotRelRes(fig_name,ax0,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    relval = [vary[i] / max(vary) for i in range(len(vary))]
    ax0.plot(varx, relval,'.',label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()
    print(min(relval))

def plotAdimRes(fig_name,ax0,varx,vary,varxname,varyname,varname):
    plt.figure(fig_name)
    xval = [(varx[i] -min(varx)) / (max(varx)-min(varx)) for i in range(len(varx))]
    yval = [(vary[i] - min(vary)) / (max(vary) - min(vary)) for i in range(len(vary))]
    ax0.plot(xval, yval,'.',label= varname)
    ax0.set_xlabel(varxname)
    ax0.set_ylabel(varyname)
    ax0.legend()

def plotRes(fig_name,ax0,ax1,varx,vary1,vary2,varxname,vary1name,vary2name):
    plt.figure(fig_name)
    ax0.plot(varx, vary1, 's',label= vary1name)
    ax0.plot(varx, vary2, 'x',label= vary2name)
    ax0.legend()
    ax0.set_xlabel(varxname)
    ax1.plot(varx, [(vary1[i] - vary2[i]) / vary1[i] * 100 for i in range(len(vary1))], 'x')

def SignaturePlots(data):
    plt.figure()
    posy = -1
    gs = gridspec.GridSpec(int(len(data)**0.5)+1, round(len(data)**0.5))
    for i,key in enumerate(data):
        posx = i%(int(len(data)**0.5)+1) # if i<=int(len(zone1)/2) else int(len(zone1)/2)
        if posx==0:
            posy += 1# i%(round(len(zone1)/2)) #0 if posx<int(len(zone1)/2) else i-posx
        ax0 = plt.subplot(gs[posx, posy])
        ax0.plot(data[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],data[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'],'.')
        ax0.plot(data[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 data[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'],'.')
        ax0.plot(data[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 data[key]['HeatedArea']['Data_Zone Ideal Loads Heat Recovery Total Heating Rate'],'.')
        ax0.plot(data[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 data[key]['HeatedArea']['Data_Zone Ideal Loads Heat Recovery Total Cooling Rate'],'.')
        plt.title('Building_'+str(key))

def DistAnalyse(mainPath):
    NewFig = createSimpleFig()
    for i in range(5, 28):
        path = mainPath + str(
            i) + '\\Sim_Results\\'
        Res = GetData(path)
        plotRelRes(NewFig['fig_name'].number, NewFig['ax0'], Res['Dist'], Res['heat1'], 'Shading Distance (m)', 'Building_' + str(i))
        Dist50 = [x for x, val in enumerate(Res['Dist']) if val < 50]
        minDist = Res['Dist'].index(min(Res['Dist']))
        maxDist = Res['Dist'].index(max(Res['Dist']))
        path2idf = mainPath + str(
            i) + '\\'
        print('For Building_'+str(i)+' : Mini is sim_'+str(Res['heat1'][minDist])+ ' / Maxi is sim_'+str(Res['heat1'][maxDist]))
        print('For Building_' + str(i) + ' : increasing dist leads to:' + str(Res['tot1'][minDist]-
            Res['tot1'][maxDist])+ 'of kWh/m2 of differences')
        epluspath = 'C:\\EnergyPlusV9-1-0\\'
        IDF.setiddname(epluspath + "Energy+.idd")
        idf = IDF(path2idf + 'Building_'+str(i)+'v'+str(Res['SimNumb'][minDist])+'.idf')
        #idf.view_model(test=False)


def wwrLeakAnalyse(path):
    Res = GetData(path)
    NewFig = createSimpleFig()
    plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['WWR'], Res['EnvLeak'], 'Window Wall Ratio (-)', 'Env Leak (l/s/m2 for 50Pa)','')
    range = [0.1,0.9 ]
    Res = Datafilter(Res, 'WWR', range)
    plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['WWR'], Res['EnvLeak'], 'Window Wall Ratio (-)','Env Leak (l/s/m2 for 50Pa)','')
    # fig_name, ax0, ax1 = createDualFig()
    # plotRes(fig_name.number,ax0,ax1,Res['EnvLeak'],Res['tot1'],Res['EPC_Tot'],'EnvLeak','Total Sim (kW/m2)','Total Mes (kW/m2)')
    # fig_name, ax0, ax1 = createDualFig()
    # plotRes(fig_name.number,ax0,ax1,Res['WWR'], Res['tot1'], Res['EPC_Tot'], 'WWR', 'Total Sim (kW/m2)', 'Total Mes (kW/m2)')
    NewFig = createSimpleFig()
    plotAdimRes(NewFig['fig_name'].number, NewFig['ax0'], Res['EnvLeak'], Res['tot1'], 'Normalized Parameter (-)', 'Normalized Heat needs (-)','Ext Env Leak [0.2,2]')
    plotAdimRes(NewFig['fig_name'].number, NewFig['ax0'], Res['WWR'], Res['tot1'], 'Normalized Parameter (-)', 'Normalized Heat needs (-)','Window Wall Ratio' +str(range))
    NewFig = createSimpleFig()
    plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['EnvLeak'], Res['tot1'], 'Env Leak (l/s/m2 for 50Pa)',
                'Total needs (kWh/m2)','')
    NewFig = createSimpleFig()
    plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['WWR'], Res['tot1'], 'Window Wall Ratio (-)', 'Total needs (kWh/m2)','')


def Datafilter(Data, Var, range):
    NewSet = {}
    for key in Data:
        NewSet[key] = [val for i,val in enumerate(Data[key]) if Data[Var][i]<range[1] and Data[Var][i]>range[0]]
    return NewSet

def DynAnalyse(path,BuildList = []):
    liste2load = path
    if len(liste2load)==1 and BuildList:
        liste2load = BuildList
        currentpath = path[0]
    for i,current_val in enumerate(liste2load):
        if len(BuildList)<2:
            Res = GetSingleSim(current_val,BuildList[0] if BuildList else [])
        else:
            Res = GetSingleSim(currentpath, current_val)
        if i==0:
            NewFig ={}
        for key in Res:
            if i==0:
                NewFig[key] = {}
            for key1 in Res[key]:
                if 'Data_' in key1:
                    if i==0:
                        NewFig[key][key1] = createSimpleFig()
                    plotResBase(NewFig[key][key1]['fig_name'].number, NewFig[key][key1]['ax0'], [i for i in range(0,len(Res[key][key1]))], Res[key][key1], 'Time', key1,key)

def DynAnalyseUnity(path,BuildList = []):
    liste2load = path
    if len(liste2load)==1 and BuildList:
        liste2load = BuildList
        currentpath = path[0]
    for i,current_val in enumerate(liste2load):
        if len(BuildList)<2:
            Res = GetSingleSim(current_val,BuildList[0] if BuildList else [])
        else:
            Res = GetSingleSim(currentpath, current_val)
        if i==0:
            NewFig ={}
        for key in Res:
            # if i==0:
            #     NewFig[key] = {}
            for key1 in Res[key]:
                if 'Data_' in key1:
                    DataLabel = key1[len('Data_'):]
                    Unit = Res[key]['Unit_' + DataLabel]
                    new = True
                    for key2 in NewFig:
                        if Unit in key2:
                            currentfig = NewFig[key2]
                            new = False
                    if new:
                        NewFig[Unit] = createSimpleFig()
                        currentfig = NewFig[Unit]
                    plotResBase(currentfig['fig_name'].number, currentfig['ax0'], [i for i in range(0,len(Res[key][key1]))], Res[key][key1], 'Time', DataLabel,Unit)

def OccupancyAnalyses(path):
    for i,current_path in enumerate(path):
        Res = GetData(current_path)
        if i==0:
            NewFig = createSimpleFig()
        plotRelRes(NewFig['fig_name'].number, NewFig['ax0'], Res['nbbuild'], Res['tot1'], 'Number of run (-)',
                    'Reduction factor of total needs (-)')
        #DynAnalyse([current_path],BuildList=['Building_10v0.pickle','Building_10v1.pickle'])

if __name__ == '__main__' :
    path = ['C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles10\\Sim_Results\\']
    #path = ['C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\LeakWWR\\CaseFiles7\\Sim_Results\\']
    #path = ['C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\DistShadingWWR03\\CaseFiles8\\Sim_Results\\']

    #this is to plot time series of all variables
    #path = ['C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles\\Sim_Results\\']
    #path.append('C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles1zoneperstoreyExtIns\\Sim_Results\\')
    #path.append('C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFilesIntIns\\Sim_Results\\')
    #path.append('C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles1zoneperstoreyExtIns05mWall\\Sim_Results\\')
    #DynAnalyseUnity(path,BuildList=['Building_11.pickle'])

    #OccupancyAnalyses(path)

    #this is to plot results from LHC sampling for the three building 7, 9 and 13 from now
    wwrLeakAnalyse(path[0])
    path = ['C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\DistShadingWWR03\\CaseFiles']
    # this is to plot results shading distance simulation in DistShading folder
    #DistAnalyse(path[0])
    plt.show()