# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import yaml, os, sys, json
import distutils.spawn
import core.GeneralFunctions as GrlFct
import building_geometry.GeomUtilities as GeomUtilities
import building_geometry.BuildingObject as BldFct
from sympy.codegen import Print
from sympy.codegen.ast import continue_
from default.data.Basic.Generate_CityModeller import ShapeCityPlanner
import default.data.Basic.Data4ExternalStudy as ExStudy




def is_tool(name):
#it will return the path of the executable or None if not installed
    return distutils.spawn.find_executable(name) is not None

def read_yaml(file_path):
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    return config

def check4localConfig(path, RetrofitConfigPath = ''):
    ListeAll = os.listdir(path) + os.listdir(RetrofitConfigPath) if RetrofitConfigPath != '' else os.listdir(path)
    localConfig = ''
    localRetConfig = ''
    Retfilefound = False
    filefound = False
    msg1 = False
    msg2 = False
    ymlFiles = ['DefaultConfig.yml','DefaultConfigKeyUnit.yml','env.default.yml','env.yml', 'RetrofitConfig.yml', 'RetrofitConfigKeyUnit.yml']
    for idx, file in enumerate(ListeAll):
        if '.yml' in file:
            if file not in ymlFiles:
                if not 'ecm' in file.lower():
                    msg1 = '/!\ More than one *.yml file other than the template was found'
                    localConfig = read_yaml(os.path.join(path,file))
                    filefound = os.path.join(path,file)
                elif RetrofitConfigPath != '' and 'ecm' in file.lower():
                    msg2 = '/!\ More than one *.yml file found for retrofitting'
                    localRetConfig = read_yaml(os.path.join(RetrofitConfigPath,file))
                    Retfilefound = os.path.join(path,file)
                else:
                    pass
    if not filefound:
        localConfig = read_yaml(os.path.join(path, 'DefaultConfig.yml'))
        filefound = os.path.join(path,'DefaultConfig.yml')
    # if not RetrofitConfigPath != None and Retfilefound:
    #     localRetConfig = read_yaml(os.path.join(RetrofitConfigPath, 'RetrofitConfig.yml'))
    #     Retfilefound = os.path.join(RetrofitConfigPath,'RetrofitConfig.yml')
    return localConfig, filefound, msg1, localRetConfig, Retfilefound, msg2

def ChangeConfigOption(config,localConfig):
    msg = False
    for Mainkey in localConfig.keys():
        if type(localConfig[Mainkey]) == dict:
            for subkey1 in localConfig[Mainkey].keys():
                if type(localConfig[Mainkey][subkey1]) == dict:
                    for subkey2 in localConfig[Mainkey][subkey1].keys():
                        if type(localConfig[Mainkey][subkey1][subkey2]) == dict:
                            for subkey3 in localConfig[Mainkey][subkey1][subkey2].keys():
                                if subkey3 not in config[Mainkey][subkey1][subkey2].keys():
                                    msg = '[Warning Config] '+Mainkey +' : '+ subkey1 +' : '+ subkey2 + ' : '+ subkey3+\
                                          ' is unknown from the DefaultConfig.yml. It will be ignored.'
                                else:
                                    config[Mainkey][subkey1][subkey2][subkey3] = localConfig[Mainkey][subkey1][subkey2][subkey3]
                        else:
                            if subkey2 not in config[Mainkey][subkey1].keys():
                                msg = '[Warning Config] '+Mainkey +' : '+ subkey1 +' : '+subkey2 + ' is unknown from the DefaultConfig.yml. It will be ignored.'
                            else:
                                config[Mainkey][subkey1][subkey2] = localConfig[Mainkey][subkey1][subkey2]
                else:
                    if subkey1 not in config[Mainkey].keys():
                        msg = '[Warning Config] '+Mainkey +' : '+subkey1 + ' is unknown from the DefaultConfig.yml. It will be ignored.'
                    else:
                        config[Mainkey][subkey1] = localConfig[Mainkey][subkey1]
        else:
            if Mainkey not in config.keys():
                msg = '[Warning Config] '+ Mainkey+ ' is unknown from the DefaultConfig.yml. It will be ignored.'
            else:
                config[Mainkey] = localConfig[Mainkey]
    return config,msg

def checkUnit(key):
    if type(key) == list:
        if len(key) ==0 :
            return []
        elif type(key[0]) == list:
            return [type(a) for b in key for a in b]
        else:
            return [type(a) for a in key]
    else:
        return [type(key)]

def checkConfigUnit(config,Unit):
    for Mainkey in Unit.keys():
        if type(Unit[Mainkey]) == dict:
            for subkey1 in Unit[Mainkey].keys():
                if type(Unit[Mainkey][subkey1]) == dict:
                    for subkey2 in Unit[Mainkey][subkey1].keys():
                        if type(Unit[Mainkey][subkey1][subkey2]) == dict:
                            for subkey3 in Unit[Mainkey][subkey1][subkey2].keys():
                                test = checkUnit(config[Mainkey][subkey1][subkey2][subkey3])
                                check = [eval(a) for a in Unit[Mainkey][subkey1][subkey2][subkey3]]
                                if False in [ch in check for ch in test]  and test:
                                    msg = (Mainkey+' : '+subkey1+' : '+subkey2+' : '+subkey3+' : ' +
                                           str(config[Mainkey][subkey1][subkey2][subkey3])+
                                           ' is not conform with input type, Please check the config.yml file')
                                    return msg
                        else:
                            test = checkUnit(config[Mainkey][subkey1][subkey2])
                            check = [eval(a) for a in Unit[Mainkey][subkey1][subkey2]]
                            if False in [ch in check for ch in test] and test:
                                msg = (Mainkey + ' : ' + subkey1 + ' : ' + subkey2 +' : ' +
                                       str(config[Mainkey][subkey1][subkey2]) +
                                       ' is not conform with input type, Please check the config.yml file')
                                return msg
                else:
                    test = checkUnit(config[Mainkey][subkey1])
                    check = [eval(a) for a in Unit[Mainkey][subkey1]]
                    if False in [ch in check for ch in test]  and test:
                        msg = (Mainkey + ' : ' + subkey1 +' : '+
                               str(config[Mainkey][subkey1]) + ' is not conform with input type, Please check the config.yml file')
                        return msg
        else:
            test = checkUnit(config[Mainkey])
            check = [eval(a) for a in Unit[Mainkey]]
            if [ch not in check for ch in test]:
                msg = (Mainkey + ' : '+ str(config[Mainkey])+' is not conform with input type, Please check the config.yml file')
                return msg
    return config

def checkGlobalConfig(config):
    #lets check for the paths
    if not is_tool(os.path.join(config['0_APP']['PATH_TO_ENERGYPLUS'],'energyplus')):
        print(' /!\ ERROR /!\ ')
        print('It seems that the path to EnergyPlus is missing, please specify it in your local.yml')
        return 'EnergyPlus path',False
    #lets check for the weather file needed for EnergyPlus
    if not os.path.isfile(os.path.join(os.path.abspath(config['0_APP']['PATH_TO_ENERGYPLUS']),config['3_SIM']['1_WeatherData']['WeatherDataFile'])):
        print(' /!\ ERROR /!\ ')
        print('It seems that the given Weatherfile to EnergyPlus is missing')
        print('Please check if : '+config['3_SIM']['1_WeatherFile']['Loc'] +' is present in : '+os.path.abspath(config['0_APP']['PATH_TO_ENERGYPLUS']))
        return 'EnergyPlus Weather path',False
    #lets check for the geojsonfile:
    ok = []
    if os.path.isdir(os.path.abspath(config['1_DATA']['PATH_TO_DATA'])):
        liste = os.listdir(config['1_DATA']['PATH_TO_DATA'])
        ok = [file for file in liste if '.geojson' in file]
    else:
        if '.geojson' in config['1_DATA']['PATH_TO_DATA']:
            ok = True
    if not ok:
        return 'DATA path',False
    config,SepThreads =  checkChoicesCombinations(config)
    return config,SepThreads

def checkParamtricSimCases(config):
    SepThreads = False
    errormsg = False
    if len(config['2_CASE']['1_SimChoices']['VarName2Change']) > 0:
        if type(config['2_CASE']['1_SimChoices']['VarName2Change']) != list:
            errormsg = '/!\ The VarName2Change must be a list either empty or a list of strings'
            return config,errormsg, SepThreads
        if len(config['2_CASE']['1_SimChoices']['VarName2Change']) > len(config['2_CASE']['1_SimChoices']['Bounds']) or \
                len(config['2_CASE']['1_SimChoices']['VarName2Change']) > len(
            config['2_CASE']['1_SimChoices']['ParamMethods']):
            errormsg = '/!\ VarName2Change [list of str], Bounds [list of lists of float or int] and ParamMethods [list of str] must have the same length'
            return config,errormsg,SepThreads
        else:
            for idx, key in enumerate(config['2_CASE']['1_SimChoices']['VarName2Change']):
                if type(config['2_CASE']['1_SimChoices']['Bounds'][idx]) != list:
                    errormsg = '/!\ Bounds must be a list of lists of 2 values for each VarName2Change'
                    return config,errormsg,SepThreads
                elif config['2_CASE']['1_SimChoices']['Bounds'][idx][1] < \
                        config['2_CASE']['1_SimChoices']['Bounds'][idx][0]:
                    errormsg = '/!\ Bounds must be [lower bound, upper bounds] in this order'
                    return config,errormsg,SepThreads
    if config['2_CASE']['1_SimChoices']['NbRuns'] > 1:
        if config['2_CASE']['2_AdvancedChoices']['CreateFMU']:
            errormsg = '/!\ It is asked to create FMUs but more than one simulation per building is asked...'
            return config,errormsg, SepThreads
        if not config['2_CASE']['1_SimChoices']['VarName2Change'] or not config['2_CASE']['1_SimChoices']['Bounds']:
            if not config['2_CASE']['2_AdvancedChoices']['FromPosteriors']:
                errormsg = '/!\ It is asked to make several runs but no variable is specified with range of variation'
                return config,errormsg, SepThreads
        if config['2_CASE']['0_GrlChoices']['MakePlotsOnly']:
            config['2_CASE']['1_SimChoices']['NbRuns'] = 1
            return config,errormsg, SepThreads
        SepThreads = True
    return config,errormsg, SepThreads

def checkChoicesCombinations(config):
    config,errormsg, SepThreads = checkParamtricSimCases(config)
    if errormsg:
        print('###  INPUT ERROR ### ')
        print(errormsg)
        return 'Choices combination issue', SepThreads
    return config,SepThreads

def grabBuildingsId(IdsFile):
    if os.path.isfile(IdsFile):
        with open(IdsFile, 'r') as file:
            Lines = file.readlines()
        BldIds = [line.split('\t')[1][:-1] for lidx,line in enumerate(Lines) if lidx>0]
    else:
        BldIds = []
        print('[Info] No ListOfBuilding_Ids.txt file was found, all building in the geojson file will be considered')
    return BldIds

def getConfig(localDir, App = ''):
    defaultConfigPath = os.path.join(os.path.dirname(os.getcwd()), 'default', 'config')
    if App == 'Shadowing':
        ConfigFromArg, Case2Launch, ShadeLim = Read_Arguments(App = App)
    else:
        ConfigFromArg, Case2Launch = Read_Arguments(App = App)
    #first the default yml file is read to define the config dictionnary as well as the corresponding unit
    config = read_yaml(os.path.join(defaultConfigPath,'DefaultConfig.yml'))
    #lets get the environment variable and try if there is a new made one
    try: env = read_yaml(os.path.join(defaultConfigPath, 'env.yml'))
    except: env = read_yaml(os.path.join(defaultConfigPath, 'env.default.yml'))
    # make the change for the env variable
    config, msg = ChangeConfigOption(config, env)

    RetrofitConfigPath = os.path.join(localDir[:localDir.find('mubes-ubem') + 11], 'bin/Retrofit')
    DefaulRetConfigUnit = read_yaml(os.path.join(RetrofitConfigPath, 'RetrofitConfigKeyUnit.yml'))
    Retrofit_config = read_yaml(os.path.join(RetrofitConfigPath, 'RetrofitConfig.yml'))
    # if msg: print(msg)
    if App == 'Shadowing':
        configUnit = read_yaml(os.path.join(defaultConfigPath, 'DefaultConfigKeyUnit.yml'))
    else:
        configUnit = read_yaml(os.path.join(defaultConfigPath, 'DefaultConfigKeyUnit.yml'))
    geojsonfile = False
    if Case2Launch:
        #this case is if a folder Name has been given, the local yml file will be read to make the config dictionary
        CaseFolder1 = os.path.join(localDir,Case2Launch)
        CaseFolder2 = Case2Launch
        #localConfig4Path, filefound, msg = check4localConfig(os.getcwd())
        if not os.path.isfile(os.path.join(CaseFolder1, 'ConfigFile.yml')) and not os.path.isfile(os.path.join(CaseFolder2, 'ConfigFile.yml')):
            print('[Unknown Case] the following folder was not found : ' + Case2Launch)
            sys.exit()
        else:
            try: localConfig = read_yaml(os.path.join(CaseFolder1, 'ConfigFile.yml'))
            except: localConfig = read_yaml(os.path.join(CaseFolder2, 'ConfigFile.yml'))
            config, msg = ChangeConfigOption(config, localConfig)
            if msg: print(msg)
            if 'See ListOfBuiling_Ids.txt for list of IDs' in config['2_CASE']['1_SimChoices']['BldID']:
                IdsFile = os.path.join(os.path.abspath(localConfig['0_APP']['PATH_TO_RESULTS']), Case2Launch,
                                       'ListOfBuiling_Ids.txt')
                config['2_CASE']['1_SimChoices']['BldID'] = grabBuildingsId(IdsFile)

            Retrofit = config['2_CASE']['1_SimChoices']['Retrofit']
            if Retrofit and not config['2_CASE']['0_GrlChoices']['MakePlotsOnly']:
                # msg = f'[Prep. Info] Retrofitting mode activated...'
                RetrofitConfigPath = os.path.join(localDir[:localDir.find('mubes-ubem') + 11], 'bin/Retrofit')
                DefaulRetConfigUnit = read_yaml(os.path.join(RetrofitConfigPath, 'RetrofitConfigKeyUnit.yml'))
                Retrofit_config = read_yaml(os.path.join(RetrofitConfigPath, 'RetrofitConfig.yml'))
                # print(msg)

            else:
                # msg = f'[Retrofit. Info] Retrofitting mode not activated (PlotOnly == True)...'
                RetrofitConfigPath = None
                Retrofit_config = None
                Retrofit = False
                # print(msg)



    elif len(ConfigFromArg) > 0:
        if type(ConfigFromArg[0]) == str:
            for xidx, xArg in enumerate(ConfigFromArg):
                if xArg[-4:] == '.yml' and not 'ecm' in xArg.lower():
                    #this case is if a yml file is given
                    ymlfile1 = os.path.join(localDir, xArg)
                    ymlfile2 = xArg
                    if not os.path.isfile(ymlfile1) and not os.path.isfile(ymlfile2):
                        print('[Error] yml file not found : '+os.path.abspath(xArg))
                        sys.exit()
                    try: localConfig = read_yaml(ymlfile1)
                    except:
                        try: localConfig = read_yaml(ymlfile2)
                        except:
                            print('[Error] The .yml file failed to be loaded, please check if the file')
                            sys.exit()
                    config, msg = ChangeConfigOption(config, localConfig)
                    if msg: print(msg)
                    if 'See ListOfBuiling_Ids.txt for list of IDs' in config['2_CASE']['1_SimChoices']['BldID']:
                        IdsFile = os.path.join(os.path.dirname(ConfigFromArg),'ListOfBuiling_Ids.txt')
                        config['2_CASE']['1_SimChoices']['BldID'] = grabBuildingsId(IdsFile)
                    #this case is if a geojson file is given (for the MakeShadowingWallFile purpose only

                elif 'ecm' in xArg.lower() and xArg[-4:] == '.yml':
                    ymlfile1 = os.path.join(localDir, xArg)
                    ymlfile2 = xArg
                    if not os.path.isfile(ymlfile1) and not os.path.isfile(ymlfile2):
                        print('[Retrofit Error] yml file not found : '+os.path.abspath(xArg))
                        sys.exit()
                    try:
                        localRetConfig = read_yaml(ymlfile1)
                    except:
                        try:
                            localRetConfig = read_yaml(ymlfile2)
                        except:
                            print('[Retrofit Error] The .yml file failed to be loaded, please check if the file')
                            sys.exit()
                    Retrofit = config['2_CASE']['1_SimChoices']['Retrofit']
                    if Retrofit:
                        Retrofit_config, msg = ChangeConfigOption(Retrofit_config, localRetConfig)
                        if msg: print(msg)
                    else: Retrofit_config = None

                elif ConfigFromArg[-8:] == '.geojson':
                    geojsonfile = True
                else:
                     print('[Unknown Argument] Please check the available options for arguments : -yml or -CONFIG')
                     sys.exit()
    elif ConfigFromArg:
        #this case is if the local config is given directly through a json file fomrat (previously converted into a dictionary in the ReadArgument() function)
        config, msg = ChangeConfigOption(config, ConfigFromArg)
        if msg: print(msg)
        config['2_CASE']['0_GrlChoices']['OutputFile'] = 'Outputs4API.txt'
    else:
        #no specific element is given, the local yml in the defaultConfigPath will be used. some different than default could be placed in the same directory
        localConfig, filefound, msg1, localRetConfig, Retfilefound, msg2 = check4localConfig(defaultConfigPath, RetrofitConfigPath)
        if msg1:
            print(msg1)
            print('[Config Info] Config completed by ' + filefound)
            config, msg1 = ChangeConfigOption(config, localConfig)
        Retrofit = config['2_CASE']['1_SimChoices']['Retrofit']
        if Retrofit:
            if msg2:
                print(msg2)
                print('[Retrofit Config Info] Config completed by ' + Retfilefound)
                Retrofit_config, msg2 = ChangeConfigOption(Retrofit_config, localRetConfig)
        else: Retrofit_config = None

    #the Unit are checked
    # config, msg = ChangeConfigOption(config, env)

    #### at this stage the potential given files in command window, the additional files in default/config and bin/ECM were checked and
    ### changes applied to config files.
    #### now check config files to ensure the variables types are correct
    config = checkConfigUnit(config,configUnit)
    if type(config) != dict:
        print('[Config Error] Something seems wrong : \n' + config)
        sys.exit()
    config, SepThreads = checkGlobalConfig(config) # todo you cand septhreads in here
    if type(config) != dict:
        print('[Config Error] Something seems wrong in : ' + config)
        sys.exit()

    if not config['2_CASE']['0_GrlChoices']['MakePlotsOnly']:
        if Retrofit_config:
            Retrofit_config = checkConfigUnit(Retrofit_config ,DefaulRetConfigUnit)
            if type(Retrofit_config) != dict:
                print('[Config Error] Something seems wrong in : ' + Retrofit_config)
                sys.exit()
    else:
        Retrofit_config = None
        pass
## For External study
    if config['2_CASE']['1_SimChoices']['StockholmBuildings'] and config['2_CASE']['1_SimChoices']['ExternalStudy']:
        msg = f'Both GenDataset and ExternalStudy activated. StockholmBuildings is preferred'
        print(msg)
    if config['2_CASE']['1_SimChoices']['StockholmBuildings']:
        msg = f'[Data Info] Generating data in the format of City Modeler'
        print(msg)
        DataProductGen_Agent = ShapeCityPlanner()
        GeneratedCityPlanner = DataProductGen_Agent.GenCore()
        CaseName = config['2_CASE']['0_GrlChoices']['CaseName']
        Path2Data = config['1_DATA']['PATH_TO_DATA']
        DataDir = DataProductGen_Agent.SaveitGeoJson(os.getcwd()[: os.getcwd().find('ubem')+5], GeneratedCityPlanner, Path2Data, CaseName)
        config['1_DATA']['PATH_TO_DATA'] = '../' + DataDir[DataDir.find('examples'):]
# Lets check if External studies is enabled
    elif config['2_CASE']['1_SimChoices']['ExternalStudy']: #todo complete coding for external study
        msg = f'[Data Info] Generating data in the format of City Modeler from user input'
        print(msg)
        CaseName = config['2_CASE']['0_GrlChoices']['CaseName']
        Path2Data = config['1_DATA']['PATH_TO_DATA']
        DataTemplate = ExStudy.Read_json(os.path.join(localDir[:localDir.find('mubes-ubem')+11], 'default/data/Basic/CM_Template.geojson'))
        UserInput = ExStudy.Read_yml(os.path.join(localDir[:localDir.find('mubes-ubem')+11], 'default/data/Basic/UserManualInput.yml'))
        Agent = ExStudy.CityModellerFactory(UserInput, DataTemplate, CaseName, Path2Data)
        DataDir = Agent.MakeChanges()
        #We replace the data diectory to new dataset generated from user input in UserManualInput
        config['1_DATA']['PATH_TO_DATA'] = '../' + DataDir[DataDir.find('examples'):]
        config['2_CASE']['1_SimChoices']['BldID'] = []
        # coords = Agent.GenCoord(50, 'L')
        # Agent.PlotGeometry(coords['coords_floor'])

    Key2Aggregate = ['0_GrlChoices', '1_SimChoices', '2_AdvancedChoices']
    CaseChoices = {}
    for key in Key2Aggregate:
        for subkey in config['2_CASE'][key]:
            CaseChoices[subkey] = config['2_CASE'][key][subkey]
    if CaseChoices['Verbose']: print('[OK] Input config. info checked and valid.')
    if 'See ListOfBuiling_Ids.txt for list of IDs' in CaseChoices['BldID']:
        CaseChoices['BldID'] = []
    epluspath = config['0_APP']['PATH_TO_ENERGYPLUS']
    FMUScriptPath = config['0_APP']['PATH_TO_ENERGYPLUSFMUKit']
    SimDir = config
    RetrofitFiles = os.path.join(os.getcwd()[:os.getcwd().find('mubes-ubem')+11], 'bin/Retrofit')
    # a first keypath dict needs to be defined to comply with the current paradigm along the code
    Buildingsfile = os.path.abspath(config['1_DATA']['PATH_TO_DATA'])
    keyPath = {'epluspath': epluspath, 'Buildingsfile': Buildingsfile, 'FMUScriptPath': FMUScriptPath,'pythonpath': '', 'GeojsonProperties': '', 'RetrofitFiles': RetrofitFiles}
    if geojsonfile:
        keyPath['Buildingsfile'] = ConfigFromArg
    # this function makes the list of dictionary with single input files if several are present in the sample folder
    GlobKey, MultipleFiles = GrlFct.ListAvailableFiles(keyPath)
    if App == 'Shadowing':
        return GlobKey, config, ShadeLim
    # this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    IDKeys = config['3_SIM']['GeomElement']['BuildIDKey']
    CoordSys = config['1_DATA']['EPSG_REF']
    if MultipleFiles:
        CaseChoices['PassBldObject'] = False
    Pool2Launch, CaseChoices['BldID'], CaseChoices['DataBaseInput'], CaseChoices['BldIDKey'], AllBldIDs = CreatePool2Launch(CaseChoices['BldID'],
                    GlobKey, IDKeys,CaseChoices['PassBldObject'],CaseChoices['RefBuildNum'],CaseChoices['RefPerimeter'],CoordSys)

    if not config['2_CASE']['0_GrlChoices']['MakePlotsOnly'] :
        if Retrofit_config:
            msg = f'[Prep. Info] Retrofitting mode activated...'
            print(msg)
            RetChoice = {}
            for key in Retrofit_config['0_SIM']:
                for subkey in Retrofit_config['0_SIM'][key]:
                    RetChoice[subkey] = Retrofit_config['0_SIM'][key][subkey]
            Pool2Retrofit, MatchedBld, Pool2Launch = CreatePool2Retrofit(RetChoice['ECM_to_Implement'], RetChoice['BuildID'], CaseChoices['BldID'], AllBldIDs, Pool2Launch, GlobKey[0]['RetrofitFiles'])
        else: Pool2Retrofit = None
    else:
        Pool2Retrofit = None
        msg = f'[Retrofit Info] Exiting retrofit mode. PlotOnly is activated'
        print(msg)
    return CaseChoices,config, SepThreads,Pool2Launch,MultipleFiles, Retrofit_config, Pool2Retrofit

def Read_Arguments(App = ''):
    #these are defaults values:
    Config2Launch = []
    Case2Launch = []
    ShadeLim =[]
    # Get command-line options.
    lastIdx = len(sys.argv) - 1
    currIdx = 1
    while (currIdx < lastIdx):
        currArg = sys.argv[currIdx]
        if (currArg.startswith('-CONFIG')):
            currIdx += 1
            Config2Launch = json.loads(sys.argv[currIdx])
        if (currArg.startswith('-yml')):
            currIdx += 1
            Config2Launch.append(sys.argv[currIdx])
        if (currArg.startswith('-Case')):
            currIdx += 1
            Case2Launch = sys.argv[currIdx]
        if (currArg.startswith('-ShadeLimits')):
            currIdx += 1
            ShadeLim = sys.argv[currIdx]
        if (currArg.startswith('-geojson')):
            currIdx += 1
            Config2Launch = sys.argv[currIdx]
        currIdx += 1
    if App == 'Shadowing': return Config2Launch,Case2Launch, ShadeLim
    else: return Config2Launch,Case2Launch

def CreatePool2Launch(BldIDs,GlobKey,IDKeys,PassBldObject,RefBuildNum,RefDist,CoordSys):
    Pool2Launch = []
    NewUUIDList = []
    AllBldIDs = []
    for nbfile,keyPath in enumerate(GlobKey):
        print('[Prep. Info] Reading GeoJson file...' )
        try : DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath,CoordSys,toBuildPool = True if not PassBldObject else False)
        except:
            print('[Error] This input file failed to be loaded : '+str(keyPath['Buildingsfile']))
            if nbfile==len(GlobKey)-1: sys.exit()
            else: continue
        #check of the building to run
        idx = len(Pool2Launch)
        IdKey = 'NoBldID'
        Id, BuildIdKey = BldFct.getDBValue(DataBaseInput['Build'][0].properties, IDKeys)
        if BuildIdKey:
            IdKey = BuildIdKey
        print('[Prep. Info] Buildings will be considered with ID key : '+IdKey )
        ReducedArea = False
        if type(RefBuildNum)==int:
            if RefBuildNum > len(DataBaseInput['Build']):
                print('###  INPUT ERROR ### ')
                print('/!\ RefBuildNum is greater than the number of object in the input GeoJson file...')
                print('/!\ Please, check you inputs.')
                sys.exit()
            ReducedArea = True
            ref = DataBaseInput['Build'][RefBuildNum].geometry.centroid
            ref = ref[0] if type(ref)==list else ref
        for bldNum, Bld in enumerate(DataBaseInput['Build']):
            if ReducedArea:
                try: coordCheck = Bld.geometry.centroid
                except: continue
                coordCheck = coordCheck[0] if type(coordCheck) == list else coordCheck
                if GeomUtilities.getDistance(ref,coordCheck)>RefDist:
                    continue
            if not BldIDs:
                try: BldID = Bld.properties[IdKey]
                except: BldID = 'NoBldID'
                Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum,'BuildID':BldID ,'TotBld_and_Origin':'','CoordSys':CoordSys , 'Ret' : {'ToRet':'', 'RetPath':''}})
                try:
                    NewUUIDList.append(Bld.properties[IdKey])
                    AllBldIDs = NewUUIDList
                except: pass
            else:
                try:
                    if Bld.properties[IdKey] in BldIDs:
                        Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum,'BuildID':Bld.properties[IdKey], 'TotBld_and_Origin':'','CoordSys':CoordSys, 'Ret' : {'ToRet':'', 'RetPath':''}})
                        NewUUIDList.append(Bld.properties[IdKey])
                    AllBldIDs.append(Bld.properties[IdKey])
                except: pass
        if not Pool2Launch:
            print('###  INPUT ERROR ### ')
            print('/!\ None of the building BldID were found in the input GeoJson file...')
            print('/!\ Please, check you inputs.')
            sys.exit()
        Pool2Launch[idx]['TotBld_and_Origin'] = str(len(Pool2Launch)-idx) +' buildings will be considered from '+os.path.basename(keyPath['Buildingsfile'])
        print('[Prep. Info] '+ str(len(Pool2Launch)-idx) +' buildings will be considered out of '+str(bldNum+1)+' in the input file ')
    return Pool2Launch,NewUUIDList,DataBaseInput if PassBldObject else [],IdKey, AllBldIDs

def CreatePool2Retrofit(ECMs, BuildID2Ret, CaseChoices, AllBldIDs, Pool2Launch, RetPath):
    Pool2Retrofit = []
    mismatch = []
    match = []
    BuildNum2Retrofit = []
    notKnown = []
    if len(BuildID2Ret) > 0:
        for mtch in BuildID2Ret:
            if mtch in CaseChoices:
                match.append(mtch)
                BuildNum2Retrofit.append(AllBldIDs.index(mtch))
                Pool2Retrofit.append({'BuildID': mtch, 'BuildNum2Ret': AllBldIDs.index(mtch), 'Matchedbuildings': True,'RetAll' : False, 'ECMs': ECMs, 'RetrofitPath' : RetPath})

            elif mtch not in (CaseChoices and AllBldIDs):
                msg = (f"[Retrofit Info] The selected Building ID '{mtch}' for retrofitting does not match any Building ID in the database.\n"
                       f"[Retrofit Info] 'Building with ID {mtch}' will be excluded from retrofitting")
                print(msg)
                notKnown.append(mtch)
            elif mtch in AllBldIDs and mtch not in CaseChoices:
                mismatch.append(mtch)

        msg = f"[Retrofit Info] {len(match)} {'buildings' if len(match)>1 else 'building' } out of {len(CaseChoices)} will be retrofitted with {ECMs}."
        print(msg)
        if len(match) == 0:
            Pool2Retrofit = None
            msg = f'[Retrofit Info] Exiting retrofit mode... (zero building to retrofit)'
            print(msg)
    elif not BuildID2Ret:
        match = 'RetAll'
        Pool2Retrofit.append({'BuildID': 'All', 'BuildNum2Ret': 'All', 'Matchedbuildings': True, 'RetAll' : True, 'ECMs': ECMs, 'RetrofitPath' : RetPath})


    if match == 'RetAll':
        for i in range(len(Pool2Launch)):
            Pool2Launch[i]['ToRet'] = True
    elif len(match) > 0:
        for i in range(len(Pool2Launch)):
            if Pool2Launch[i]['BuildID'] in match:
                Pool2Launch[i]['Ret']['ToRet'] = True
                Pool2Launch[i]['Ret']['RetPath'] = RetPath
            else:
                Pool2Launch[i]['Ret']['ToRet'] = False
    else:
        pass

    return Pool2Retrofit, match, Pool2Launch
