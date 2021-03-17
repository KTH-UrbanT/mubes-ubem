# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import pickle
import matplotlib.pyplot as plt
from matplotlib import gridspec
import numpy as np
import os, sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)
sys.path.append("..")
from DataBase import DB_Building
from geomeppy import IDF

def GetData(path):
    os.chdir(path)
    liste = os.listdir()
    ResBld = {}
    SimNumb = []
    ErrFiles = []
    print('reading file...')
    for i in liste:
        if '.pickle' in i:
            with open(i, 'rb') as handle:
                try:
                    num = int(i[i.index('_') + 1:i.index('v')])
                except:
                    num = int(i[i.index('_') + 1:i.index('.')])
                SimNumb.append(num)
                ResBld[SimNumb[-1]] = pickle.load(handle)
            try:
                ErrFiles.append(os.path.getsize(i[:i.index('.pickle')]+'.err'))
            except:
                ErrFiles.append(0)

    variables=['elec','heat','cool','tot','nbbuild','EPC_elec','EPC_Heat','EPC_Cool','EPC_Tot',
               'DBareas','EnergieTot','EnvLeak','Dist','WWR','IntMass','ExtMass','ExtIns','TempOP27',
               'PowerPic','MaxPowDay','EPareas1']

    Res = {}
    for key in variables:
        Res[key] = []

    print('organizing data...')
    for i,key in enumerate(ResBld):
        Res['elec'].append(ResBld[key]['EnergyConsVal'][1]/3.6/ResBld[key]['EPlusHeatArea']*1000) #convert GJ in kWh/m2
        Res['cool'].append(ResBld[key]['EnergyConsVal'][4]/3.6/ResBld[key]['EPlusHeatArea']*1000)
        Res['heat'].append(ResBld[key]['EnergyConsVal'][5]/3.6/ResBld[key]['EPlusHeatArea']*1000)
        Res['tot'].append((ResBld[key]['EnergyConsVal'][1]+ResBld[key]['EnergyConsVal'][4]+ResBld[key]['EnergyConsVal'][5])/3.6/ResBld[key]['EPlusHeatArea']*1000) #to have GJ into kWh/m2
        eleval = 0
        val = ResBld[key]['BuildDB']
        for x in val.EPCMeters['ElecLoad']:
            if val.EPCMeters['ElecLoad'][x]:
                eleval += val.EPCMeters['ElecLoad'][x]
        Res['EPC_elec'].append(eleval/ResBld[key]['EPlusHeatArea'])
        heatval = 0
        for x in val.EPCMeters['Heating']:
            heatval += val.EPCMeters['Heating'][x]
        Res['EPC_Heat'].append(heatval/ResBld[key]['EPlusHeatArea'])
        coolval = 0
        for x in val.EPCMeters['Cooling']:
            coolval += val.EPCMeters['Cooling'][x]
        Res['EPC_Cool'].append(coolval/ResBld[key]['EPlusHeatArea'])
        Res['EPC_Tot'].append((eleval+heatval+coolval)/ResBld[key]['EPlusHeatArea'])
        Res['EPareas1'].append(ResBld[key]['EPlusHeatArea'])
        Res['DBareas'].append(val.surface)

        try:
            TotalPower[key] = [ResBld[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'][i] +
                          ResBld[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'][i] +
                          ResBld[key]['HeatedArea']['Data_Electric Equipment Total Heating Rate'][i]
                          for i in range(len(ResBld[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate']))]
            Res['EnergieTot'].append(sum(TotalPower[key])/1000/ResBld[key]['EPlusHeatArea'])
        except:
            pass
        Res['IntMass'].append(val.InternalMass['HeatedZoneIntMass']['WeightperZoneArea'])
        Res['ExtMass'].append(val.Materials['Wall Inertia']['Thickness'])
        Res['ExtIns'].append(val.ExternalInsulation)
        Res['nbbuild'].append(key)
        Res['EnvLeak'].append(val.EnvLeak)
        Res['WWR'].append(val.wwr)
        Res['Dist'].append(val.MaxShadingDist)
        #TempOP = ResBld[key]['HeatedArea']['Data_Zone Operative Temperature']
        #Res['TempOP27'].append(len([i for i in TempOP if i > 27]))
        Pow = ResBld[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate']
        Pow = [i/1000 for i in Pow]
        Res['PowerPic'].append(max(Pow))
        var = np.array(Pow)
        Res['MaxPowDay'].append(Pow.index(max(Pow))/24)
        var = var.reshape(365,24,1)
        if i ==0 :
            Powjr = var
        else:
            Powjr = np.append(Powjr,var,axis = 2)
        #var = np.array(ResBld[key]['HeatedArea']['Data_Zone Operative Temperature'])
        var = var.reshape(365, 24, 1)
        if i == 0:
            TempInt = var
        else:
            TempInt = np.append(TempInt, var, axis=2)
    Res['TempInt'] = TempInt
    Res['TempExt'] = ResBld[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature']
    return Res

def GetSingleSim(path,buildList=[]):
    os.chdir(path)
    if not buildList:
        liste = os.listdir()
    else:
        liste = [buildList]
    ResBld = {}
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
                ResBld[SimNumb[-1]] = pickle.load(handle)
    print('organizing data...')
    if len(ResBld)>1:
        print('Sorry, ti seems that there are at least 2 simulation results file in this path...')
    else:
        Res = {}
        toget = ['HeatedArea','NonHeatedArea','OutdoorSite']
        for key in ResBld:
            for key1 in ResBld[key]:
                if key1 in toget:
                    Res[key1] = ResBld[key][key1]
    return Res

def createDualFig(title):
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:-1, 0])
    ax0.grid()
    ax1 = plt.subplot(gs[-1, 0])
    ax1.grid()
    plt.tight_layout()
    plt.title(title)
    return {'fig_name' : fig_name, 'ax0': ax0, 'ax1' : ax1}

def createSimpleFig():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:, 0])
    ax0.grid()
    plt.tight_layout()
    return {'fig_name' : fig_name, 'ax0': ax0}


def plotResBase(fig_name,ax0,varx,vary,varxname,varyname,title,sign):
    plt.figure(fig_name)
    ax0.plot(varx, vary,sign,label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()
    plt.title(title)

def plotRelRes(fig_name,ax0,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    relval = [vary[i] / max(vary) for i in range(len(vary))]
    ax0.plot(varx, relval,label= varyname)
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

def plotRes(fig_name,ax0,ax1,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    for id,xvar in enumerate(vary):
        ax0.plot(varx, vary[id], 's',label= varyname[id])
    ax0.legend()
    ax0.set_xlabel(varxname)
    for id,xvar in enumerate(vary):
        ax1.plot(varx, [(vary[id][i] - vary[0][i]) / vary[0][i] * 100 for i in range(len(vary[0]))], 'x')

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
    Res = GetData(path[0])
    NewFig = createSimpleFig()
    plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['EnvLeak'], Res['PowerPic'], 'Env Leak (l/s/m2 for 50Pa)', 'PowerPic','','.')

    plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['EnvLeak'], Res['PowerPic'], 'Env Leak (l/s/m2 for 50Pa)', 'PowerPic','','o')
    # fig_name, ax0, ax1 = createDualFig()
    # plotRes(fig_name.number,ax0,ax1,Res['EnvLeak'],Res['tot1'],Res['EPC_Tot'],'EnvLeak','Total Sim (kW/m2)','Total Mes (kW/m2)')
    # fig_name, ax0, ax1 = createDualFig()
    # plotRes(fig_name.number,ax0,ax1,Res['WWR'], Res['tot1'], Res['EPC_Tot'], 'WWR', 'Total Sim (kW/m2)', 'Total Mes (kW/m2)')
    # NewFig = createSimpleFig()
    # plotAdimRes(NewFig['fig_name'].number, NewFig['ax0'], Res['EnvLeak'], Res['tot1'], 'Normalized Parameter (-)', 'Normalized Heat needs (-)','Ext Env Leak' + str(evlerange))
    # plotAdimRes(NewFig['fig_name'].number, NewFig['ax0'], Res['WWR'], Res['tot1'], 'Normalized Parameter (-)', 'Normalized Heat needs (-)','Window Wall Ratio' +str(wwrrange))
    # NewFig = createSimpleFig()
    # plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['EnvLeak'], Res['tot1'], 'Env Leak (l/s/m2 for 50Pa)',
    #             'Total needs (kWh/m2)','')
    # NewFig = createSimpleFig()
    # plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res['WWR'], Res['tot1'], 'Window Wall Ratio (-)', 'Total needs (kWh/m2)','')


def Datafilter(Data, Var, range):
    NewSet = {}
    for key in Data:
        if 'TempExt'not in key:
            if len(np.shape(Data[key]))==1:
                NewSet[key] = [val for i,val in enumerate(Data[key]) if Data[Var][i]<=range[1] and Data[Var][i]>=range[0]]
            else:
                idx = [i for i,val in enumerate(Data[Var]) if val<= range[1] and val>= range[0]]
                NewSet[key] = np.array(Data[key][:,:,idx])
        else:
            NewSet[key] = Data[key]
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
                    plotResBase(NewFig[key][key1]['fig_name'].number, NewFig[key][key1]['ax0'], [i for i in range(0,len(Res[key][key1]))], Res[key][key1], 'Time', key1,key,'-')

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

def GlobRes(path):
    Res= {}
    tot=[]
    heat = []
    elec = []
    varyname = ['CsteLoad','SummerW3','SummerW5','WinterW3','WinterW5',]
    for id,curPath in enumerate(path):
        Res[id] = GetData(curPath)
        tot.append(Res[id]['tot1'])
        heat.append(Res[id]['heat1'])
        elec.append(Res[id]['elec1'])
        cas = curPath[::-1]
        cas = cas[cas.index('\\')+2:]
        #varyname.append(cas[:cas.index('\\')][::-1])
    FigName = createDualFig('Total Needs')
    plotRes(FigName['fig_name'].number, FigName['ax0'], FigName['ax1'], Res[0]['nbbuild'], tot, 'Nb Build', varyname)
    FigName = createDualFig('')
    plotRes(FigName['fig_name'].number, FigName['ax0'], FigName['ax1'], Res[0]['nbbuild'], heat, 'Nb Build', varyname)
    FigName = createDualFig('Elec Loads')
    plotRes(FigName['fig_name'].number, FigName['ax0'], FigName['ax1'], Res[0]['nbbuild'], elec, 'Nb Build', varyname)



def InertiaAnalyses(path,keyword):
    for i,current_path in enumerate(path):
        Res = GetData(current_path)
        bounds = [0, 150]
        Res = Datafilter(Res, 'IntMass', bounds)
        bounds = [0.5, 1]
        Res1 = Datafilter(Res, 'ExtIns', bounds)
        bounds = [0, 0.5]
        Res2 = Datafilter(Res, 'ExtIns', bounds)

        idx = Res1[keyword].index(min(Res1[keyword]))
        var = Res1['TempInt'][:, :, idx]
        TempIntmMExtIns = var.reshape(8760,1)
        PmassminiExtIns = Res1['Powjr'][:, :, idx]
        PmassminExtIns = PmassminiExtIns.reshape(8760, 1)
        idx = Res1[keyword].index(max(Res1[keyword]))
        var = Res1['TempInt'][:, :, idx]
        TempIntMMExtIns = var.reshape(8760, 1)
        PmassmaxiExtIns = Res1['Powjr'][:, :, idx]
        PmassmaxExtIns = PmassmaxiExtIns.reshape(8760, 1)
        EcartPmassExtIns = [(-pi+PmassmaxExtIns[idx]) for idx,pi in enumerate(PmassminExtIns)]
        idx = Res2[keyword].index(min(Res2[keyword]))
        var = Res2['TempInt'][:, :, idx]
        TempIntmMIntIns = var.reshape(8760, 1)
        PmassminiIntIns = Res2['Powjr'][:, :, idx]
        PmassminIntIns = PmassminiIntIns.reshape(8760, 1)
        idx = Res2[keyword].index(max(Res2[keyword]))
        var = Res2['TempInt'][:, :, idx]
        TempIntMMIntIns = var.reshape(8760, 1)
        PmassmaxiIntIns = Res2['Powjr'][:, :, idx]
        PmassmaxIntIns = PmassmaxiIntIns.reshape(8760, 1)
        EcartPmassIntIns = [(-pi + PmassmaxIntIns[idx]) for idx, pi in enumerate(PmassminIntIns)]

        fig = plt.figure()
        plt.title('Power analyses (kW)')
        gs = gridspec.GridSpec(3, 1)
        ax1 = plt.subplot(gs[0, 0])
        ax1.grid()
        ax1.plot([hr for hr in range(8760)],PmassmaxExtIns,label='P MMass ExtIns')
        ax1.plot([hr for hr in range(8760)], PmassminExtIns, label='P mMass Ext Ins')
        ax1.plot([hr for hr in range(8760)], PmassmaxIntIns, label='P MMass IntIns')
        ax1.plot([hr for hr in range(8760)], PmassminIntIns, label='P mMass Int Ins')
        ax1.set_ylabel('kW')
        ax1.legend()
        ax0 = plt.subplot(gs[1, 0],sharex=ax1)
        ax0.grid()
        ax0.plot([hr for hr in range(8760)], EcartPmassExtIns, label='P (M-m)Mass ExtIns')
        ax0.plot([hr for hr in range(8760)], EcartPmassIntIns, label='P (M-m)Mass Int Ins')
        ax0.legend()
        ax0.set_ylabel('kW')
        ax0 = plt.subplot(gs[2, 0], sharex=ax1)
        ax0.grid()
        ax0.plot([hr for hr in range(8760)], TempIntMMExtIns, label='int Temp MMass ExtIns')
        ax0.plot([hr for hr in range(8760)], TempIntmMExtIns, label='int Temp mMass ExtIns')
        ax0.plot([hr for hr in range(8760)], TempIntMMIntIns, label='int Temp MMass IntIns')
        ax0.plot([hr for hr in range(8760)], TempIntmMIntIns, label='int Temp mMass IntIns')
        ax0.plot([hr for hr in range(8760)], Res['TempExt'], label='Ext Temp')
        ax0.legend()
        ax0.set_ylabel('deg C')
        ax0.set_xlabel('Time (hr)')
        plt.figure()
        plt.title('Cumulative difference cumsum(M-m) (kWh)')
        plt.grid()
        plt.plot([hr for hr in range(8760)], np.cumsum(EcartPmassExtIns), label='P (M-m)Mass ExtIns')
        plt.plot([hr for hr in range(8760)], np.cumsum(EcartPmassIntIns), label='P (M-m)Mass Int Ins')
        plt.legend()
        plt.xlabel('Time (hr)')
        plt.ylabel('kWh')
        plt.figure()
        plt.title('Pow difference vers ExtTemp')
        plt.grid()
        plt.plot(Res['TempExt'], EcartPmassExtIns,'.', label='P (M-m)Mass ExtIns')
        plt.plot(Res['TempExt'], EcartPmassIntIns,'.', label='P (M-m)Mass Int Ins')
        plt.legend()
        plt.xlabel('Ext Temp')
        plt.ylabel('kWh')

        Dist =[]
        for k in range(len(Res1['Powjr'][1, :, 1])):
            distrib = [(Res1['Powjr'][26, k, j]-np.mean(Res1['Powjr'][26, k, :])) for j in range(len(Res1['Powjr'][26,k, :]))]
            Dist.append(np.std(distrib))
        Distrib = createSimpleFig()
        plotResBase(Distrib['fig_name'].number, Distrib['ax0'], [hr for hr in range(24)], Dist, keyword + ' (m)',
                    'Standard deviation Ext Ins (W)', keyword + '_Impact')
        Dist = []
        for k in range(len(Res2['Powjr'][1, :, 1])):
            distrib = [(Res2['Powjr'][26, k, j] - np.mean(Res2['Powjr'][26, k, :])) for j in
                       range(len(Res2['Powjr'][26, k, :]))]
            Dist.append(np.std(distrib))
        plotResBase(Distrib['fig_name'].number, Distrib['ax0'],  [hr for hr in range(24)], Dist, keyword + ' (m)',
                    'Standard deviation Int Ins (W)', keyword + '_Impact')

        if i==0:
            NewFig = createSimpleFig()
        plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res1[keyword], Res1['heat1'], keyword+' (m)',
                    'HeatNeeds Ext Ins (kW/m2)',keyword+'_Impact')
        plotResBase(NewFig['fig_name'].number, NewFig['ax0'], Res2[keyword], Res2['heat1'], keyword + ' (m)',
                    'HeatNeeds Int Ins (kW/m2)', keyword + '_Impact')
        if i==0:
            NewFig1 = createSimpleFig()
        plotResBase(NewFig1['fig_name'].number, NewFig1['ax0'], Res1[keyword], Res1['ErrFiles'],
                    keyword+' (kg/m2)',
                    'ErrFile size', 'Error Files')
        plotResBase(NewFig1['fig_name'].number, NewFig1['ax0'], Res2[keyword], Res2['ErrFiles'],
                    keyword + ' (kg/m2)',
                    'ErrFile size', 'Error Files')
        if i==0:
            NewFig2 = createSimpleFig()
        plotResBase(NewFig2['fig_name'].number, NewFig2['ax0'], Res1['nbbuild'], Res1['heat1'],
                    keyword+' (m)',
                    'heat1', 'Error Files')
        plotResBase(NewFig2['fig_name'].number, NewFig2['ax0'], Res2['nbbuild'], Res2['heat1'],
                    keyword + ' (m)',
                    'heat1', 'Error Files')
        if i==0:
            NewFig3 = createSimpleFig()
        plotResBase(NewFig2['fig_name'].number, NewFig3['ax0'], Res1[keyword], Res1['TempOP27'],
                    keyword+' (m)',
                    'OP Temp > 27 Ext Ins (hr)', 'Error Files')
        plotResBase(NewFig3['fig_name'].number, NewFig3['ax0'], Res2[keyword], Res2['TempOP27'],
                    keyword + ' (m)',
                    'OP Temp > 27 Int Ins (hr)', 'nb hours with Temp OP above 27')
        if i==0:
            NewFig4 = createSimpleFig()
        plotResBase(NewFig4['fig_name'].number, NewFig4['ax0'], Res1[keyword], Res1['PowerPic'],
                    keyword+' (m)',
                    'Maximum Pic Power Ext Ins (kW)', 'Temp')
        plotResBase(NewFig4['fig_name'].number, NewFig4['ax0'], Res2[keyword], Res2['PowerPic'],
                    keyword + ' (m)',
                    'Maximum Pic Power Int Ins (kW)', 'Maximum Pic Power')

if __name__ == '__main__' :

    #the main idea of this file is to present some way for analyzing the data.
    #some usful function are implemented such as agregating the data from several simulation in one disctionary
    #this enable to make easy plots of variables over others.
    #some generic function to create figure and make plots are also available.
    #but specific function are to be created for specific anaylses. some are left as example but they might not be
    # compatible with other simulations than the one they were created for.
    # some propose plot for timeseries with overplots of other specific cases while other function enable to plot not timedependent variables
    #the ain paradigm is to give the path or a list of path and data are gathered in one element

    mainpath = os.getcwd()
    path = [mainpath + os.path.normcase('/Archi2D1zoneperBloc/Sim_Results')]
    path.append(mainpath + os.path.normcase('/Archi2D1zoneperFloor/Sim_Results'))



    Res = {}
    for id, curPath in enumerate(path):
        Res[id] = GetData(curPath)
    DynAnalyse(path, ['Building_7v0.pickle'])

# available functions
    #wwrLeakAnalyse(path)
    #DynAnalyse(path,['Building_6v0.pickle','Building_5v0.pickle'])#,'Building_7v0.pickle','Building_8v0.pickle','Building_9v0.pickle'])
    #GlobRes(path[0])
    #DynAnalyse(path, BuildList=['Building_5.pickle'])
    #DynAnalyseUnity(path,BuildList=['Building_10v0.pickle','Building_10v1.pickle'])
    #DynAnalyseUnity(path,BuildList=['Building_11.pickle'])
    #InertiaAnalyses(path,'IntMass')
    #OccupancyAnalyses(path)
    # this is to plot results shading distance simulation in DistShading folder
    #DistAnalyse(path[0])

    plt.show()