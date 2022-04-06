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
    for file in Liste:
        if '.yml' in file:
            localConfig = read_yaml(os.path.join(path,file))
            new_config = ChangeConfigOption(config,localConfig)
    return new_config

def ChangeConfigOption(config,localConfig):
    for Mainkey in localConfig.keys():
        if type(localConfig[Mainkey]) == dict:
            for subkey1 in localConfig[Mainkey].keys():
                if type(localConfig[Mainkey][subkey1]) == dict:
                    for subkey2 in localConfig[Mainkey][subkey1].keys():
                        if type(localConfig[Mainkey][subkey1][subkey2]) == dict:
                            for subkey3 in localConfig[Mainkey][subkey1][subkey2].keys():
                                config[Mainkey][subkey1][subkey2][subkey3] = localConfig[Mainkey][subkey1][subkey2][subkey3]
                        else:
                            config[Mainkey][subkey1][subkey2] = localConfig[Mainkey][subkey1][subkey2]
                else:
                    config[Mainkey][subkey1] = localConfig[Mainkey][subkey1]
        else:
            config[Mainkey] = localConfig[Mainkey]
    return config

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
        return 'EnergyPlus path'
    #lets check for the weather file needed for EnergyPlus
    if not os.path.isfile(os.path.join(os.path.abspath(config['0_APP']['PATH_TO_ENERGYPLUS']),config['3_SIM']['1_WeatherFile']['Loc'])):
        print(' /!\ ERROR /!\ ')
        print('It seems that the given Weatherfile to EnergyPlus is missing')
        print('Please check if : '+config['3_SIM']['1_WeatherFile']['Loc'] +' is present in : '+os.path.abspath(config['0_APP']['PATH_TO_ENERGYPLUS']))
        return 'EnergyPlus Weather path'
    #lets check for the geojsonfile:
    ok = []
    if os.path.isdir(os.path.abspath(config['1_DATA']['Buildingsfile'])):
        liste = os.listdir(config['1_DATA']['Buildingsfile'])
        ok = [file for file in liste if '.geojson' in file]
    else:
        if '.geojson' in config['1_DATA']['Buildingsfile']:
            ok = True
    if not ok:
        return 'DATA path'
    config,SepThreads =  checkChoicesCombinations(config)
    return config,SepThreads

def checkChoicesCombinations(config):
    if len(config['2_CASE']['1_SimChoices']['VarName2Change'])>0:
        if type(config['2_CASE']['1_SimChoices']['VarName2Change']) != list:
            print('###  INPUT ERROR ### ')
            print('/!\ The VarName2Change must be a list either empty or a list of strings')
            print('/!\ Please, check you inputs')
            return 'Choices combination issue', False
    if config['2_CASE']['1_SimChoices']['NbRuns']>1:
        SepThreads = True
        if config['2_CASE']['2_AdvancedChoices']['CreateFMU'] :
            print('###  INPUT ERROR ### ' )
            print('/!\ It is asked to ceate FMUs but the number of runs for each building is above 1...')
            print('/!\ Please, check you inputs as this case is not allowed yet')
            return 'Choices combination issue',False
        if not config['2_CASE']['1_SimChoices']['VarName2Change'] or not config['2_CASE']['1_SimChoices']['Bounds']:
            if not config['2_CASE']['2_AdvancedChoices']['FromPosteriors']:
                print('###  INPUT ERROR ### ')
                print('/!\ It is asked to make several runs but no variable is specified with range of variation...')
                print('/!\ Please, check you inputs VarName2Change and / or Bounds')
                return 'Choices combination issue',False
    else:
        SepThreads = False
    return config,SepThreads

# path2file = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CoreFiles'
# path2read = os.path.join(path2file,'DefaultConfigTest.yml')
#
# tutu = read_yaml(path2read)