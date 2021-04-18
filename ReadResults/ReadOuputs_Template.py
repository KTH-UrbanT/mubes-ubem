import os, sys
import matplotlib.pyplot as plt
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
import numpy as np
sys.path.append(os.path.dirname(os.getcwd()))
import Utilities



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
# the main paradigm is to give the path or a list of path and data are gathered in one element


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
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [vary], 'Building', [name[nb]],
                                 'Areas (m2)', signe[nb])
        #vary = [(varyref[idx]-vary[idx])/varyref[idx] for idx in range(len(vary))]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1],varyref, [vary], 'ATemp (m2)', [name[nb]],
                                 'EP Area (m2)', signe[nb])
    Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1],[0,max(varyref)], [[0,max(varyref)]], 'ATemp (m2)', ['1:1'],
                                'EP Area (m2)', '--')


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
        vary = [Res['EP_Heat'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [vary], 'Building', [name[nb]],
                                 'Heat Needs (kWh/m2)', signe[nb])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varyref, [vary], 'EP Sim',
                                 [name[nb]],
                                 'EP Sim', signe[nb])
    Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], [0, max(varyref)], [[0, max(varyref)]],
                             'EPCs', ['1:1'],
                             'Heat Needs (kWh/m2)', 'k-')


def plotTimeSeries(GlobRes,FigName,name,Location,TimeSerieList,SimNum=0):
    refVar= '[''BuildID''][''50A_UUID'']'
    reference = [GlobRes[0]['BuildID'][i]['50A_UUID'] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
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



if __name__ == '__main__' :

    CaseName= 'ForTest' #Name of the case study to post-process

    #Names (attributes) wanted to be taken in the pickle files for post-processing. The time series are agrregated into HeatedArea, NonHeatedArea and OutdoorSite
    extraVar=['height','StoreyHeigth','nbfloor','BlocHeight','BlocFootprintArea','BlocNbFloor','HeatedArea','NonHeatedArea','OutdoorSite']
    Names4Plots = [CaseName] #because we can have several path for several studies we want to overplot.
    mainpath = os.path.dirname(os.path.dirname(os.getcwd()))
    path = [mainpath + os.path.normcase('/MUBES_SimResults/'+CaseName+'/Sim_Results')]

    Res = {}
    TimeSerieList=[]
    for id, curPath in enumerate(path):
        Res[id] = Utilities.GetData(curPath,extraVar)
        #lets grab the time series name (the chossen ouputs from EP).
        # /!\ the data are taken from the building number 0, thus if for example not an office type, the will be no occupant. Choose another building if needed
        blfRef=0
        if id==0:
            for key in Res[id]['HeatedArea'][0].keys():
                if type(Res[id]['HeatedArea'][0][key])==list:
                    TimeSerieList.append(key)

    #The opening order does not follows the building simulation number while opening the data. Thus, this first graphs provides the correspondance between the other plots, building number and their simulation number
    IndexFig = Utilities.createSimpleFig()
    plotIndex(Res, IndexFig, Names4Plots)
    #this 2nd plot gives the size of the error file. It gives insights if some buildings causses particulary over whole issue in the simulation process
    ErrorFig = Utilities.createSimpleFig()
    plotErrorFile(Res, ErrorFig, Names4Plots)
    #this 3rd graph gives the footprint area and the correspondance between EPCs value if available
    AreaFig = Utilities.createMultilFig('',2,linked=False)
    plotAreaVal(Res, AreaFig, Names4Plots)
    #this one gives geometric values
    DimFig = Utilities.createMultilFig('', 3)
    plotDim(Res, DimFig,Names4Plots)
    # this one gives the energy demand of heating with EPCs values
    EnergyFig = Utilities.createMultilFig('',2,linked=False)
    plotEnergy(Res, EnergyFig,Names4Plots)

    #below, some timeseries are plotted, all time series available but only for building Simulation Number 0
    Timecomp={}
    for i,serie in enumerate(TimeSerieList):
        try:
            Timecomp[i] = Utilities.createSimpleFig()
            plotTimeSeries(Res,Timecomp[i],Names4Plots,'HeatedArea',serie,SimNum =0)
        except:
            pass

    plt.show()