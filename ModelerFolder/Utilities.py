#this file is just a tank of utilities for ploting stuff mainly.
#It creates the figures and the plots
import os
import pickle
import matplotlib.pyplot as plt
from matplotlib import gridspec


def CountAbovethreshold(Data,threshold):
    #give the length of data above a threshold, for hourly Data, it is number of Hrs above the threshold
    return len([i for i in Data if i > threshold])

def DailyVal(Data):
    #inputs needs to be hourly value avor a full year (8760 values)
    #give time series in a daily distribution (365 value of 24 hours
    DailyMax = []
    DailyMin = []
    var = np.array(Data)
    var.reshape(365, 24, 1)
    for i in var[:,0,0]:
        DailyMax.append(max(i))
        DailyMin.append(min(i))
        if i==0:
            DailyDistrib = var
        else:
            DailyDistrib = np.append(DailyDistrib, var, axis=2)
    return {'DailyMax': DailyMax, 'DailyMin' : DailyMin, 'DailyDistrib': DailyDistrib}

def getSortedIdx(reference,Data):
    #return the index order for sake of comparison two different simulation with different buildong order
    #was necesseray to make comparison between several geojson file of the same district.
    #both input are time series, the outputs are the indexes of Data that matches with reference index
    #for example, it was used with FormularId as reference key
    index_y = []
    varx = []
    reference = [val for val in reference if val !=None]
    for idx1, valref in enumerate(reference):
        if valref!=None:
            for idx2, locval in enumerate(Data):
                if valref == locval and locval!=None:
                    index_y.append(idx2)
                    varx.append(idx1)
    return index_y,varx

#this function enable to create a two subplots figure with ratio definition between the two plots
def createDualFig(title,ratio):
    fig_name = plt.figure()
    gs = gridspec.GridSpec(10,1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:round(ratio*10), 0])
    ax0.grid()
    ax1 = plt.subplot(gs[round(ratio*10)+1:, 0])
    ax1.grid()
    ax1.sharex(ax0)
    #plt.tight_layout()
    plt.title(title)
    return {'fig_name' : fig_name, 'ax0': ax0, 'ax1' : ax1}

#this function enable to create a two subplots figure with ratio definition between the two plots
def createMultilFig(title,nbFig,linked=True):
    fig_name = plt.figure()
    gs = gridspec.GridSpec(nbFig,1, left=0.1, bottom = 0.1)
    ax = {}
    for i in range(nbFig):
        ax[i] = plt.subplot(gs[i, 0])
        ax[i].grid()
        if i>0 and linked:
            ax[i].sharex(ax[0])
    #plt.tight_layout()
    plt.title(title)
    return {'fig_name' : fig_name, 'ax': ax}

#this function enable to create a single graph areas
def createSimpleFig():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:, 0])
    ax0.grid()
    #plt.tight_layout()
    return {'fig_name' : fig_name, 'ax0': ax0}

#basic plots
def plotBasicGraph(fig_name,ax0,varx,vary,varxname,varyname,title,sign):
    plt.figure(fig_name)
    for nb,var in enumerate(vary):
        ax0.plot(varx,var,sign,label= varyname[nb], mfc='none')
    ax0.set_xlabel(varxname)
    ax0.set_ylabel(title)
    ax0.legend()

#this plots variables realtively to their maximum value
def plotRelative2Max(fig_name,ax0,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    relval = [vary[i] / max(vary) for i in range(len(vary))]
    ax0.plot(varx, relval,label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()
    print(min(relval))

#this plots variables dimensioless values (from 0-1)
def plotDimLess(fig_name,ax0,varx,vary,varxname,varyname,varname):
    plt.figure(fig_name)
    xval = [(varx[i] -min(varx)) / (max(varx)-min(varx)) for i in range(len(varx))]
    yval = [(vary[i] - min(vary)) / (max(vary) - min(vary)) for i in range(len(vary))]
    ax0.plot(xval, yval,'.',label= varname)
    ax0.set_xlabel(varxname)
    ax0.set_ylabel(varyname)
    ax0.legend()

#this plots in 2 subplots basic values and error, vary is thus a list of list, the first one being the reference
def plotBasicWithError(fig_name,ax0,ax1,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    for id,xvar in enumerate(vary):
        ax0.plot(varx, vary[id], 's',label= varyname[id])
    ax0.legend()
    ax0.set_xlabel(varxname)
    for id,xvar in enumerate(vary):
        ax1.plot(varx, [(vary[id][i] - vary[0][i]) / vary[0][i] * 100 for i in range(len(vary[0]))], 'x')

#this one I don't really get it yet...why I have done this....
def plot2Subplots(fig_name,ax0,ax1,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    ax = [ax0,ax1]
    for i in len(varx):
        ax[i].plot(varx[i], vary[i])
        ax[i].set_xlabel(varxname)
        ax[i].set_ylabel(varyname)
        ax[i].grid()

def GetData(path,extravariables = []):
    os.chdir(path)
    liste = os.listdir()
    ResBld = {}
    Res = {}
    SimNumb = []
    Res['ErrFiles'] = []
    print('reading file...')
    #First round just to see what number to get
    StillSearching = True
    num =[]
    idx1 = ['_','v']
    idx2 = ['v','.']
    while StillSearching:
        for i,file in enumerate(liste):
            if '.pickle' in file:
                num.append(int(file[file.index(idx1[0]) + 1:file.index(idx1[1])]))
            if len(num)==2:
                if (num[1]-num[0])>0:
                    idxF = idx1
                else:
                    idxF = idx2
                StillSearching = False
                break
    #now that we found this index, lets go along alll the files
    for file in liste:
        if '.pickle' in file:
            SimNumb.append(int(file[file.index(idxF[0]) + 1:file.index(idxF[1])]))
            with open(file, 'rb') as handle:
                ResBld[SimNumb[-1]] = pickle.load(handle)
            try:
                Res['ErrFiles'].append(os.path.getsize(file[:file.index('.pickle')]+'.err'))
            except:
                Res['ErrFiles'].append(0)

    #lets get the mandatory variables
    variables=['EP_elec','EP_heat','EP_cool','SimNum','EPC_elec','EPC_Heat','EPC_Cool','EPC_Tot',
               'ATemp','EP_Area','BuildID']
    # lest build the Res dictionnary
    for key in variables:
        Res[key] = []
    # #lets add to the extravariable the time series if present
    # TimeSeriesKeys = ['HeatedArea','NonHeatedArea','OutdoorSite']
    # for TimeKey in TimeSeriesKeys:
    #     if TimeKey in ResBld[SimNumb[0]].keys():
    #         extravariables.append(TimeKey)
    #lest add the keysin the Res Dict of the extravariables
    for key in extravariables:
        Res[key] = []
    #now we aggregate the data into Res dict
    print('organizing data...')
    for i,key in enumerate(ResBld):
        Res['SimNum'].append(key)
        #lets first read the attribut of the building object (simulation inputs)
        BuildObj = ResBld[key]['BuildDB']
        Res['BuildID'].append(BuildObj.BuildID)
        Res['EP_Area'].append(BuildObj.EPHeatedArea)
        Res['ATemp'].append(BuildObj.ATemp)
        eleval = 0
        for x in BuildObj.EPCMeters['ElecLoad']:
            if BuildObj.EPCMeters['ElecLoad'][x]:
                eleval += BuildObj.EPCMeters['ElecLoad'][x]
        Res['EPC_elec'].append(eleval/BuildObj.EPHeatedArea)
        heatval = 0
        for x in BuildObj.EPCMeters['Heating']:
            heatval += BuildObj.EPCMeters['Heating'][x]
        Res['EPC_Heat'].append(heatval/BuildObj.EPHeatedArea)
        coolval = 0
        for x in BuildObj.EPCMeters['Cooling']:
            coolval += BuildObj.EPCMeters['Cooling'][x]
        Res['EPC_Cool'].append(coolval/BuildObj.EPHeatedArea)
        Res['EPC_Tot'].append((eleval+heatval+coolval)/BuildObj.EPHeatedArea)

        for key1 in Res:
            if key1 in ['EP_elec','EP_cool','EP_heat']:
                idx = 1 if 'EP_elec' in key1 else 4  if 'EP_cool' in key1 else 5 if 'EP_heat' in key1 else None
                Res[key1].append(ResBld[key]['EnergyConsVal'][idx] / 3.6 / BuildObj.EPHeatedArea * 1000)

        #Now lest get the extravariables
        for key1 in extravariables:
            try:
                Res[key1].append(ResBld[key][key1])
            except:
                try:
                    Res[key1].append(eval('BuildObj.'+key1))
                except:
                    Res[key1].append(-1)

    return Res