import json
import os
import pydeck as pdk
import webbrowser
import numpy as np
from pyproj import Transformer


def VisBldonMap(Path2GeoJson):

    # ---------------------------------------------------------
    # 1️⃣ LOAD GEOJSON
    # ---------------------------------------------------------
    with open(os.path.join(Path2GeoJson, "Generated_Buildings.geojson"), encoding="utf-8") as f:
        data = json.load(f)

    features = data["features"]

    buildings = []

    # ---------------------------------------------------------
    # 2️⃣ ENERGY CLASS → COLOR SCALE
    # ---------------------------------------------------------
    energy_color_map = {
        "A": [0, 160, 0],        # strong green
        "B": [80, 200, 0],
        "C": [170, 220, 0],
        "D": [255, 220, 0],
        "E": [255, 150, 0],
        "F": [255, 80, 0],
        "G": [220, 0, 0],        # red
    }

    # ---------------------------------------------------------
    # 3️⃣ EXTRACT FOOTPRINT + HEIGHT + PROPERTIES
    # ---------------------------------------------------------
    for feature in features:

        props = feature["properties"]
        geom = feature["geometry"]

        if geom["type"] == "GeometryCollection":
            for g in geom["geometries"]:
                if g["type"] == "MultiPolygon":

                    # collect all Z values
                    all_z = []
                    for polygon in g["coordinates"]:
                        for pt in polygon[0]:
                            all_z.append(pt[2])

                    min_z = min(all_z)
                    max_z = max(all_z)
                    height = max_z - min_z

                    # find bottom face (footprint)
                    for polygon in g["coordinates"]:
                        face = polygon[0]
                        z_vals = [p[2] for p in face]

                        if min(z_vals) == max(z_vals) and z_vals[0] == min_z:

                            energy_class = str(props.get("EgiEnergiklass", "")).strip().upper()
                            color = energy_color_map.get(
                                energy_class,
                                [180, 180, 180]  # default grey if missing
                            )

                            buildings.append({
                                "polygon": face,
                                "height": height,
                                "uuid": props.get("50A_UUID"),
                                "address": props.get("IdAdr"),
                                "floors": props.get("EgenAntalPlan"),
                                "atemp": props.get("EgenAtemp"),
                                "energy_class": energy_class,
                                "year": props.get("43S_BYGGAR"),
                                "color": color
                            })

    # ---------------------------------------------------------
    # 4️⃣ CONVERT EPSG:3006 → EPSG:4326
    # ---------------------------------------------------------
    transformer = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)

    converted = []
    for item in buildings:
        new_poly = []
        for x, y, z in item["polygon"]:
            lon, lat = transformer.transform(x, y)
            new_poly.append([lon, lat])

        converted.append({
            "polygon": new_poly,
            "height": item["height"],
            "uuid": item["uuid"],
            "address": item["address"],
            "floors": item["floors"],
            "atemp": item["atemp"],
            "energy_class": item["energy_class"],
            "year": item["year"],
            "color": item["color"]
        })

    buildings = converted

    # ---------------------------------------------------------
    # 5️⃣ MAP CENTER
    # ---------------------------------------------------------
    all_points = [p for b in buildings for p in b["polygon"]]
    center_lon = np.mean([p[0] for p in all_points])
    center_lat = np.mean([p[1] for p in all_points])

    # ---------------------------------------------------------
    # 6️⃣ EXTRUDED BUILDING LAYER
    # ---------------------------------------------------------
    building_layer = pdk.Layer(
        "PolygonLayer",
        buildings,
        get_polygon="polygon",
        extruded=True,
        get_elevation="height",
        get_fill_color="color",
        pickable=True,
        material={
            "ambient": 0.3,
            "diffuse": 0.6,
            "shininess": 20
        }
    )

    # ---------------------------------------------------------
    # 7️⃣ VIEW STATE
    # ---------------------------------------------------------
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=17,
        pitch=60,
        bearing=30,
    )

    # ---------------------------------------------------------
    # 8️⃣ CREATE DECK WITH TOOLTIP
    # ---------------------------------------------------------
    deck = pdk.Deck(
        layers=[building_layer],
        initial_view_state=view_state,
        map_style="light",
        tooltip={
            "html": """
            <b>Building ID:</b> {uuid} <br/>
            <b>Address:</b> {address} <br/>
            <b>Construction Year:</b> {year}<br/>
            <b>Height:</b> {height} m <br/>
            <b>Floors:</b> {floors} <br/>
            <b>Atemp:</b> {atemp} m² <br/>
            <b>Energy Class:</b> {energy_class}
            """,
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "font-size": "13px"
            }
        }
    )

    return deck


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":

    project_root = os.path.join(
        os.path.abspath(os.path.join(os.getcwd(), "..", "..")),
        'examples'
    )

    Path2GeoJson = os.path.join(project_root, 'Data_for_NUS')

    deck = VisBldonMap(Path2GeoJson)

    html_path = "3D_Buildings.html"
    deck.to_html(html_path)

    # ---------------------------------------------------------
    # ADD LEGEND TO HTML
    # ---------------------------------------------------------
    legend_html = """
    <div style="
    position: absolute;
    bottom: 30px;
    right: 30px;
    background-color: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0,0,0,0.3);
    font-family: Arial;
    font-size: 14px;
    z-index: 1000;
    min-width: 260px;
    ">
    <b>Energy Performance Class</b><br><br>

    <div><span style="color:rgb(0,160,0)">■</span> A  (≤ 50 kWh/m²·yr)</div>
    <div><span style="color:rgb(80,200,0)">■</span> B  (51–75 kWh/m²·yr)</div>
    <div><span style="color:rgb(170,220,0)">■</span> C  (76–100 kWh/m²·yr)</div>
    <div><span style="color:rgb(255,220,0)">■</span> D  (101–135 kWh/m²·yr)</div>
    <div><span style="color:rgb(255,150,0)">■</span> E  (136–180 kWh/m²·yr)</div>
    <div><span style="color:rgb(255,80,0)">■</span> F  (181–235 kWh/m²·yr)</div>
    <div><span style="color:rgb(220,0,0)">■</span> G  (> 235 kWh/m²·yr)</div>

    <br>
    <div style="font-size:12px; color:gray;">
    Primary energy use per heated floor area
    </div>
    </div>
    """

    with open(html_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    html_content = html_content.replace("</body>", legend_html + "\n</body>")

    with open(html_path, "w", encoding="utf-8") as file:
        file.write(html_content)

    webbrowser.open(html_path)
