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
    # for i,key in enumerate(zone1.keys()):
    #     if i==0:
    #         print('First key :' + str(zone1[key].keys()))
    #         for key1 in zone1[key].keys():
    #             if isinstance(zone1[key][key1],dict):
    #                 keytoprnit = [key for key in zone1[key][key1].keys() if 'Data' in key]
    #                 for nb in keytoprnit:
    #                     print(nb)
    #                 break
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

def createNewFig():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:-1, 0])
    ax0.grid()
    ax1 = plt.subplot(gs[-1, 0])
    ax1.grid()
    plt.tight_layout()
    return fig_name, ax0, ax1

def createNewFig1():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:, 0])
    ax0.grid()
    plt.tight_layout()
    return fig_name, ax0


def plotResBase(fig_name,ax0,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    ax0.plot(varx, vary,'.',label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()

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

def DistAnalyse():
    fig_name, ax0 = createNewFig1()
    for i in range(5, 28):
        path = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\DistShading\\CaseFiles' + str(
            i) + '\\Sim_Results\\'
        Res = GetData(path)
        plotRelRes(fig_name.number, ax0, Res['Dist'], Res['tot1'], 'Dist', 'Building_' + str(i))
        Dist50 = [x for x, val in enumerate(Res['Dist']) if val < 50]
        minDist = Res['Dist'].index(min(Res['Dist']))
        maxDist = Res['Dist'].index(max(Res['Dist']))
        path2idf = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\DistShading\\CaseFiles' + str(
            i) + '\\'
        print('For Building_'+str(i)+' : Mini is sim_'+str(Res['SimNumb'][minDist])+ ' / Maxi is sim_'+str(Res['SimNumb'][maxDist]))
        epluspath = 'C:\\EnergyPlusV9-1-0\\'
        IDF.setiddname(epluspath + "Energy+.idd")
        idf = IDF(path2idf + 'Building_'+str(i)+'v'+str(Res['SimNumb'][maxDist])+'.idf')
        idf.view_model(test=False)

    plt.show()

def wwrLeakAnalyse():
    path = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles13\\Sim_Results\\'
    Res = GetData(path)
    fig_sample, ax0 = createNewFig1()
    plotResBase(fig_sample.number, ax0, Res['WWR'], Res['EnvLeak'], 'Window Wall Ratio (-)', 'Env Leak (l/s/m2 for 50Pa)')
    range = [0.1,0.9 ]
    Res = Datafilter(Res, 'WWR', range)
    plotResBase(fig_sample.number, ax0, Res['WWR'], Res['EnvLeak'], 'Window Wall Ratio (-)','Env Leak (l/s/m2 for 50Pa)')
    # fig_name, ax0, ax1 = createNewFig()
    # plotRes(fig_name.number,ax0,ax1,Res['EnvLeak'],Res['tot1'],Res['EPC_Tot'],'EnvLeak','Total Sim (kW/m2)','Total Mes (kW/m2)')
    # fig_name, ax0, ax1 = createNewFig()
    # plotRes(fig_name.number,ax0,ax1,Res['WWR'], Res['tot1'], Res['EPC_Tot'], 'WWR', 'Total Sim (kW/m2)', 'Total Mes (kW/m2)')
    fig_name, ax0 = createNewFig1()
    plotAdimRes(fig_name.number, ax0, Res['EnvLeak'], Res['tot1'], 'Normalized Parameter (-)', 'Normalized Heat needs (-)','Ext Env Leak [0.2,2]')
    plotAdimRes(fig_name.number, ax0, Res['WWR'], Res['tot1'], 'Normalized Parameter (-)', 'Normalized Heat needs (-)','Window Wall Ratio' +str(range))
    fig_name, ax0 = createNewFig1()
    plotResBase(fig_name.number, ax0, Res['EnvLeak'], Res['tot1'], 'Env Leak (l/s/m2 for 50Pa)',
                'Total needs (kWh/m2)')
    fig_name, ax0 = createNewFig1()
    plotResBase(fig_name.number, ax0, Res['WWR'], Res['tot1'], 'Window Wall Ratio (-)', 'Total needs (kWh/m2)')

    plt.show()

def Datafilter(Data, Var, range):
    NewSet = {}
    for key in Data:
        NewSet[key] = [val for i,val in enumerate(Data[key]) if Data[Var][i]<range[1] and Data[Var][i]>range[0]]
    return NewSet


if __name__ == '__main__' :
    wwrLeakAnalyse()
    #DistAnalyse()
