import json, os
import pandas as pd
import yaml
import fiona
import numpy as np
from pyproj import Transformer, CRS
import re
import matplotlib.pyplot as plt
import geopandas as gpd
import math
import shutil


def read_geojson(Path):
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

class CityModellerFactory:
    def __init__(self, ManualConfig, CP_template, CaseName, Path2Data):
        self.CaseName = CaseName
        self.Path2Data = Path2Data
        self.ManualConfig = ManualConfig
        self.CP_template = CP_template
        self.height = self.ManualConfig['0_Bld_Opt']['height']
        self.MainPath = os.getcwd()[: os.getcwd().find('mubes-ubem') + 11]
    def MakeChanges(self):
        for keys in self.CP_template.get('features')[0]['properties'].keys():
            try:
                self.CP_template.get('features')[0]['properties'][keys] = self.ManualConfig['0_Bld_Opt'][keys]
            except: continue
        if self.ManualConfig['0_Bld_Opt']['Coordinates']:
            self.CoordSys = self.ManualConfig['0_Bld_Opt']['CoordSys']
            self.Coords = [tuple(coord) for coord in self.ManualConfig['0_Bld_Opt']['Coordinates']]
            self.CP_final = self.AddCoordinates()
        elif self.ManualConfig['0_Bld_Opt']['EgenAtemp']:
            self.Coords = None
            total_area = self.ManualConfig['0_Bld_Opt']['EgenAtemp']
            BldShape = self.ManualConfig['0_Bld_Opt']['BldShape']
            self.SyntheticCoord = self.GenCoord(total_area, BldShape)
            self.CP_final = self.AddCoordinates()

        geojson_cleaned = clean_nans(self.CP_final)
        geojson_str = json.dumps(
            geojson_cleaned,
            indent=2,
            ensure_ascii=False
        )
        geojson_str = re.sub(
            r'\[\s*([-0-9.eE]+),\s*([-0-9.eE]+),\s*([-0-9.eE]+)\s*\]',
            r'[\1, \2, \3]',
            geojson_str
        )
        geojson_str = re.sub(
            r'\[\s*([-0-9.eE]+),\s*([-0-9.eE]+)\s*\]',
            r'[\1, \2]',
            geojson_str
        )
        # Lets specify a folder to save the generated dataset in it
        DataFolder = os.path.join(f"{self.MainPath}{self.Path2Data[3:]}"[:(f"{self.MainPath}{self.Path2Data[3:]}").find('examples')+9], 'Data_for_'+self.CaseName)
        if os.path.exists(DataFolder):
            shutil.rmtree(DataFolder)
            os.mkdir(DataFolder)
        else:
            os.mkdir(DataFolder)
        # Save it in the created folder
        with open(os.path.join(DataFolder, "CityModeler.geojson"), "w", encoding="utf-8") as f:
            f.write(geojson_str)
        return DataFolder
        # return self.CP_final
# Here we add generated coord from Atemp or coords defined in yml file
    def AddCoordinates(self):
        if self.Coords and len(self.Coords) % 2 == 0:
            CRS_Type = self.guess_crs_from_coords(self.Coords)
            if CRS_Type != 'unknown':
                TransformedCoords_floor, TransformedCoords_roof = self.convert_to_epsg3006(self.Coords, self.CoordSys, CRS_Type)
                self.PlotGeometry(TransformedCoords_floor)

                self.CP_template.get('features')[0]['geometry']['geometries'][0]['coordinates'] = [[TransformedCoords_roof]]
                self.CP_template.get('features')[0]['geometry']['geometries'][0]['coordinates'].append([TransformedCoords_floor])
                return self.CP_template
            else:
                msg = '[Error] Unable to convert coordinates. Check if coordinates are in a geographic or projected CRS.'
                print(msg)
                SystemExit

        elif not self.Coords:
            self.CP_template.get('features')[0]['geometry']['geometries'][0]['coordinates'] = [[self.SyntheticCoord['coords_roof']]]
            self.CP_template.get('features')[0]['geometry']['geometries'][0]['coordinates'].append([self.SyntheticCoord['coords_floor']])
            return self.CP_template

    def guess_crs_from_coords(self, coords):
        """
        Guess if coordinates are in a geographic or projected CRS.
        Parameters:
        - coords: List of (x, y) tuples
        Returns:
        - 'geographic', 'projected', or 'unknown'
        """
        try:
            xs = [x for x, y in coords]
            ys = [y for x, y in coords]

            # Check if values fit typical lat/lon ranges
            if all(-180 <= x <= 180 for x in xs) and all(-90 <= y <= 90 for y in ys):
                return "geographic"
            # Check if values are large enough to be projected (e.g., meters)
            elif all(abs(x) > 1000 and abs(y) > 1000 for x, y in coords):
                return "projected"
            else:
                return "unknown"
        except Exception as e:
            print(f"Error during detection: {e}")
            return "unknown"

    def convert_to_epsg3006(self, Coords, CoordSys, CRS_Type):
        """
        Convert a list of coordinates from unknown CRS to EPSG:3006.
        Parameters:
        - coords: List of (x, y) tuples
        Returns:
        - List of transformed (x, y) in EPSG:3006
        """
        Coords.append(Coords[0])
        if CoordSys == 'EPSG:3006' and CRS_Type == 'projected':
            AdjCoord_floor = [(x, y, 0) for x, y in Coords]
            AdjCoord_roof = [(x, y, self.height) for x, y in Coords]
            return AdjCoord_floor, AdjCoord_roof
        elif CoordSys == 'EPSG:4326' and CRS_Type == 'geographic':
            # Set up transformer
            transformer = Transformer.from_crs(CRS.from_user_input(CoordSys), CRS.from_epsg(3006), always_xy=True)
            # Transform each coordinate
            transformed_floor = [transformer.transform(x, y, 0) for x, y in Coords]
            transformed_roof = [transformer.transform(x, y, self.height) for x, y in Coords]

            return transformed_floor, transformed_roof
        else:
            msg = f"[Error] Unable to convert coordinates from {CoordSys} to EPSG:3006. CRS type doesnt match with coordinates."
            print(msg)
            SystemExit

    def GenCoord(self, total_area, BldShape):
        """
        Generate L-shape coordinates given total area.
        Parameters:
            total_area (float): Total area of the L-shape in m²
            base_width (float): Optional fixed base width (default: sqrt of area)
            cut_ratio (tuple): (width%, height%) of the notch cutout
            origin (tuple): (x0, y0) origin point
            z (float): Elevation
        Returns:
            List of [x, y, z] coordinates forming a closed L-shape.
        """
        origin = (674056.2506249119, 6582140.614278449)
        if BldShape == 'L':
            base_width = math.sqrt(total_area)  # assume squareish
            cut_ratio = (0.5, 0.5)
        elif BldShape == 'R' or BldShape == '':
            base_width = 1.7 * math.sqrt(total_area) # assume squareish
            cut_ratio = (0, 0)
        elif BldShape == 'S':
            base_width = math.sqrt(total_area)  # assume squareish
            cut_ratio = (0, 0)

        # Step 1: Estimate base height
        base_height = total_area / base_width

        # Step 2: Define cutout dimensions as fraction of base
        cut_width = base_width * cut_ratio[0]
        cut_height = base_height * cut_ratio[1]

        # Step 3: Compute actual area of full rectangle and subtract notch
        full_area = base_width * base_height
        notch_area = cut_width * cut_height
        l_shape_area = full_area - notch_area

        # Step 4: Adjust height to match requested area
        scale_factor = total_area / l_shape_area
        base_width *= math.sqrt(scale_factor)
        base_height *= math.sqrt(scale_factor)
        cut_width = base_width * cut_ratio[0]
        cut_height = base_height * cut_ratio[1]

        x0, y0 = origin

        # Step 5: Generate coordinates
        if BldShape == 'L':
            coords_floor = [
                (x0, y0, 0),
                (x0 + base_width, y0, 0),
                (x0 + base_width, y0 + base_height, 0),
                (x0 + cut_width, y0 + base_height, 0),
                (x0 + cut_width, y0 + cut_height, 0),
                (x0, y0 + cut_height, 0),
                (x0, y0, 0)]
        elif BldShape == 'R' or 'S':
            coords_floor = [
                (x0, y0, 0),
                (x0 + base_width, y0, 0),
                (x0 + base_width, y0 + base_height, 0),
                (x0, y0 + base_height, 0),
                (x0, y0, 0)]
        coords_roof = [(x, y, self.height ) for x, y, z in coords_floor]
        return {'coords_floor':coords_floor, 'coords_roof':coords_roof}

    def PlotGeometry(self, Coords):
        x_vals = [x for x, y, z in Coords]
        y_vals = [y for x, y, z in Coords]

        # Plot
        plt.plot(x_vals, y_vals, color='blue', linewidth=2)
        plt.fill(x_vals, y_vals, color='skyblue', alpha=0.4)  # Optional: fill the rectangle
        plt.title("Rectangle in Projected Coordinates (e.g., EPSG:3006)")
        plt.xlabel("Easting (m)")
        plt.ylabel("Northing (m)")
        plt.axis('equal')
        plt.grid(True)
        plt.show()
