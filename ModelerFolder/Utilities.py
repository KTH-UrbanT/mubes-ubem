#this file is just a tank of utilities for ploting stuff mainly.
#It creates the figures and the plots
import os
import pickle
import matplotlib.pyplot as plt
from matplotlib import gridspec
import numpy as np


def CountAbovethreshold(Data,threshold):
    #give the length of data above a threshold, for hourly Data, it is number of Hrs above the threshold
    return len([i for i in Data if i > threshold])

def DailyVal(Data):
    #inputs needs to be hourly value avor a full year (8760 values)
    #give time series in a daily distribution (365 value of 24 hours
    DailyMax = []
    DailyMin = []
    var = np.array(Data)
    var = var.reshape(365, 24, 1)
    for i in range(len(var[:,0,0])):
        DailyMax.append(max(var[i,:,0]))
        DailyMin.append(min(var[i,:,0]))
        if i==0:
            DailyDistrib = var[i,:,0]
        else:
            DailyDistrib = np.vstack((DailyDistrib, var[i,:,0]))
    return {'DailyMax': DailyMax, 'DailyMin' : DailyMin, 'DailyDistrib': DailyDistrib}

def getMatchedIndex(Vary1,Vary2,tol):
    Relativerror = [(Vary2[i] - Vary1[i]) / Vary2[i] * 100 for i in range(len(Vary1))]
    GoodIdx = [idx for idx, val in enumerate(Relativerror) if abs(val) <= tol]
    return GoodIdx


#function copy/paste from : https://www.askpython.com/python/examples/principal-component-analysis
def PCA(X, num_var = 6, plot2D = False, plotSphere = False, plotInertia = False):
    n, p = X.shape
    # Step-1
    X_meaned = (X - np.mean(X, axis=0))/np.std(X, axis=0)
    # Step-2
    cov_mat = np.cov(X_meaned, rowvar=False)
    # Step-3
    eigen_values, eigen_vectors = np.linalg.eigh(cov_mat)
    # Step-4
    sorted_index = np.argsort(eigen_values)[::-1]
    sorted_eigenvalue = eigen_values[sorted_index]
    sorted_eigenvectors = eigen_vectors[:, sorted_index]
    Inertia = [val/sum(sorted_eigenvalue) for val in sorted_eigenvalue]
    # Step-5
    eigenvector_subset = sorted_eigenvectors[:, 0:num_var]
    # Step-6
    X_reduced = np.dot(eigenvector_subset.transpose(), X_meaned.transpose()).transpose()
    corvar = np.zeros((p, p))
    for k in range(p):
        corvar[:, k] = sorted_eigenvectors.transpose()[k, :] * np.sqrt(sorted_eigenvalue)[k]
    if plot2D:
        plotCorCircle(X, corvar, num_var)
    if plotSphere:
        plotCorSphere(X, corvar, num_var)
    if plotInertia:
        plotPCAsInertia(Inertia)
    return {'Coord' : X_reduced, 'EigVect':sorted_eigenvectors, 'EigVal': sorted_eigenvalue, 'Inertia': Inertia,
            'CorVar':corvar}

def plotPCAsInertia(Inertia):
    fig, axes = plt.subplots(figsize=(6, 6))
    plt.plot(Inertia)
    plt.xlabel('PCs')
    plt.ylabel('Inertia (-)')

def plotCorCircle(X,CorVar,num_var):
    for i in range(num_var-1):
        # cercle des corrélations
        fig, axes = plt.subplots(figsize=(6, 6))
        axes.set_xlim(-1, 1)
        axes.set_ylim(-1, 1)
        # affichage des étiquettes (noms des variables)
        for j in range(num_var-1):
            plt.arrow(0, 0, CorVar[j, i], CorVar[j, i + 1])
            # length_includes_head=True,
            # head_width=0.08, head_length=0.00002)
            plt.annotate(X.columns[j], (CorVar[j, i], CorVar[j, i + 1]))
            plt.xlabel('PC' + str(i))
            plt.ylabel('PC' + str(i + 1))
        # ajouter les axes
        plt.plot([-1, 1], [0, 0], color='silver', linestyle='-', linewidth=1)
        plt.plot([0, 0], [-1, 1], color='silver', linestyle='-', linewidth=1)
        cercle = plt.Circle((0, 0), 1, color='blue', fill=False)
        axes.add_artist(cercle)

def plotCorSphere(X, corvar,p):
    #Make the last 3D spehere plot
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    # draw sphere
    u, v = np.mgrid[0:2*np.pi:50j, 0:np.pi:50j]
    x = np.cos(u)*np.sin(v)
    y = np.sin(u)*np.sin(v)
    z = np.cos(v)
    # alpha controls opacity
    ax.plot_surface(x, y, z, color="g", alpha=0.3)
    # tails of the arrows
    tails= np.zeros(p)
    # heads of the arrows with adjusted arrow head length
    ax.quiver(tails,tails,tails,corvar[:,0], corvar[:,1], corvar[:,2],
              color='r', arrow_length_ratio=0.15)
    for i in range(p):
        ax.text(corvar[i,0],corvar[i,1],corvar[i,2],X.columns[i])
    ax.quiver(np.zeros(3),np.zeros(3),np.zeros(3),[1,0,0], [0,1,0], [0,0,1],
              length=1.25, normalize=True,color='k', arrow_length_ratio=0.15)
    ax.text(1.25,0,0,'PC0')
    ax.text(0,1.25,0,'PC1')
    ax.text(0,0,1.25,'PC2')
    ax.grid(False)
    plt.axis('off')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_title('3D plots over the three first PCAs')

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

def GetData(path,extravariables = [], Timeseries = [],BuildNum=[]):
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
    if len(BuildNum)==0:
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
    else:
        idxF = ['_'+str(BuildNum[0])+'v','.']
    #now that we found this index, lets go along alll the files
    for file in liste:
        if '.pickle' in file:
            try:
                SimNumb.append(int(file[file.index(idxF[0]) + len(idxF[0]):file.index(idxF[1])]))
                with open(file, 'rb') as handle:
                    ResBld[SimNumb[-1]] = pickle.load(handle)
                try:
                    Res['ErrFiles'].append(os.path.getsize(file[:file.index('.pickle')]+'.err'))
                except:
                    Res['ErrFiles'].append(0)
            except:
                pass

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
    # lest add the keysin the Res Dict of the extravariables
    try:
        for key in Timeseries:
            varName = Timeseries[key]['Location']+'_'+Timeseries[key]['Data']
            Res[varName] = []
    except:
        pass
    #now we aggregate the data into Res dict
    print('organizing data...')
    for i,key in enumerate(ResBld):
        if key==14:
            a=1
        Res['SimNum'].append(key)
        #lets first read the attribut of the building object (simulation inputs)
        BuildObj = ResBld[key]['BuildDB']
        try:
            Res['BuildID'].append(BuildObj.BuildID)
        except:
            Res['BuildID'].append(None)
        Res['EP_Area'].append(BuildObj.EPHeatedArea)
        try:
            Res['ATemp'].append(BuildObj.ATemp)
        except:
            Res['ATemp'].append(BuildObj.surface)
        eleval = 0
        for x in BuildObj.EPCMeters['ElecLoad']:
            if BuildObj.EPCMeters['ElecLoad'][x]:
                eleval += BuildObj.EPCMeters['ElecLoad'][x]
        Res['EPC_elec'].append(eleval/BuildObj.ATemp if BuildObj.ATemp!=0 else 0)
        heatval = 0
        for x in BuildObj.EPCMeters['Heating']:
            heatval += BuildObj.EPCMeters['Heating'][x]
        Res['EPC_Heat'].append(heatval/BuildObj.ATemp if BuildObj.ATemp!=0 else 0)
        coolval = 0
        for x in BuildObj.EPCMeters['Cooling']:
            coolval += BuildObj.EPCMeters['Cooling'][x]
        Res['EPC_Cool'].append(coolval/BuildObj.ATemp if BuildObj.ATemp!=0 else 0)
        Res['EPC_Tot'].append((eleval+heatval+coolval)/BuildObj.ATemp if BuildObj.ATemp!=0 else 0)

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
        try:
            for key1 in Timeseries:
                varName = Timeseries[key1]['Location'] + '_' + Timeseries[key1]['Data']
                if len(Res[varName])==0:
                    Res[varName] = ResBld[key][Timeseries[key1]['Location']][Timeseries[key1]['Data']]
                else:
                    Res[varName] = np.vstack((Res[varName] ,ResBld[key][Timeseries[key1]['Location']][Timeseries[key1]['Data']]))
        except:
            pass

    return Res