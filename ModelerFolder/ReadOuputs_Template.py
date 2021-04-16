import os, sys
import matplotlib.pyplot as plt
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
from geomeppy import IDF
import numpy as np
os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'ModelerFolder')
from ModelerFolder import Utilities


# the main idea of this file is to present some way for analyzing the data.
# some useful function are implemented in Utilities. Such as agregating the data from several simulation in one disctionary
# this enable to make easy plots of variables over others.
# The function getData enable to grab all the minimu information (yearly energy consumptionand EPC's values
# but also all the time series if present
# some extravaroable can be added and taken from the building object, thus the neames of the extravraible should the same as the object's attribute

# some other generic function to create figure and make plots are also available.

# but specific function are to be created for specific anaylses. some are left as example but they might not be
# compatible with other simulations than the one they were created for.

# some propose plot for timeseries with overplots of other specific cases while other function enable to plot not timedependent variables
# the ain paradigm is to give the path or a list of path and data are gathered in one element





def plotAreaVal(GlobRes,FigName,name):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        varyref = [Res['ATemp'][idx] for idx in index_y]
        maxpow = [max(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate']) for idx in
                   index_y]

        if nb==0:
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [varyref], 'Building num', ['ATemp'],
                                         'Areas (m2)', 'x')
        vary = [Res['EP_Area'][idx] for idx in index_y]
        print([maxpow[idx] / vary[idx] for idx in range(len(maxpow))])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [vary], 'Building', [name[nb]],
                                 'Areas (m2)', signe[nb])
        #vary = [(varyref[idx]-vary[idx])/varyref[idx] for idx in range(len(vary))]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1],varyref, [vary], 'ATemp (m2)', [name[nb]],
                                 'EP Area (m2)', signe[nb])
    Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1],[0,max(varyref)], [[0,max(varyref)]], 'ATemp (m2)', ['1:1'],
                                'EP Area (m2)', '--')
    newpath =os.path.normcase('C:\\Users\\xav77\Documents\FAURE\prgm_python\\UrbanT\HammarbyData\HammarbyData.pickle')
    import pickle
    with open(newpath, 'rb') as handle:
        Meas = pickle.load(handle)
    reference = [GlobRes[0]['BuildID'][i]['FormularId'] for i in range(len(GlobRes[0]['BuildID']))]
    locref = []
    keyorder = []
    for key in Meas.keys():
        locref.append(int(Meas[key]['FormularId']))
        keyorder.append(key)
    index_y, varx = Utilities.getSortedIdx(reference, locref)
    sortedMeas = [float(Meas[idx]['FormularId']) for idx in keyorder]
    newsortedMeas = [sortedMeas[idx] for idx in index_y]
    print([newsortedMeas[i]-reference[xi] for i,xi in enumerate(varx)])
    vary = [float(Meas[idx]['Atemp.EPC']) for idx in keyorder]
    newvary = [vary[idx] for idx in index_y]
    Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [newvary],
                             'Building num', ['Atemp.EPC'],
                             'Area (m2)', 'd')
    vary = [float(Meas[idx]['Atemp.DH']) for idx in keyorder]
    newvary = [vary[idx] for idx in index_y]
    Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [newvary],
                             'Building num', ['Atemp.DH'],
                             'Area (m2)', 'd')


def plotErrorFile(GlobRes,FigName,name):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = [Res['ErrFiles'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'],varx, [vary], 'Building', [name[nb]],
                                 'ErrFilesSize (bytes)', signe[nb])


def plot2Energy(GlobRes,FigName,name):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = [Res['EP_heat'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'],varx, [vary], 'Building', [name[nb]],
                                 'Heat Needs', signe[nb])
        print(len(vary),name[nb])
        print(varx)
        if nb%4==0:
            vary0 = vary
            varx0 = varx
        else:
            newy =[]
            newx = []
            for i,x1 in enumerate(varx0):
                for j,x2 in enumerate(varx):
                    if x1==x2:
                        newy.append((vary0[i]-vary[j])/vary0[i] if vary0[i] !=0 else 0)
                        newx.append(x2)
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax1'],newx, [newy], 'Building', [name[nb]],
                                         'Error factor (-)', signe[nb])

def plotDim(GlobRes,FigName,name):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [Res['BuildID'][i]['50A_UUID'] for i in range(len(Res['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        footprint = Res['BlocFootprintArea']
        nbfloor = [Res['nbfloor'][idx] for idx in index_y]
        sh1 = Res['StoreyHeigth']
        sh2 = [Res['height'][idx]/val for idx,val in enumerate(Res['nbfloor'])]
        StoreyHeight = [sh1[idx] if sh1[idx]!=-1 else sh2[idx] for idx in index_y]
        try:
            max(Res['BlocHeight'][0])
            Bld_height = [Res['BlocHeight'][idx] for idx in index_y]
            Bld_nbfloor= [Res['BlocNbFloor'][idx] for idx in index_y]
            Bld_footprint = [footprint[idx] for idx in index_y]
            floorarea = [sum(val) for val in Bld_footprint]
            Vol = []
            for idx in range(len(floorarea)):
                Vol.append(sum([Bld_height[idx][i] * Bld_footprint[idx][i] for i in range(len(Bld_footprint[idx]))]))
            #var x needs to be corrected with added avlues were there is several height
            varx4Height = []
            height = []
            floor = []
            for idx,nbbloc in enumerate(Bld_height):
                for i in range(len(nbbloc)):
                    varx4Height.append(varx[idx])
                    height.append(nbbloc[i])
                    floor.append(Bld_nbfloor[idx][i])
        except:
            height = [Res['height'][idx] for idx in index_y]
            floorarea = [footprint[idx][0] for idx in index_y]
            varx4Height = varx
            Vol = [height[idx] * floorarea[idx] for idx in range(len(floorarea))]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [floorarea], 'Building', [name[nb]],
                                 'Footprint Area (m2)', signe[nb])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varx4Height, [height], 'Building', [name[nb]],
                                 'Height (m)', signe[nb])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][2], varx, [Vol], 'Building', [name[nb]],
                                 'Volume (m3)', signe[nb])
        # Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][3], varx, [StoreyHeight], 'Building', [name[nb]],
        #                          'Storey Height (m)', signe[nb])
        # Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][3], varx4Height, [floor], 'Building',
        #                          [name[nb]],
        #                          'Storey Height (m)', signe[nb])

def plotEnergyVsPower(GlobRes,FigName,name):
    refVar = '[''BuildID''][''50A_UUID'']'
      # we need this reference because some building are missing is somme simulation !!!
    # definition of the reference for comparison
    signe = ['.', 's', '>', '<', 'd', 'o', '.', 's', '>', '<', 'd', 'o']
    for nb in GlobRes:
        if nb%4==0:
            reference = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(
                len(GlobRes[nb]['BuildID']))]
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y, varx = Utilities.getSortedIdx(reference, locref)
        if nb%4==0:
            varyref = [Res['EP_heat'][idx] for idx in index_y]
            varxref = [max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],
                                          int(len(Res['HeatedArea'][idx][
                                                      'Data_Zone Ideal Loads Supply Air Total Heating Rate']) / 8760)))
                    for idx in index_y]
        else:
            vary = [Res['EP_heat'][idx] for idx in index_y]
            varx = [max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],
                                          int(len(Res['HeatedArea'][idx][
                                                      'Data_Zone Ideal Loads Supply Air Total Heating Rate']) / 8760)))
                    for idx in index_y]
            varx2plot = [(varx[idx]-val)/val for idx,val in enumerate(varxref)]
            vary2plot = [(vary[idx] - val) / val for idx, val in enumerate(varyref)]
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx2plot, [vary2plot], 'Power Factor (-)', [name[nb]],
                                     'energy Factor (-)', signe[nb],5)

def plotEnergyVsPower1(GlobRes,FigName,name):
    refVar = '[''BuildID''][''50A_UUID'']'
      # we need this reference because some building are missing is somme simulation !!!
    # definition of the reference for comparison
    signe = ['.', 's', '>', '<', 'd', 'o', '.', 's', '>', '<', 'd', 'o']
    for nb in GlobRes:
        if nb%4==0:
            reference = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(
                len(GlobRes[nb]['BuildID']))]
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y, varx = Utilities.getSortedIdx(reference, locref)
        if nb%4==0:
            varyref = [Res['EP_heat'][idx] for idx in index_y]
            varxref = [max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],
                                          int(len(Res['HeatedArea'][idx][
                                                      'Data_Zone Ideal Loads Supply Air Total Heating Rate']) / 8760)))
                    for idx in index_y]
        else:
            vary = [Res['EP_heat'][idx] for idx in index_y]
            varx = [max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],
                                          int(len(Res['HeatedArea'][idx][
                                                      'Data_Zone Ideal Loads Supply Air Total Heating Rate']) / 8760)))
                    for idx in index_y]
            varx2plot = [(varx[idx]-val)/val for idx,val in enumerate(varxref)]
            vary2plot = [(vary[idx] - val) / val for idx, val in enumerate(varyref)]
            for bld in range(len(varx2plot)):
                Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx2plot[bld], [vary2plot[bld]], 'Power Factor (-)', [],
                                     'energy Factor (-)', '.',varxref[bld]/max(varxref)*50)

def plotEnergyVsPower2(GlobRes,FigName,name):
    refVar = '[''BuildID''][''50A_UUID'']'
      # we need this reference because some building are missing is somme simulation !!!
    # definition of the reference for comparison
    signe = ['.', 's', '>', '<', 'd', 'o', '.', 's', '>', '<', 'd', 'o']
    for nb in GlobRes:
        if nb%4==0:
            reference = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(
                len(GlobRes[nb]['BuildID']))]
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y, varx = Utilities.getSortedIdx(reference, locref)
        if nb%4==0:
            varyref = [Res['EP_heat'][idx] for idx in index_y]
            varxref = [max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],
                                          int(len(Res['HeatedArea'][idx][
                                                      'Data_Zone Ideal Loads Supply Air Total Heating Rate']) / 8760)))
                    for idx in index_y]

            finalsx = {}
            finalsy = {}
        else:
            vary = [Res['EP_heat'][idx] for idx in index_y]
            vary = [max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],
                                          int(len(Res['HeatedArea'][idx][
                                                      'Data_Zone Ideal Loads Supply Air Total Heating Rate']) / 8760)))
                    for idx in index_y]

            varx2plot = [(varx[idx]-val)/val for idx,val in enumerate(varxref)]
            vary2plot = [(vary[idx] - val) / val for idx, val in enumerate(varyref)]
            if not finalsx:
                for idx, val in enumerate(varx2plot):
                    finalsx[idx] = []
                    finalsy[idx] = []
            for idx,val in enumerate(varx2plot):
                finalsx[idx].append(varx2plot[idx])
                finalsy[idx].append(vary2plot[idx])
        if nb%4==3:
            for bld in finalsx.keys():
                Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], [val for val in finalsx[bld] if val!=0], [[val for val in finalsy[bld] if val!=0]], 'Power Factor (-)', [bld],
                                 'energy Factor (-)', signe[nb]+'--')

def plotEnergy(GlobRes,FigName,name):
    refVar = '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(
        len(GlobRes[0]['BuildID']))]  # we need this reference because some building are missing is somme simulation !!!
    # definition of the reference for comparison
    signe = ['.', 's', '>', '<', 'd', 'o', '.', 's', '>', '<', 'd', 'o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y, varx = Utilities.getSortedIdx(reference, locref)
        varyref = [Res['EPC_Heat'][idx] for idx in index_y]
        if nb == 0:
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [varyref], 'Building num',
                                     ['EPCs'],
                                     'Heat Needs (kWh/m2)', 'x')
        vary = [Res['EP_heat'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [vary], 'Building', [name[nb]],
                                 'Heat Needs (kWh/m2)', signe[nb])
        # vary = [(varyref[idx]-vary[idx])/varyref[idx] for idx in range(len(vary))]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varyref, [vary], 'EP Sim',
                                 [name[nb]],
                                 'EP Sim', signe[nb])
    Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], [0, max(varyref)], [[0, max(varyref)]],
                             'EPCs', ['1:1'],
                             'Heat Needs (kWh/m2)', 'k-')
    # Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], [0, max(varyref)], [[0, 0.9*max(varyref)]],
    #                          'EPCs', ['1:0.9'],
    #                          'Heat Needs (kWh/m2)', 'b--')
    # Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], [0, max(varyref)], [[0, 1.1*max(varyref)]],
    #                          'EPCs', ['1:1.1'],
    #                          'Heat Needs (kWh/m2)', 'b--')

def plotPower(GlobRes,FigName,name):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary =[max(Utilities.Average(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'],int(len(Res['HeatedArea'][idx]['Data_Zone Ideal Loads Supply Air Total Heating Rate'])/8760))) for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'],varx, [vary], 'Building', [name[nb]],
                                 'max Power Needs', signe[nb])
        print(len(vary),name[nb])
        print(varx)
        if nb%4==0:
            vary0 = vary
            varx0 = varx
        else:
            newy =[]
            newx = []
            for i,x1 in enumerate(varx0):
                for j,x2 in enumerate(varx):
                    if x1==x2:
                        newy.append((vary0[i]-vary[j])/vary0[i] if vary0[i] !=0 else 0)
                        newx.append(x2)
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax1'],newx, [newy], 'Buildings', [name[nb]],
                                         'Error factor (-)', signe[nb])

def plotTimeSeries(GlobRes,FigName,name,Location,TimeSerieList,SimNum=0):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        print(Res['SimNum'])
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = Res[Location][index_y[varx.index(SimNum)]][TimeSerieList]
        varx = np.linspace(1,len(vary),len(vary))
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'],varx, [vary], 'Time', [name[nb]],
                                 TimeSerieList, '--')
        if nb==0:
            vary0 = vary
        else:
            diff = [(vary0[idx]-val) for idx,val in enumerate(vary)]
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax1'],varx, [diff], 'Time', [name[nb]],
                                     'Error', '--')


def plotSignature(GlobRes,FigName,name,Location,SimNum=0):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = Res['HeatedArea'][index_y[SimNum]]['Data_Zone Ideal Loads Supply Air Total Heating Rate']
        varycool = Res['HeatedArea'][index_y[SimNum]]['Data_Zone Ideal Loads Zone Total Cooling Rate']
        varx = Res['OutdoorSite'][index_y[SimNum]]['Data_Site Outdoor Air Drybulb Temperature']
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'],varx, [vary], 'Time', [name[nb]],
                                 'Sig', '.')
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax1'], varx, [varycool], 'Time', [name[nb]],
                                 'Sig', '.')

def plotIndex(GlobRes,FigName,name):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = [Res['SimNum'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'], varx, [vary], 'Building',
                                 [name[nb]],
                                 'Building num in the GeojSon file', signe[nb])

def plotBar(GlobRes):
    for nb in GlobRes:
        Res = GlobRes[nb]
        data=np.array(Res['EPC_Heat']).reshape(len(Res['EPC_Heat']),1)
        if nb==0:
            Data2bar = data
        else:
            Data2bar = np.append(Data2bar,data,axis=1)
    Data2plot= Data2bar.transpose()
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    X = np.linspace(0,len(Res['EPC_Heat']),len(Res['EPC_Heat']))
    ax.bar(X + 0.00, Data2plot[0], color='b', width=0.25)
    ax.bar(X + 0.25, Data2plot[1], color='g', width=0.25)
    ax.bar(X + 0.50, Data2plot[2], color='r', width=0.25)
    ax.bar(X + 0.75, Data2plot[3], color='r', width=0.25)



if __name__ == '__main__' :



    mainpath = os.getcwd()

    path = [mainpath + os.path.normcase('/hammarbyr0/Sim_Results')]
    # path.append(mainpath + os.path.normcase('/hammarbyr2/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/hammarbyr1/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/hammarbyr101/Sim_Results'))

    #path = [mainpath + os.path.normcase('/Minnebergwith25Wm/Sim_Results')]
    #path.append(mainpath + os.path.normcase('/MinnebergFMUwith25Wm/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/Minnebergr0/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/Minnebergr2/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/Minnebergr1/Sim_Results'))
    #path.append(mainpath + os.path.normcase('/minnebergwith10wm/Sim_Results'))
    #path.append(mainpath + os.path.normcase('/Minnebergr101/Sim_Results'))

    #path.append(mainpath + os.path.normcase('/25dv61zoneperfloorperim/Sim_Results'))

    #path = [mainpath + os.path.normcase('/zoneperfloorv9_v2/Sim_Results')]
    # path.append(mainpath + os.path.normcase('/25dv71zoneperbloc/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/25dv71zoneperblocperim/Sim_Results'))
    #path.append(mainpath + os.path.normcase('/zoneperfloorv9_v2/Sim_Results'))
    # path.append(mainpath + os.path.normcase('/25dv71zoneperfloor_perim/Sim_Results'))
    #path.append(mainpath + os.path.normcase('/WithNewMat/Sim_Results'))
    #path.append(mainpath + os.path.normcase('/25Dzoneperfloor/Sim_Results'))
    #path.append(mainpath + os.path.normcase('/3/Sim_Results'))

    extraVar=['height','StoreyHeigth','nbfloor','BlocHeight','BlocFootprintArea','BlocNbFloor','HeatedArea','NonHeatedArea','OutdoorSite']

    testName = ['model','r1','r2','r101']
    Pathname = ['EP', 'Min', '25Dv7']
    newTestName = []
    for key in Pathname:
        for key1 in testName:
            newTestName.append(key+key1)
    testName = newTestName

    Res = {}
    TimeSerieList=[]
    for id, curPath in enumerate(path):
        Res[id] = Utilities.GetData(curPath,extraVar)
        if id ==0:
            for key in Res[id]['HeatedArea'][8].keys():
                if type(Res[id]['HeatedArea'][8][key])==list:
                    TimeSerieList.append(key)
    # # # #plotBar(Res) I don't know how to make bar plots....
    # Timecomp={}
    # for i,serie in enumerate(TimeSerieList):
    #     try:
    #         Timecomp[i] = Utilities.createDualFig('',ratio = 0.3)
    #         plotTimeSeries(Res,Timecomp[i],testName,'HeatedArea',serie,SimNum =9)
    #     except:
    #         pass

    # try:
    #     Signature = Utilities.createDualFig('', ratio=0.3)
    #     plotSignature(Res, Signature, testName, 'HeatedArea', SimNum=20)
    # except:
    #     pass

    #
    # #plotthe index value in each 2D and 2.5D files (needed to have both building for depper analyses
    IndexFig = Utilities.createSimpleFig()
    plotIndex(Res, IndexFig, testName)
    # #
    # # # plotthe index value in each 2D and 2.5D files (needed to have both building for depper analyses
    # ErrorFig = Utilities.createSimpleFig()
    # plotErrorFile(Res, ErrorFig, testName)
    # #
    # #
    # #
    # #plot the Areas of all buildings, as many path as you want can be given here
    AreaFig = Utilities.createMultilFig('',2,linked=False)
    ResArea =Res#{0:Res[0],1:Res[4]}
    plotAreaVal(ResArea, AreaFig, testName)
    # # #
    # #plot absolute and relative error two simulation, thus 2 pathes are needed for this
    # Energy2Fig = Utilities.createDualFig('', ratio=0.5)
    # plot2Energy(Res, Energy2Fig,testName)
    #
    # # plot absolute and relative error two simulation, thus 2 pathes are needed for this
    # DimFig = Utilities.createMultilFig('', 3)
    # plotDim(Res, DimFig,testName)
    # #
    # # #plot the energy heat needs of all buildings, as many path as you want can be given here
    EnergyFig = Utilities.createMultilFig('',2,linked=False)
    plotEnergy(Res, EnergyFig,testName)
    #
    # PowerFig = Utilities.createDualFig('', ratio=0.5)
    # plotPower(Res, PowerFig,testName)
    #
    #
    # EnergyFig1 = Utilities.createMultilFig('', 1, linked=False)
    # plotEnergyVsPower1(Res, EnergyFig1, testName)

    plt.show()