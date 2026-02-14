import os.path

import numpy as np
from shapely.geometry import Polygon
from pvlib.iotools import read_epw
from pvlib.location import Location
from pvlib.irradiance import get_total_irradiance
from shapely.geometry.polygon import Polygon


def Solar_Irradiance(BldObj, keypath, WeatherFile):
    Weather_path = os.path.join(keypath['epluspath'], WeatherFile)
    weather, meta = read_epw(Weather_path)
    poa = []
    wh = []
    site = Location(
        latitude=meta["latitude"],
        longitude=meta["longitude"],
        altitude=meta["altitude"],
        tz=meta["TZ"]
    )

    times = weather.index
    # Solar position
    solar_pos = site.get_solarposition(times)
    # IRRADIANCE FROM EPW
    dni = weather["dni"]
    ghi = weather["ghi"]
    dhi = weather["dhi"]
    tilt = 0
    azimuths = [azimuth_from_polygon_coords(p) for p in BldObj.footprint]

    for azimuth in azimuths:
        # computes how much solar radiation actually hits your roof surface (Plane-Of-Array irradiance)
        poa.append(get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            dni=dni,
            ghi=ghi,
            dhi=dhi,
            solar_zenith=solar_pos["zenith"],
            solar_azimuth=solar_pos["azimuth"]
        ))
    for k in poa:
        wh.append(k["poa_global"].sum())
    return wh


def azimuth_from_polygon_coords(coords):
    """
    coords: list of (x, y) tuples for one polygon ring
    returns: azimuth degrees from North, clockwise (0..360)
    """
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)  # fixes many self-intersections

    mrr = poly.minimum_rotated_rectangle
    pts = list(mrr.exterior.coords)

    # 4 rectangle edges (ignore last repeated point)
    edges = [(pts[i], pts[i+1]) for i in range(4)]

    def length(e):
        (x1, y1), (x2, y2) = e
        return np.hypot(x2 - x1, y2 - y1)

    longest = max(edges, key=length)
    (x1, y1), (x2, y2) = longest

    # azimuth: 0°=North, clockwise
    az = (np.degrees(np.arctan2(x2 - x1, y2 - y1)) + 360) % 360
    return az





