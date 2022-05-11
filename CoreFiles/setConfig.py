# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import yaml, os, sys, json
import distutils.spawn
import CoreFiles.GeneralFunctions as GrlFct
import BuildObject.GeomUtilities as GeomUtilities
import BuildObject.BuildingObject as BldFct


def is_tool(name):
#it will return the path of the executable or None if not installed
  return distutils.spawn.find_executable(name) is not None

def read_yaml(file_path):
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    return config

def check4localConfig(path):
    Liste = os.listdir(path)
    filefound = False
    msg = False
    for file in Liste:
        if '.yml' in file:
            if file != 'LocalConfig_Template.yml':
                if filefound:
                    msg = '/!\ More than one *.yml file other than the template was found'
                else:
                    localConfig = read_yaml(os.path.join(path,file))
                    filefound = os.path.join(path,file)
    if not filefound:
        localConfig = read_yaml(os.path.join(path, 'LocalConfig_Template.yml'))
        filefound =  os.path.join(path,'LocalConfig_Template.yml')
    return localConfig, filefound, msg

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
                                          ' is unknown from the DefaultConfig.yml.It will be ignored.'
                                else:
                                    config[Mainkey][subkey1][subkey2][subkey3] = localConfig[Mainkey][subkey1][subkey2][subkey3]
                        else:
                            if subkey2 not in config[Mainkey][subkey1].keys():
                                msg = '[Warning Config] '+Mainkey +' : '+ subkey1 +' : '+subkey2 + ' is unknown from the DefaultConfig.yml.It will be ignored.'
                            else:
                                config[Mainkey][subkey1][subkey2] = localConfig[Mainkey][subkey1][subkey2]
                else:
                    if subkey1 not in config[Mainkey].keys():
                        msg = '[Warning Config] '+Mainkey +' : '+subkey1 + ' is unknown from the DefaultConfig.yml.It will be ignored.'
                    else:
                        config[Mainkey][subkey1] = localConfig[Mainkey][subkey1]
        else:
            if Mainkey not in config.keys():
                msg = '[Warning Config] '+ Mainkey+ ' is unknown from the DefaultConfig.yml.It will be ignored.'
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
                                           'is not conform with input type, Please check the config.yml file')
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

def getConfig(App = ''):
    if App == 'Shadowing':
        ConfigFromArg, Case2Launch, ShadeLim = Read_Arguments(App = App)
    else:
        ConfigFromArg, Case2Launch = Read_Arguments(App = App)
    config = read_yaml(os.path.join(os.path.dirname(os.getcwd()),'CoreFiles','DefaultConfig.yml'))
    configUnit = read_yaml(os.path.join(os.path.dirname(os.getcwd()), 'CoreFiles', 'DefaultConfigKeyUnit.yml'))
    geojsonfile = False
    if Case2Launch:
        localConfig4Path, filefound, msg = check4localConfig(os.getcwd())
        print(os.path.join(os.path.abspath(config['0_APP']['PATH_TO_RESULTS']), Case2Launch, 'ConfigFile.yml'))
        if os.path.isfile(
                os.path.join(os.path.abspath(localConfig4Path['0_APP']['PATH_TO_RESULTS']), Case2Launch, 'ConfigFile.yml')):
            localConfig = read_yaml(
                os.path.join(os.path.abspath(localConfig4Path['0_APP']['PATH_TO_RESULTS']), Case2Launch, 'ConfigFile.yml'))
            config, msg = ChangeConfigOption(config, localConfig)
            if msg: print(msg)
        else:
            print('[Unknown Case] the following folder was not found : ' + os.path.join(
                os.path.abspath(localConfig4Path['0_APP']['PATH_TO_RESULTS']), Case2Launch))
            sys.exit()
    elif type(ConfigFromArg) == str:
        if ConfigFromArg[-4:] == '.yml':
            localConfig = read_yaml(ConfigFromArg)
            config, msg = ChangeConfigOption(config, localConfig)
            if msg: print(msg)
        elif ConfigFromArg[-8:] == '.geojson':
            geojsonfile = True
        else:
             print('[Unknown Argument] Please check the available options for arguments : -yml or -CONFIG')
             sys.exit()
    elif ConfigFromArg:
        config, msg = ChangeConfigOption(config, ConfigFromArg)
        if msg: print(msg)
        config['2_CASE']['0_GrlChoices']['OutputFile'] = 'Outputs4API.txt'
    else:
        localConfig,filefound,msg = check4localConfig(os.getcwd())
        if msg: print(msg)
        config, msg = ChangeConfigOption(config, localConfig)
        if msg: print(msg)
        print('[Config Info] Config completed by ' + filefound)
    config = checkConfigUnit(config,configUnit)
    if type(config) != dict:
        print('[Config Error] Something seems wrong : \n' + config)
        sys.exit()
    config, SepThreads = checkGlobalConfig(config)
    if type(config) != dict:
        print('[Config Error] Something seems wrong in : ' + config)
        sys.exit()
    Key2Aggregate = ['0_GrlChoices', '1_SimChoices', '2_AdvancedChoices']
    CaseChoices = {}
    for key in Key2Aggregate:
        for subkey in config['2_CASE'][key]:
            CaseChoices[subkey] = config['2_CASE'][key][subkey]
    if CaseChoices['Verbose']: print('[OK] Input config. info checked and valid.')
    if 'See ListOfBuiling_Ids.txt for list of IDs' in CaseChoices['BldID']:
        CaseChoices['BldID'] = []
    epluspath = config['0_APP']['PATH_TO_ENERGYPLUS']
    # a first keypath dict needs to be defined to comply with the current paradigme along the code
    Buildingsfile = os.path.abspath(config['1_DATA']['PATH_TO_DATA'])
    keyPath = {'epluspath': epluspath, 'Buildingsfile': Buildingsfile, 'pythonpath': '', 'GeojsonProperties': ''}
    if geojsonfile:
        keyPath['Buildingsfile'] = ConfigFromArg
    # this function makes the list of dictionnary with single input files if several are present inthe sample folder
    GlobKey, MultipleFiles = GrlFct.ListAvailableFiles(keyPath)
    if App == 'Shadowing':
        return GlobKey, config, ShadeLim
    # this function creates the full pool to launch afterward, including the file name and which buildings to simulate
    IDKeys = config['3_SIM']['GeomElement']['BuildIDKey']
    CoordSys = config['1_DATA']['EPSG_REF']
    if MultipleFiles:
        CaseChoices['PassBldObject'] = False
    Pool2Launch, CaseChoices['BldID'], CaseChoices['DataBaseInput'], CaseChoices['BldIDKey'] = CreatePool2Launch(CaseChoices['BldID'],
                    GlobKey, IDKeys,CaseChoices['PassBldObject'],CaseChoices['RefBuildNum'],CaseChoices['RefPerimeter'],CoordSys)
    return CaseChoices,config, SepThreads,Pool2Launch,MultipleFiles

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
            Config2Launch = sys.argv[currIdx]
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
    for nbfile,keyPath in enumerate(GlobKey):
        print('[Prep. Info] Reading GeoJson file...' )
        try : DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath,CoordSys,toBuildPool = True if not PassBldObject else False)
        except:
            print('[Error] This input file failed to be loaded : '+str(keyPath['Buildingsfile']))
            continue
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
                Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum,'BuildID':BldID ,'TotBld_and_Origin':'','CoordSys':CoordSys })
                try: NewUUIDList.append(Bld.properties[IdKey])
                except: pass
            else:
                try:
                    if Bld.properties[IdKey] in BldIDs:
                        Pool2Launch.append({'keypath': keyPath, 'BuildNum2Launch': bldNum,'BuildID':Bld.properties[IdKey], 'TotBld_and_Origin':'','CoordSys':CoordSys })
                        NewUUIDList.append(Bld.properties[IdKey])
                except: pass
        if not Pool2Launch:
            print('###  INPUT ERROR ### ')
            print('/!\ None of the building BldID were found in the input GeoJson file...')
            print('/!\ Please, check you inputs.')
            sys.exit()
        Pool2Launch[idx]['TotBld_and_Origin'] = str(len(Pool2Launch)-idx) +' buildings will be considered from '+os.path.basename(keyPath['Buildingsfile'])
        print('[Prep. Info] '+ str(len(Pool2Launch)-idx) +' buildings will be considered out of '+str(bldNum+1)+' in the input file ')
    return Pool2Launch,NewUUIDList,DataBaseInput if PassBldObject else [],IdKey