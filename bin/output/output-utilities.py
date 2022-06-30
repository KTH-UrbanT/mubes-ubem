#this file is just a tank of utilities for ploting stuff mainly.
#It creates the figures and the plots
import os,sys
import pickle#5 as pickle
#import pickle5
import matplotlib.pyplot as plt
from matplotlib import gridspec
import numpy as np
import CoreFiles.GeneralFunctions as GrlFct
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn import metrics
import pandas as pd

def makePolyPlots(CaseChoices,Pool2Launch):
    forced2D = False
    if CaseChoices['DataBaseInput']: Need2LoadFile = False
    else : Need2LoadFile = True
    cpt = '--------------------'
    cpt1 = '                    '
    totalsize = len(Pool2Launch)
    plot3d = False
    for idx, Case in enumerate(Pool2Launch):
        if Case['TotBld_and_Origin']:
            if Need2LoadFile:
                DataBaseInput = GrlFct.ReadGeoJsonFile(Case['keypath'], Case['CoordSys'], toBuildPool=False)
                DataBase = DataBaseInput['Build']
            else:
                DataBaseInput = CaseChoices['DataBaseInput']
                DataBase = DataBaseInput['Build']

        if idx ==0:
            if max(DataBase[0].geometry.poly3rdcoord) > 0 and not forced2D: plot3d = True
            if not CaseChoices['MakePlotsPerBld']:
                # fig = plt.figure(figsize=(100,100))
                fig = plt.figure()
                if plot3d: ax = plt.axes(projection="3d")
                else: ax = fig.add_subplot(111)
        done = (idx + 1 ) / totalsize
        print('\r', end='')
        ptcplt = '.' if idx % 2 else ' '
        msg = cpt[:int(20 * done)] + ptcplt + cpt1[int(20 * done):] + str(round(100 * done, 1))
        print('Figure being completed by ' + msg + ' %', end='', flush=True)
        if CaseChoices['MakePlotsPerBld']:
            fig = plt.figure()
            if plot3d: ax = plt.axes(projection="3d")
            else: ax = fig.add_subplot(111)
        BldObj = DataBase[Case['BuildNum2Launch']]
        coords = BldObj.geometry.coordinates
        propreties = BldObj.properties
        for i,poly in enumerate(coords):
            if len(poly) > 1:
                poly2plot = poly
            else:
                poly2plot = poly[0]
            x, y = zip(*poly2plot)
            if plot3d:
                z = [BldObj.geometry.poly3rdcoord[i]]*len(x)
                plt.plot(x, y,z, '-')
            else:
                plt.plot(x, y, '-')
        if CaseChoices['MakePlotsPerBld'] or len(Pool2Launch)==1:
            try : titlemsg = str(CaseChoices['BldIDKey']) + ' : ' + str(
                        propreties[CaseChoices['BldIDKey']])
            except: titlemsg = 'No BldId found in the GeoJSON'
            plt.title(titlemsg + ' / Building num in the file : ' + str(
                        Case['BuildNum2Launch']) +
                              '\n ' + str(len(coords)) + ' polygons found')
            if plot3d: setPolygonPlotAxis(ax)
            else: ax.set_aspect('equal', adjustable='box')
        if CaseChoices['MakePlotsPerBld'] and len(Pool2Launch)>1 : plt.show()
    if plot3d: setPolygonPlotAxis(ax)
    else: ax.set_aspect('equal', adjustable='box')
    if len(Pool2Launch)==1 and plot3d:
        makeMultiPolyplots(DataBase[Pool2Launch[0]['BuildNum2Launch']])
    # fig.savefig('C:\\Users\\xav77\\Documents\\FAURE\\DataBase\\France\\Stockbis.eps', format='eps', dpi=1200)
    plt.show()

def makeMultiPolyplots(BldObj):
    coords = BldObj.geometry.coordinates
    h = np.unique([round(val,5) for val in BldObj.geometry.poly3rdcoord])
    for i in range(len(h)):
        plt.figure(i+2)
    plt.figure(i+3)
    for i, poly in enumerate(coords):
        fignum = np.where(h == round(BldObj.geometry.poly3rdcoord[i],5))[0]+2
        makeplot(fignum,poly,title = 'Horizontal polygon found at altitude : '+str(round(BldObj.geometry.poly3rdcoord[i],5)))
        makeplot(len(h)+2,poly,title = 'All horizontal polygons from global upperview')

def makeplot(fignum,poly,title = ''):
    fig = plt.figure(fignum)
    ax = fig.add_subplot(111)
    if len(poly) > 1:
        poly2plot = poly
    else:
        poly2plot = poly[0]
    x, y = zip(*poly2plot)
    # z = [BldObj.geometry.poly3rdcoord[i]] * len(x)
    plt.plot(x, y,'.-')#, z, '.-')
    plt.title(title)
    ax.set_aspect('equal', adjustable='box')
    #setPolygonPlotAxis(ax)


def setPolygonPlotAxis(ax):
    xlim = ax.get_xlim3d()
    ylim = ax.get_ylim3d()
    Rangex = xlim[1]-xlim[0]
    Rangey = ylim[1] - ylim[0]
    zlim = ax.get_zlim3d()
    Rangez = zlim[1] - zlim[0]
    range = max(Rangex,Rangey)
    ax.set_xlim3d([xlim[0]-(range-Rangex)/2,xlim[1]+(range-Rangex)/2])
    ax.set_ylim3d([ylim[0] - (range - Rangey) / 2, ylim[1] + (range - Rangey) / 2])
    ax.set_zlim3d([zlim[0] - (range - Rangez) / 2, zlim[1] + (range - Rangez) / 2])

def CountAbovethreshold(Data,threshold):
    #give the length of data above a threshold, for hourly Data, it is number of Hrs above the threshold
    return len([i for i in Data if i > threshold])

def Average(Data,WindNbVal):
    #make an average
    NewData =[sum(Data[:WindNbVal])/WindNbVal]
    for i in range(1,len(Data)):
        if i%WindNbVal==0:
            NewData.append(sum(Data[i:i+WindNbVal])/WindNbVal)
    return NewData


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
    fig_name = plt.figure(figsize=(10, 7))
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
    fig_name = plt.figure(figsize=(10, 7))
    gs = gridspec.GridSpec(nbFig,1, left=0.1, bottom = 0.1)
    ax = {}
    for i in range(nbFig):
        ax[i] = plt.subplot(gs[i, 0])
        ax[i].grid()
        if i>0 and linked:
            ax[i].sharex(ax[0])

        if i ==0:
            plt.title(title)
    #plt.tight_layout()
    return {'fig_name' : fig_name, 'ax': ax}

def createMultilDblFig(title,nbFigx,nbFigy,linked=True):
    fig_name = plt.figure(figsize=(10, 7))
    gs = gridspec.GridSpec(nbFigx,nbFigy, left=0.1, bottom = 0.1)
    ax = {}
    totfig = 0
    for i in range(nbFigx):
        for j in range(nbFigy):
            ax[totfig] = plt.subplot(gs[i, j])
            ax[totfig].grid()
            totfig+=1
            if i>0 and j>0 and linked:
                ax[i].sharex(ax[0])
            if i==0 and j==0:
                plt.title(title)
    #plt.tight_layout()
    return {'fig_name' : fig_name, 'ax': ax}

#this function enable to create a single graph areas
def createSimpleFig():
    fig_name = plt.figure(figsize=(7, 5))
    plt.rc('font', size=15)
    #plt.subplots_adjust(bottom=0.3)
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:, 0])
    ax0.grid()
    #plt.tight_layout()
    return {'fig_name' : fig_name, 'ax0': ax0}

#basic plots
def plotBasicGraph(fig_name,ax0,varx,vary,varxname,varyname,title,sign,color = 'black', legend = True, markersize = 5, xlim =[], ylim = [], mfc = 'none'):
    plt.figure(fig_name)

    if len(varyname)>0:
        for nb,var in enumerate(vary):
            ax0.plot(varx,var,sign,label= varyname[nb], mfc=mfc,markersize=markersize,color = color)
        ax0.set_xlabel(varxname)
        ax0.set_ylabel(title)
        if xlim:
            ax0.set_xlim(xlim)
        if ylim:
            ax0.set_ylim(ylim)
        if legend:
            ax0.legend()
    else:
        for nb,var in enumerate(vary):
            ax0.plot(varx,var,sign, mfc=mfc,markersize=markersize,color = color)
        ax0.set_xlabel(varxname)
        ax0.set_ylabel(title)
        if xlim:
            ax0.set_xlim(xlim)
        if ylim:
            ax0.set_ylim(ylim)

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

def plotHist(fig_name,ax0,vary,varyname):
    plt.figure(fig_name)
    ax0.hist(vary,normed=True,label = varyname)
    ax0.legend()

def GetData(path,extravariables = [], Timeseries = [],BuildNum=[],BldList = []):
    os.chdir(path)
    liste = os.listdir()
    ResBld = {}
    Res = {}
    SimNumb = []
    Res['ErrFiles'] = []
    Res['Warnings'] = []
    Res['Errors'] = []
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
                    if abs(num[1]-num[0])>0:
                        idxF = idx1
                    else:
                        idxF = idx2
                    StillSearching = False
                    break
            if i == len(liste):
                StillSearching = False
                idxF = idx1
    else:
        idxF = ['_'+str(BuildNum[0])+'v','.']
    #now that we found this index, lets go along alll the files

    for file in liste:
        if '.pickle' in file:
            NbRun = int(file[file.index(idxF[0]) + len(idxF[0]):file.index(idxF[1])])
            if BldList:
                if NbRun not in BldList:
                    continue
            try:
                #print(file)
                SimNumb.append(NbRun)
                try:
                    with open(file, 'rb') as handle:
                        ResBld[SimNumb[-1]] = pickle.load(handle)
                except:
                    import pickle5
                    with open(file, 'rb') as handle:
                        ResBld[SimNumb[-1]] = pickle5.load(handle)
                try:
                    Res['ErrFiles'].append(os.path.getsize(file[:file.index('.pickle')]+'.err'))
                    with open(file[:file.index('.pickle')]+'.err') as file:
                        lines = file.readlines()
                    Res['Warnings'].append(int(lines[-1][lines[-1].index('--')+2:lines[-1].index('Warning')]))
                    Res['Errors'].append(int(lines[-1][lines[-1].index('Warning') + 8:lines[-1].index('Severe Errors')]))
                except:
                    Res['ErrFiles'].append(0)
            except:
                pass

    #lets get the mandatory variables
    variables=['EP_Elec','EP_Heat','EP_Cool','EP_DHW','SimNum','EPC_Elec','EPC_Heat','EPC_Cool','EPC_Tot',
               'DB_Surf','EP_Area','BuildID','BldSimName']
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
        ResDone = True
        Res['SimNum'].append(key)
        #lets first read the attribut of the building object (simulation inputs)
        try:
            BuildObj = ResBld[key]['BuildDB']
        except:
            BuildObj = ResBld[key]['BuildData']
            ResDone = False
        try:
            Res['BuildID'].append(BuildObj.BuildID)
        except:
            Res['BuildID'].append(None)
        Res['EP_Area'].append(BuildObj.EPHeatedArea)
        Res['BldSimName'].append(BuildObj.name)
        try:
            Res['DB_Surf'].append(BuildObj.DB_Surf)
        except:
            Res['DB_Surf'].append(BuildObj.surface)
            #Res['DB_Surf'].append(BuildObj.ATemp)
        eleval = 0
        for x in BuildObj.EPCMeters['ElecLoad']:
            if BuildObj.EPCMeters['ElecLoad'][x]:
                eleval += BuildObj.EPCMeters['ElecLoad'][x]
        Res['EPC_Elec'].append(eleval/Res['DB_Surf'][-1] if Res['DB_Surf'][-1]!=0 else 0)
        heatval = 0
        for x in BuildObj.EPCMeters['Heating']:
            heatval += BuildObj.EPCMeters['Heating'][x]
        Res['EPC_Heat'].append(heatval/Res['DB_Surf'][-1] if Res['DB_Surf'][-1]!=0 else 0)
        coolval = 0
        for x in BuildObj.EPCMeters['Cooling']:
            coolval += BuildObj.EPCMeters['Cooling'][x]
        Res['EPC_Cool'].append(coolval/Res['DB_Surf'][-1] if Res['DB_Surf'][-1]!=0 else 0)
        Res['EPC_Tot'].append((eleval+heatval+coolval)/Res['DB_Surf'][-1] if Res['DB_Surf'][-1]!=0 else 0)

#forthe old way of doing things and the new paradigm for global results
        try:
            for key1 in Res:
                if key1 in ['EP_Elec','EP_Cool','EP_Heat']:
                    idx = 1 if 'EP_elec' in key1 else 4  if 'EP_cool' in key1 else 5 if 'EP_heat' in key1 else None
                    Res[key1].append(ResBld[key]['EnergyConsVal'][idx] / 3.6 / BuildObj.EPHeatedArea * 1000)
        except:
            if ResDone:
                for key1 in Res:
                    if key1 in ['EP_Elec']:
                        Res[key1].append(ResBld[key]['GlobRes']['Interior Equipment']['Electricity [GJ]'] / 3.6 / BuildObj.EPHeatedArea * 1000)
                    if key1 in ['EP_Cool']:
                        Res[key1].append(ResBld[key]['GlobRes']['Cooling']['District Cooling [GJ]'] / 3.6 / BuildObj.EPHeatedArea * 1000)
                    if key1 in ['EP_Heat']:
                        Res[key1].append(ResBld[key]['GlobRes']['Heating']['District Heating [GJ]'] / 3.6 / BuildObj.EPHeatedArea * 1000)
                    if key1 in ['EP_DHW']:
                        Res[key1].append(ResBld[key]['GlobRes']['Water Systems']['District Heating [GJ]'] / 3.6 / BuildObj.EPHeatedArea * 1000)
            else:
                pass


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
    #Finaly lets reorder the results by the number of the SimNum :
    sorted_idx = np.argsort(Res['SimNum'])
    for key in Res.keys():
        if Res[key]:
            Res[key] = [Res[key][idx] for idx in sorted_idx]
    return Res


def plotDHWdistrib(Distrib,name,DataQual = []):
    fig = plt.figure(name)
    gs = gridspec.GridSpec(24, 1)

    XMAX1 = [0]*len(Distrib)
    act = ['mean', 'max', 'min', 'std']
    ope = 'mean'
    for yr,Dist in enumerate(Distrib):
        xmax1 = [0] * 24
        for i in range(24):
            distrib = [val for id,val in enumerate(Dist[:,i])]
            xmax1[i] = gener_Plot(gs, distrib, i, 0, name)
        XMAX1.append(max(xmax1))
    for i in range(24):
        ax0 = plt.subplot(gs[i, 0])
        ax0.set_xlim([0, max(XMAX1)])
        #plt.title(name)
        #plt.show()

def gener_Plot(gs,data,i,pos,titre):
    ax0 = plt.subplot(gs[i, pos])
    #ax0.hist(data, 50, alpha=0.75)
    #ax0.set_xlim([0, pos*5+10])
    pt = np.histogram(data, 50)
    volFlow = [pt[1][i] + float(j) for i, j in enumerate(np.diff(pt[1]))]
    #plt.plot(volFlow,pt[0])
    plt.fill_between(volFlow,0,pt[0],alpha = 0.5)
    if i==0:
        plt.title(titre)
    plt.yticks([0], [str(i)])
    if pos>0:
        plt.yticks([0], [''])
    plt.grid()
    if i<23:
        plt.tick_params(
            axis='x',  # changes apply to the x-axis
            which='both',  # both major and minor ticks are affected
            bottom=False,  # ticks along the bottom edge are off
            top=False,  # ticks along the top edge are off
            labelbottom=False)  # labels along the bottom edge are off
    else:
        plt.xlabel('L/min')#data = np.array(data)
    return max(volFlow)

def getLRMetaModel(X,y):
    #this function comuts a Linear Regression model give the X parameters in a dataframe formet and the y output
    #20% of the data are used to check the model afterward
    #the function returns the coeffient of the model
    #print('Launching calib process of linear regression')
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    coeff_df = pd.DataFrame(regressor.coef_, X.columns, columns=['Coefficient'])
    y_pred = regressor.predict(X_test)
    # print('Mean Absolute Error:', metrics.mean_absolute_error(y_test, y_pred))
    # print('Mean Squared Error:', metrics.mean_squared_error(y_test, y_pred))
    #print('R2:', metrics.r2_score(y_test, y_pred))
    # print('Root Mean Squared Error:', np.sqrt(metrics.mean_squared_error(y_test, y_pred)))
    return coeff_df, regressor.intercept_, metrics.r2_score(y_test, y_pred)