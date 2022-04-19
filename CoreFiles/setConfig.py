# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import yaml, os
import distutils.spawn


def is_tool(name):
#it will return the path of the executable or None if not installed
  return distutils.spawn.find_executable(name) is not None

def read_yaml(file_path):
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    return config

def check4localConfig(config,path):
    Liste = os.listdir(path)
    new_config = config
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
    new_config, msg1 = ChangeConfigOption(config, localConfig)
    return new_config, filefound, msg1 if not msg else msg

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
            return errormsg, SepThreads
        if len(config['2_CASE']['1_SimChoices']['VarName2Change']) > len(config['2_CASE']['1_SimChoices']['Bounds']) or \
                len(config['2_CASE']['1_SimChoices']['VarName2Change']) > len(
            config['2_CASE']['1_SimChoices']['ParamMethods']):
            errormsg = '/!\ VarName2Change [list of str], Bounds [list of lists of float or int] and ParamMethods [list of str] must have the same length'
            return errormsg,SepThreads
        else:
            for idx, key in enumerate(config['2_CASE']['1_SimChoices']['VarName2Change']):
                if type(config['2_CASE']['1_SimChoices']['Bounds'][idx]) != list:
                    errormsg = '/!\ Bounds must be a list of lists of 2 values for each VarName2Change'
                    return errormsg,SepThreads
                elif config['2_CASE']['1_SimChoices']['Bounds'][idx][1] < \
                        config['2_CASE']['1_SimChoices']['Bounds'][idx][0]:
                    errormsg = '/!\ Bounds must be [lower bound, upper bounds] in this order'
                    return errormsg,SepThreads
    if config['2_CASE']['1_SimChoices']['NbRuns'] > 1:
        SepThreads = True
        if config['2_CASE']['2_AdvancedChoices']['CreateFMU']:
            errormsg = '/!\ It is asked to ceate FMUs but more than one simulation per building is asked...'
            return errormsg, SepThreads
        if not config['2_CASE']['1_SimChoices']['VarName2Change'] or not config['2_CASE']['1_SimChoices']['Bounds']:
            if not config['2_CASE']['2_AdvancedChoices']['FromPosteriors']:
                errormsg = '/!\ It is asked to make several runs but no variable is specified with range of variation'
                return errormsg, SepThreads
    return errormsg, SepThreads

def checkChoicesCombinations(config):
    errormsg, SepThreads = checkParamtricSimCases(config)
    if errormsg:
        print('###  INPUT ERROR ### ')
        print(errormsg)
        return 'Choices combination issue', SepThreads
    return config,SepThreads

# path2file = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CoreFiles'
# path2read = os.path.join(path2file,'DefaultConfigTest.yml')
#
# tutu = read_yaml(path2read)