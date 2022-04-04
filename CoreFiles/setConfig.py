# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import yaml, os
import distutils.spawn


def is_tool(name):
#it will return the path of the executable or None if not installed
  return distutils.spawn.find_executable(name) is not None

def read_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

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

def checkGlobalConfig(config):
    #lets check for the paths
    if not is_tool(os.path.join(config['0_APP']['PATH_TO_ENERGYPLUS'],'energyplus')):
        print(' /!\ ERROR /!\ ')
        print('It seems that the path to EnergyPlus is missing, please specify it in your local.yml')
        return 'EnergyPlus path'
    #lets check for the weather file needed for EnergyPlus
    if not os.path.isfile(os.path.join(os.path.abspath(config['0_APP']['PATH_TO_ENERGYPLUS']),config['2_SIM']['1_WeatherFile']['Loc'])):
        print(' /!\ ERROR /!\ ')
        print('It seems that the given Weatherfile to EnergyPlus is missing')
        print('Please check if : '+config['2_SIM']['1_WeatherFile']['Loc'] +' is present in : '+os.path.abspath(config['0_APP']['PATH_TO_ENERGYPLUS']))
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
    return config


# path2file = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CoreFiles'
# path2read = os.path.join(path2file,'DefaultConfigTest.yml')
#
# tutu = read_yaml(path2read)