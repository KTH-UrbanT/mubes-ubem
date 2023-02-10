import os, sys
import matplotlib.pyplot as plt
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
# path2addFMU = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'FMUsKit/EnergyPlusToFMU-v3.1.0'))
# sys.path.append(path2addFMU)
import numpy as np
sys.path.append(os.path.dirname(os.getcwd()))
import output_utilities as Utilities
import core.setConfig as setConfig


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
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    refVar= '[''BuildID''][key]'
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i][key] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        varx = [int(Res['SimNum'][idx]) for idx in index_y]
        varyref = [Res['DB_Surf'][idx] for idx in index_y]
        if nb==0:
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [varyref], 'Building num', ['ATemp'],
                                         'Areas (m2)', 'x')
        vary = [Res['EP_Area'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [vary], 'Building', [name[nb]],
                                 'Areas (m2)', signe[np.random.randint(0, 10)])
        #vary = [(varyref[idx]-vary[idx])/varyref[idx] for idx in range(len(vary))]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1],varyref, [vary], 'ATemp (m2)', [name[nb]],
                                 'EP Area (m2)', signe[np.random.randint(0, 10)])
    # Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1],[0,max(varyref)], [[0,max(varyref)]], 'ATemp (m2)', ['1:1'],
    #                             'EP Area (m2)', '--')


def plotErrorFile(GlobRes,FigName,name,legend = True):
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    refVar = '[''BuildID''][key]'
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(
        len(GlobRes[0]['BuildID']))]  # we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    offset = 0
    tot = 0
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i][key] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = [Res['Warnings'][idx] for idx in index_y]
        varx = [int(Res['SimNum'][idx]) for idx in index_y]
        #arx = [int(x) for x in np.linspace(offset, offset + len(vary), len(vary))]
        xtitle = 'Building'
        Warnings = [Res['SimNum'][idx] for idx, val in enumerate(vary) if val > 0]
        if Warnings:
            print('Case nb : ' + str(nb) + ' has simulations with Warnings on buildings : ' + str(Warnings))
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [vary], xtitle, [name[nb]],
                                 'Nb Warnings', signe[np.random.randint(0,10)],legend = legend)
        vary = [Res['Errors'][idx] for idx in index_y]
        varx = [int(Res['SimNum'][idx]) for idx in index_y]
        #varx = [int(x) for x in np.linspace(offset, offset + len(vary), len(vary))]
        #offset +=  (len(vary) + 1) if wanted to be added in x axis along the different cases
        xtitle = 'Building'
        Errors = [Res['SimNum'][idx] for idx,val in enumerate(vary) if val>0]
        if Errors:
            print('File nb : '+str(nb)+' has simulations with errors on buildings : '+str(Errors))
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varx, [vary], xtitle, [name[nb]],
                                 'Nb Severe Errors (bytes)', signe[np.random.randint(0, 10)], legend=legend)


def plotDim(GlobRes,FigName,name):
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    refVar= '[''BuildID''][key]'
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [Res['BuildID'][i][key] for i in range(len(Res['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        varx = [int(Res['SimNum'][idx]) for idx in index_y]
        footprint = Res['BlocFootprintArea']
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
                                 'Footprint Area (m2)', signe[np.random.randint(0, 10)])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varx4Height, [height], 'Building', [name[nb]],
                                 'Height (m)', signe[np.random.randint(0, 10)])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][2], varx, [Vol], 'Building', [name[nb]],
                                 'Volume (m3)', signe[np.random.randint(0, 10)])

def plotShadingEffect(GlobRes,FigName,name):
    refVar = '[''BuildID''][key]'
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(
        len(GlobRes[0]['BuildID']))]  # we need this reference because some building are missing is somme simulation !!!
    # definition of the reference for comparison
    signe = ['.', 's', '>', '<', 'd', 'o', '.', 's', '>', '<', 'd', 'o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        varx = Res['MaxShadingDist']
        vary = Res['EP_Heat']
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [vary], 'Max Shading Distance (m)', [name[nb]],
                                 'Heat Needs (kWh/m2)', signe[np.random.randint(0, 10)])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varx, [[val/max(vary) for val in vary]], 'Max Shading Distance (m)',
                                 [name[nb]],
                                 'Heat Needs (kWh/m2)', signe[np.random.randint(0, 10)])



def plotEnergy(GlobRes,FigName,name):
    refVar = '[''BuildID''][key]'
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(
        len(GlobRes[0]['BuildID']))]  # we need this reference because some building are missing is somme simulation !!!
    # definition of the reference for comparison
    signe = ['.', 's', '>', '<', 'd', 'o','v','^','1','2','3','4','8','p','P','*','h','H','+']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i][key] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y, varx = Utilities.getSortedIdx(reference, locref)
        varx = [int(Res['SimNum'][idx]) for idx in index_y]
        varyref = [Res['EPC_Heat'][idx] for idx in index_y]
        if nb == 0:
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [varyref], 'Building num',
                                     ['EPCs'],
                                     'Heat Needs (kWh/m2)', 'x')
        vary = [Res['EP_Heat'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0], varx, [vary], 'Building', [name[nb]],
                                 'Heat Needs (kWh/m2)', signe[np.random.randint(0, len(signe))])
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varyref, [vary], 'EP Sim',
                                 [name[nb]],
                                 'EP Sim', signe[np.random.randint(0, len(signe))])
    # Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], [0, max(varyref)], [[0, max(varyref)]],
    #                          'EPCs', ['1:1'],
    #                          'Heat Needs (kWh/m2)', 'k-')


def plotTimeSeries(GlobRes,FigName,name,Location,TimeSerieList,Unit,SimNum=[]):
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    refVar= '[''BuildID''][key]'
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        if not SimNum:
            SimNum = Res['SimNum']
        locref = [GlobRes[nb]['BuildID'][i][key] for i in range(len(GlobRes[nb]['BuildID']))]

        for num,nbBld in enumerate(SimNum):
            index_y, varx = Utilities.getSortedIdx(reference, locref)
            vary = Res[Location][index_y[varx.index(num)]][TimeSerieList]
            varx = np.linspace(1,len(vary),len(vary))
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][0],varx, [vary], 'Time', [name[nb]+'_Bld_'+str(nbBld)+' '+TimeSerieList],
                                     Unit, '--')
            Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax'][1], varx, [np.cumsum(vary)], 'Time',
                                     [],
                                     'Cumulative form', '--')
        # if nb==0:
        #     vary0 = vary
        # else:
        #     diff = [(vary0[idx]-val) for idx,val in enumerate(vary)]
        #     Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax1'],varx, [diff], 'Time', [name[nb]],
        #                              'Error', '--')


def plotIndex(GlobRes,FigName,name):
    key = GlobRes[0]['BuildID'][0]['BldIDKey']
    refVar= '[''BuildID''][key]'
    reference = [GlobRes[0]['BuildID'][i][key] for i in range(len(GlobRes[0]['BuildID']))]#we need this reference because some building are missing is somme simulation !!!
    #definition of the reference for comparison
    signe = ['.','s','>','<','d','o','.','s','>','<','d','o']
    for nb in GlobRes:
        Res = GlobRes[nb]
        locref = [GlobRes[nb]['BuildID'][i][key] for i in range(len(GlobRes[nb]['BuildID']))]
        index_y,varx = Utilities.getSortedIdx(reference,locref)
        vary = locref #[Res['SimNum'][idx] for idx in index_y]
        Utilities.plotBasicGraph(FigName['fig_name'].number, FigName['ax0'], varx, [vary], 'Building',
                                 [name[nb]],
                                 'Building num in the GeojSon file', signe[np.random.randint(0, 10)])

def Read_Arguments():
    #these are defaults values:
    Config2Launch = []
    CaseNameArg =[]
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-yml')):
            currIdx += 1
            Config2Launch = sys.argv[currIdx]
        if (currArg.startswith('-Case')):
            currIdx += 1
            CaseNameArg = sys.argv[currIdx]
        currIdx += 1
    return Config2Launch,CaseNameArg

def getPathList(config):
    CaseNames = config['2_CASE']['0_GrlChoices']['CaseName'].split(',')
    path = []
    Names4Plots = []
    for CaseName in CaseNames:
        configPath = os.path.abspath(os.path.join(config['0_APP']['PATH_TO_RESULTS'],
                                                  CaseName))
        if not os.path.exists(configPath):
            print('Sorry, the folder '+CaseName+' does not exist...use -Case or -yml option or change your localConfig.yml')
            sys.exit()
        if os.path.exists(os.path.join(configPath,'Sim_Results')):
            path.append(os.path.join(configPath,'Sim_Results'))
            Names4Plots.append(CaseName)
        else:
            if len(CaseNames)>1:
                print(
                    'Sorry, but CaseNames '+str(CaseNames)+' cannot be aggregated because all or some contains several subcases')
                sys.exit()
            liste = [f for f in os.listdir(configPath) if os.path.isdir(os.path.abspath(f))]
            for folder in liste:
                path.append(os.path.join(configPath,folder,'Sim_Results'))
                Names4Plots.append(CaseName + '/' + folder)
    return path,Names4Plots,CaseNames

if __name__ == '__main__' :
    defaultConfigPath = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'default','config')
    ConfigFromArg,CaseNameArg = Read_Arguments()
    config = setConfig.read_yaml(os.path.join(defaultConfigPath, 'DefaultConfig.yml'))
    configUnit = setConfig.read_yaml(os.path.join(defaultConfigPath,'DefaultConfigKeyUnit.yml'))
    #lets get the environment variable and try if there is a new made one
    try: env = setConfig.read_yaml(os.path.join(defaultConfigPath, 'env.yml'))
    except: env = setConfig.read_yaml(os.path.join(defaultConfigPath, 'env.default.yml'))
    # make the change for the env variable
    config, msg = setConfig.ChangeConfigOption(config, env)

    LocalConfigPath = os.getcwd() #this can be changed if specific folder to consider is known
    localConfig, filefound, msg = setConfig.check4localConfig(LocalConfigPath,case = 1)
    if msg: print(msg)
    if localConfig: config, msg = setConfig.ChangeConfigOption(config, localConfig)
    if msg: print(msg)
    #config['2_CASE']['0_GrlChoices']['CaseName'] = 'Simple'

    if CaseNameArg:
        config['2_CASE']['0_GrlChoices']['CaseName'] = CaseNameArg
        path, Names4Plots,CaseNames = getPathList(config)
    elif type(ConfigFromArg) == str:
        if ConfigFromArg[-4:] == '.yml':
            localConfig = setConfig.read_yaml(ConfigFromArg)
            config, msg = setConfig.ChangeConfigOption(config, localConfig)
            path,Names4Plots,CaseNames = getPathList(config)
        else:
            print('[Unknown Argument] Please check the available options for arguments : -yml or -Case')
            sys.exit()
    else:
        path, Names4Plots,CaseNames = getPathList(config)
    print('[Studied Results Folder] '+str(Names4Plots))
    #Names (attributes) wanted to be taken in the pickle files for post-processing. The time series are agrregated into HeatedArea, NonHeatedArea and OutdoorSite
    extraVar=['AirRecovEff',"IntLoadCurveShape","wwr","EnvLeak","AreaBasedFlowRate",'BlocHeight','BlocNbFloor','HeatedArea','BlocFootprintArea']
    #path can be define in hard for specific use:
    # path = ['C:/Users/FAURE/Documents/prgm_python/mubes-ubem/ForTest/Sim_results']
    # CaseNames = 'Test'


    Names4Plots = CaseNames
    Res = {}
    TimeSerieList=[]
    TimeSerieUnit = []
    id =0
    for idx, curPath in enumerate(path):
        print('Considering results from : '+Names4Plots[idx])
        try:
            Res[idx] = Utilities.GetData(curPath,extraVar)
            #lets grab the time series name (the chossen ouputs from EP).
            # /!\ the data are taken from the building number 0, thus if for example not an office type, the will be no occupant. Choose another building if needed
            blfRef=0
            if idx==0:
                for key in Res[idx]['HeatedArea'][blfRef].keys():
                    if type(Res[idx]['HeatedArea'][blfRef][key])==list:
                        TimeSerieList.append(key)
                        TimeSerieUnit.append(Res[idx]['HeatedArea'][blfRef][key.replace('Data_','Unit_')])
        except: pass


    # with open('ShapeFact.txt', 'w') as f:
    #     for idx,val in enumerate(Res[0]['SimNum']):
    #         f.write(str(val)+'\t'+str(Res[0]['ExtEnvSurf'][idx])+'\t'+str(Res[0]['IntVolume'][idx])+'\n')
    #The opening order does not follows the building simulation number while opening the data. Thus, this first graphs provides the correspondance between the other plots, building number and their simulation number
    # IndexFig = Utilities.createSimpleFig()
    # plotIndex(Res, IndexFig, Names4Plots)
    # #this 2nd plot gives the size of the error file. It gives insights if some buildings causses particulary over whole issue in the simulation process
    # ErrorFig = Utilities.createMultilFig('',2,linked=False)
    # plotErrorFile(Res, ErrorFig, Names4Plots)
    #this 3rd graph gives the footprint area and the correspondance between EPCs value if available
    AreaFig = Utilities.createMultilFig('',2,linked=False)
    plotAreaVal(Res, AreaFig, Names4Plots)
    #this one gives geometric values
    DimFig = Utilities.createMultilFig('', 3)
    plotDim(Res, DimFig,Names4Plots)
    # this one gives the energy demand of heating with EPCs values
    EnergyFig = Utilities.createMultilFig('',2,linked=False)
    plotEnergy(Res, EnergyFig,Names4Plots)
    #this one is the consumption depending on the shading distance (of course simulation should have been done before...)
    # ShadingFig = Utilities.createMultilFig('',2,linked=False)
    # plotShadingEffect(Res, ShadingFig,Names4Plots)

    # #below, some timeseries are plotted, all time series available but only for building Simulation Number 0
    # Figures={}
    # UniqueUnit = list(set(TimeSerieUnit))
    # for Unit in UniqueUnit:
    #     Figures[Unit] = Utilities.createMultilFig('', 2, linked=False)
    # for i,serie in enumerate(TimeSerieList):
    #     try:
    #         #Timecomp[i] =  Utilities.createMultilFig('',2,linked=False)
    #         plotTimeSeries(Res,Figures[TimeSerieUnit[i]],Names4Plots,'HeatedArea',serie,TimeSerieUnit[i],SimNum =[])
    #     except:
    #         pass

    plt.show()