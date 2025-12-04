# @Author  :Mohammadhossein Alizadeh
# @Email   : alizad@kth.st@kth.se

import os
import json
import sys

import pandas as pd
import yaml
import numpy as np
from shapely.geometry import Polygon
from pyproj import Transformer
import math
import re
import geopandas as gpd
import fiona
import copy  # Only once at the top of your script
import shutil

def read_geojson(self, Path):
    geodata = gpd.read_file(Path)
    return geodata

def readCSV(Path):
    return pd.read_csv(Path, delimiter=";", low_memory=False)

def Read_json(Path):
    try:
        with open(Path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # Load JSON data into a Python dictionary
        return data
    except FileNotFoundError:
        print(f"Error: The file '{Path}' was not found.")

def Read_yml(Path):
    with open(Path, "r") as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
        return data

def readGjsonFiona(Path):
    selected_data = []
    with fiona.open(Path) as src:
        for feature in src:
            selected_entry = {
                "50A_UUID": feature["properties"].get("50A_UUID"),
                "FootPrints": feature['geometry'].get("coordinates"),
                "FormularID": feature["properties"].get("FormularId"),
                "FNR" : feature["properties"].get("FNR"),
            }
            selected_data.append(selected_entry)
    return selected_data

# def Find_UUIDfromAddress():

def clean_nans(obj):
    """Recursively clean NaNs, Series, and NumPy types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    elif isinstance(obj, (pd.Series, np.ndarray)):
        # Convert Series to list and clean each item
        return [clean_nans(x) for x in obj.tolist()]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return None if math.isnan(obj) else float(obj)
    elif pd.isna(obj):  # catches pd.NA and np.nan
        return None
    elif obj == "":
        return ""
    else:
        return obj
# This class contains everything required to creat CityModeller from datasets to functions
# There is a template of CityModeller in dir with name CM_Template that we use to generate CityModeller
class ShapeCityPlanner():
    def __init__(self, path):
        self.Mainpath = path #os.getcwd()[: os.getcwd().find('bin')]
        self.config = Read_yml(os.path.join(self.Mainpath, 'default/data/Basic/CityModellerConfig.yml'))
        self.cpBuildings = readCSV(os.path.join(self.Mainpath, self.config['0_Setup']['cpBuildings']))
        self.cpProperties = readCSV(os.path.join(self.Mainpath, self.config['0_Setup']['cpProperties']))
        self.cpNow = readCSV(os.path.join(self.Mainpath, self.config['0_Setup']['cpNow']))
        self.cpFootprints = readGjsonFiona(os.path.join(self.Mainpath,self.config['0_Setup']['cpFootprints']))
        self.template = Read_json(os.path.join(self.Mainpath, self.config['0_Setup']['CityModeller_Tempalte']))
        if self.config['1_Sim']['InputType'] == "Address":
            try:
                self.AddressUUID_data = pd.read_excel(os.path.join(os.getcwd()[:os.getcwd().find('bin')], self.config['1_Sim']['address2UUID_DataPath']))
                self.User_Address = self.config['1_Sim']['Address']
                mask = self.AddressUUID_data['Building'].str.contains(self.User_Address, case=False, na=False)
                self.UUID = self.AddressUUID_data.loc[mask, '55A_UUIDREGBYG'].tolist()
            except:
                msg = f'No building UUID found with address {self.User_Address}'
                print(msg)
                sys.exit()
        elif self.config['1_Sim']['InputType'] == "UUID":
            if self.config['1_Sim']['UUID'] == "":
                self.All_UUID = []
                for samplebld in self.cpFootprints:
                    self.All_UUID.append(samplebld.get('50A_UUID'))
                    self.UUID = self.All_UUID
            else:
                self.UUID = self.config['1_Sim']['UUID']


        self.BldFootPrints = [FP for FP in self.cpFootprints if FP.get('50A_UUID') in self.UUID]
        self.coordinates = self.BldFootPrints[0].get('FootPrints')
        self.FormularID = self.BldFootPrints[0].get('FormularID')
        self.FNR = self.BldFootPrints[0].get('FNR')
        self.BldcpNow = self.cpNow[self.cpNow['FormularId'] == self.FormularID]
        self.BldcpProperties = self.cpProperties[self.cpProperties['FNR'] == float(self.FNR)]

    def GenCore(self):
        FirstRun = True
        Listofqout = {
            "43S_TILLBYAR", "43T_TILLBYAR",
            "EgenAtempBad", "EgenAtempButik", "EgenAtempHotell", "EgenAtempKontor",
            "EgenAtempKopcentrum", "EgenAtempLivsmedel", "EgenAtempOvrig", "EgenAtempOvrigaVad",
            "EgenAtempRestaurang", "EgenAtempSkolor", "EgenAtempTeater", "EgenAtempVard", "EgenAtempVardDag",
            "EgiBerElProduktion", "EgiBerEngProduktion", "EgiSolcell", "EgiSolvarme", "EgiVerksamhet"
        }
        # Here it loops through all UUID defined in CityModellerConfig['1_Sim']['UUID'] to create CityModeller for each of them
        for ID in self.UUID:
            ReplcaeTemplate = True
            if ReplcaeTemplate:
                template = copy.deepcopy(self.template)
            BldFootPrints = [FP for FP in self.cpFootprints if FP.get('50A_UUID') == ID]
            coordinates = BldFootPrints[0].get('FootPrints')
            FormularID = BldFootPrints[0].get('FormularID')
            if FormularID == None: continue
            FNR = BldFootPrints[0].get('FNR')
            BldcpNow = self.cpNow[self.cpNow['FormularId'] == FormularID]
            BldcpBuilding = self.cpBuildings[self.cpBuildings['50A_UUID'] == ID]
            Height = BldcpBuilding['STS_BYGG_H'].values[0].item()
            if math.isnan(Height):
                msg = f'[CityModeller Creation] Building {ID} is disregarded because has nan in height column STS_BYGG_H'
                print(msg)
                continue
            BldcpProperties = self.cpProperties[self.cpProperties['FNR'] == float(FNR)]
            template.get('features')[0]['type'] = 'Feature'
            template.get('features')[0]['geometry']['type'] = 'GeometryCollection'
            geomtype = template.get('features')[0]['geometry']['geometries'][0]['type']

            for keys in template.get('features')[0]['properties'].keys():
                if keys in self.cpNow.columns:
                    try:
                        if pd.isna(BldcpNow[keys].values[0].item()) and keys in Listofqout:
                            template.get('features')[0]['properties'][keys] = ""
                        else:
                            template.get('features')[0]['properties'][keys] = BldcpNow[keys].values[0].item() if type(
                                BldcpNow[keys].values[0]) is (np.int64 or np.float64) else BldcpNow[keys].values[0]
                    except:
                        template.get('features')[0]['properties'][keys] = BldcpNow[keys].item()
                elif keys in self.cpBuildings.columns:
                    try:
                        if pd.isna(BldcpNow[keys].values[0].item()) and keys in Listofqout:
                            template.get('features')[0]['properties'][keys] = ""
                        else:
                            template.get('features')[0]['properties'][keys] = BldcpBuilding[keys].values[0].item() if type(BldcpBuilding[keys].values[0]) is np.float64 else \
                            BldcpBuilding[keys].values[0]
                    except:
                        template.get('features')[0]['properties'][keys] = BldcpBuilding[keys].item()

                elif keys in self.cpProperties.columns:
                    try:
                        if pd.isna(BldcpNow[keys].values[0].item()) and keys in Listofqout:
                            template.get('features')[0]['properties'][keys] = ""
                        else:
                            template.get('features')[0]['properties'][keys] = BldcpProperties[keys].values[
                                0].item() if type(BldcpProperties[keys].values[0]) is np.float64 else \
                            BldcpProperties[keys].values[0]
                    except:
                        template.get('features')[0]['properties'][keys] = BldcpProperties[keys].item()
            for block in coordinates:
                for idx, Info in enumerate([block]):
                    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
                    coordinates_sweref99_Floor = [transformer.transform(lon, lat, 0) for lon, lat in Info]
                    coordinates_sweref99_Roof = [transformer.transform(lon, lat, Height) for lon, lat in Info]
                    polygon = Polygon(coordinates_sweref99_Roof)
                    coords_lists_sweref99_Roof = [[[list(coord) for coord in coordinates_sweref99_Roof]]]
                    coords_lists_sweref99_Floor = [[[list(coord) for coord in coordinates_sweref99_Floor]]]
                if ReplcaeTemplate:
                    template.get('features')[0]['geometry']['geometries'][0]['type'] = geomtype
                    template.get('features')[0]['geometry']['geometries'][0]['coordinates'] = coords_lists_sweref99_Roof
                    template.get('features')[0]['geometry']['geometries'][0]['coordinates'].append(
                        coords_lists_sweref99_Floor[0])
                    ReplcaeTemplate = False
                else:
                    template.get('features')[0]['geometry']['geometries'].append({'type': geomtype, 'coordinates': [
                        coords_lists_sweref99_Roof[0], coords_lists_sweref99_Floor[0]]})
            if FirstRun:
                MainFile = template.copy()
                FirstRun = False
            else:
                MainFile.get('features').append(template.get('features')[0])
        return MainFile, self.UUID
#The generated CityPlanner will be stored in directory specified in config['1_DATA]['PATH_TO_DATA']
# Define different name for your study to save data from stockholm in it
    def SaveitGeoJson(self, Mainpath, BuildingData, Path2Data, CaseName):
        # Replace this with your actual GeoJSON input dictionary
        geojson_cleaned = clean_nans(BuildingData)
        DataFolder = os.path.join(Mainpath,'examples', 'Data_for_'+CaseName)
            # os.path.join(f"{Mainpath}{Path2Data[3:]}"[:(f"{Mainpath}{Path2Data[3:]}").find('examples')+9], 'Data_for_'+CaseName)
        if os.path.exists(DataFolder):
            shutil.rmtree(DataFolder)
            os.mkdir(DataFolder)
        else:
            os.mkdir(DataFolder)
        # Dump to string with Unicode and indentation
        geojson_str = json.dumps(geojson_cleaned, indent=2, ensure_ascii=False)
        geojson_str = re.sub(
            r'\[\s*([-0-9.eE]+),\s*([-0-9.eE]+),\s*([-0-9.eE]+)\s*\]',
            r'[\1, \2, \3]', geojson_str)
        geojson_str = re.sub(
            r'\[\s*([-0-9.eE]+),\s*([-0-9.eE]+)\s*\]',
            r'[\1, \2]', geojson_str)
        # Save to GeoJSON file
        with open(DataFolder +'/Generated_Buildings.geojson', "w", encoding="utf-8") as f:
            f.write(geojson_str)
        return DataFolder