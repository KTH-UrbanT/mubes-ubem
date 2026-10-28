"""MUBES solar explorer: raw surveyed geometry, EPW weather and geometric rays.

Run: venv/bin/python solarvisualization.py
Validate: venv/bin/python solarvisualization.py --validate
Dependencies: dash, plotly, numpy, pandas, pvlib, pyproj, shapely,
              trimesh, rtree, mapbox-earcut.
This standalone application does not import or alter the simulation pipeline.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pvlib
import trimesh
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
from pyproj import CRS, Proj, Transformer
from shapely.affinity import translate
from shapely.geometry import LineString, Polygon, box, shape
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, transform, unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "default/data/Case_Study/SvB 1965-1975/SvB_1965_1975_Buildings.geojson"
COHORT_FILE = ROOT / "examples/1965-1975/Final_Sim_Results/SvB_Base/FinalLogsCompiled.log"
EPW_FILE = Path("/Applications/EnergyPlus-9-5-0/WeatherData/SWE_ST_Stockholm.024850_TMYx.2009-2023.epw")
WALL_FIELDS = {"id": "50A_UUID", "bottom": "zmin", "top": "zmax"}
# Inspected project mappings, overridable here or with --fields JSON.
# 43S_BYGGAR is used by the existing retrofit scenario loader.
FIELD_CANDIDATES = {
    "id": ["50A_UUID", "UUID", "uuid", "building_id", "id"],
    "year": ["43S_BYGGAR", "EgenNybyggAr", "construction_year", "year_built"],
    "height": ["height", "Height", "building_height"],
    "floors": ["EgenAntalPlan", "floors", "num_floors", "storeys"],
    "address": ["IdAdr", "address", "name"],
}
FIELD_OVERRIDES: dict[str, str] = {}
# This project's GeoJSON omits its CRS. Generate_CityModeller.py explicitly
# transforms EPSG:4326 to EPSG:3006. Custom inputs without CRS require --crs.
PROJECT_CRS = "EPSG:3006"
YEAR_MIN, YEAR_MAX, EXPECTED_COUNT = 1965, 1975, 159
TOLERANCE = 0.02  # metres: adjacency tolerance and outward ray-origin offset
SAMPLES = 3  # SAMPLES x SAMPLES equally weighted, cell-centre samples per wall
FALLBACK_LOCATION = {"latitude": 59.35, "longitude": 18.0667, "altitude": 52.0, "TZ": 1.0}
LOG = logging.getLogger("solarvisualization")
COLORS = [[0, "#edf1f4"], [0.15, "#71b8c4"], [0.4, "#287c9b"],
          [0.65, "#efbe45"], [0.85, "#e77a37"], [1, "#ae342b"]]
STATUS_COLORS = {"Night": "#79868b", "Away from sun": "#a7b1b8",
                 "Obstructed": "#476779", "Partly sunlit": "#d9ae45", "Sunlit": "#f4cd53"}


def polygons(geometry):
    """Yield polygon members, retaining holes and multipart components."""
    if geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for member in geometry.geoms:
            yield from polygons(member)


def number(value) -> Optional[float]:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def detect_fields(features: list[dict], overrides: dict[str, str]) -> dict[str, str]:
    keys = set().union(*(f.get("properties", {}).keys() for f in features))
    mapping = {}
    for role, candidates in FIELD_CANDIDATES.items():
        selected = overrides.get(role) or next((k for k in candidates if k in keys), None)
        if selected is None or selected not in keys:
            if role == "address":
                continue
            raise ValueError(f"Cannot detect {role}; specify --fields. Available fields: {sorted(keys)}")
        mapping[role] = selected
    return mapping


@dataclass
class Building:
    uid: str
    year: Optional[int]
    floors: Optional[float]
    height: float
    address: str
    target: bool


@dataclass
class Solid:
    """One real footprint component extruded between surveyed elevations."""
    uid: str
    polygon: Polygon
    bottom: float
    top: float


@dataclass
class Wall:
    surface_id: str
    uid: str
    vertices: np.ndarray
    normal: np.ndarray
    azimuth: float
    area: float


def raw_polygon_groups(geometry: dict):
    """GeometryCollections contain separate surveyed blocks in this dataset."""
    kind = geometry["type"]
    if kind == "GeometryCollection":
        for member in geometry["geometries"]:
            yield from raw_polygon_groups(member)
    elif kind == "MultiPolygon":
        yield geometry["coordinates"]
    elif kind == "Polygon":
        yield [geometry["coordinates"]]
    else:
        raise ValueError(f"Unsupported building geometry: {kind}")


def extract_solids(feature: dict, uid: str, height: Optional[float], transformer: Transformer,
                   warnings: list[str]) -> list[Solid]:
    """Use base/roof Z for surveyed shells; use real height fields for 2D data.

    Vertical shell faces collapse to lines in XY and must never be interpreted
    as footprints. Horizontal base faces are distinguished from duplicate roofs.
    """
    result = []
    for group in raw_polygon_groups(feature["geometry"]):
        flat = []
        zs = []
        for rings in group:
            outer = rings[0]
            zs.extend(float(p[2]) for p in outer if len(p) > 2)
            z = [float(p[2]) for p in outer if len(p) > 2]
            if z and max(z) - min(z) > 0.01:
                continue
            polygon = Polygon([p[:2] for p in outer], [[p[:2] for p in r] for r in rings[1:]])
            if not polygon.is_valid:
                polygon = make_valid(polygon)
                warnings.append(f"Repaired geometry: {uid}")
            polygon = transform(transformer.transform, polygon)
            flat.append((min(z) if z else 0.0, polygon))
        if not flat:
            raise ValueError(f"{uid}: no usable horizontal footprint")
        base = min(z for z, _ in flat)
        surveyed = bool(zs) and max(zs) - min(zs) > 0.1
        top = max(zs) if surveyed else base + (height or 0)
        if top <= base:
            raise ValueError(f"{uid}: missing positive height; geometry is not fabricated")
        footprint = unary_union([p for z, p in flat if abs(z - base) < 0.01])
        for poly in polygons(footprint):
            if poly.area > 0.01:
                # Remove numerically collinear/duplicate ring nodes below the
                # source's millimetre precision before roof triangulation.
                result.append(Solid(uid, orient(poly.simplify(1e-6, preserve_topology=True), sign=1), base, top))
    return result


class City:
    def __init__(self, path: Path, cohort: Optional[Path], crs: Optional[str],
                 overrides: dict[str, str], samples: int = SAMPLES):
        self.path, self.cohort, self.samples = path, cohort, samples
        self.warnings: list[str] = []
        document = json.loads(path.read_text())
        features = document.get("features", [])
        if not features:
            raise ValueError(f"Empty building dataset: {path}")
        self.mapping = detect_fields(features, overrides)
        declared = document.get("crs", {}).get("properties", {}).get("name")
        source = crs or declared or (PROJECT_CRS if path.resolve() == DATASET.resolve() else None)
        if not source:
            raise ValueError("Dataset has no CRS metadata; supply --crs explicitly")
        self.source_crs = CRS.from_user_input(source)
        self.crs = CRS.from_epsg(3006)
        transformer = Transformer.from_crs(self.source_crs, self.crs, always_xy=True)
        cohort_ids = None
        if cohort:
            if not cohort.exists():
                raise ValueError(f"Cohort file unavailable: {cohort}. Use --all-years for the full year filter.")
            cohort_ids = set(re.findall(r"50A_UUID\s*:\s*([\da-fA-F-]{36})", cohort.read_text()))
            if not cohort_ids:
                raise ValueError(f"No UUIDs found in cohort log: {cohort}")
        self.buildings: dict[str, Building] = {}
        self.solids: list[Solid] = []
        year_count = 0
        for feature in features:
            prop = feature.get("properties", {})
            uid = str(prop.get(self.mapping["id"], "")).strip()
            if not uid or uid == "None":
                raise ValueError("Building without an identifier")
            if uid in self.buildings:
                raise ValueError(f"Duplicate building ID: {uid}; merge duplicate records explicitly")
            year = number(prop.get(self.mapping["year"]))
            year = int(year) if year is not None else None
            in_year = year is not None and YEAR_MIN <= year <= YEAR_MAX
            year_count += int(in_year)
            target = in_year and (cohort_ids is None or uid in cohort_ids)
            solids = extract_solids(feature, uid, number(prop.get(self.mapping["height"])), transformer, self.warnings)
            if not solids:
                raise ValueError(f"No solid geometry for {uid}")
            self.buildings[uid] = Building(uid, year, number(prop.get(self.mapping["floors"])),
                                          max(s.top - s.bottom for s in solids),
                                          str(prop.get(self.mapping.get("address", ""), "")), target)
            self.solids.extend(solids)
        self.target_ids = {b.uid for b in self.buildings.values() if b.target}
        self.shading_walls: list[Wall] = []
        self.context_wall_file=path.with_name(path.name.replace('_Buildings.geojson','_Walls.geojson'))
        self.extra_context_count=0
        if self.context_wall_file!=path and self.context_wall_file.exists():
            self.load_context_walls(transformer)
        if not self.target_ids:
            raise ValueError("No buildings match the selected cohort and construction years")
        if cohort_ids and cohort_ids - self.target_ids:
            self.warnings.append(f"{len(cohort_ids - self.target_ids)} cohort UUIDs are absent or outside the selected years")
        if len(self.target_ids) != EXPECTED_COUNT:
            self.warnings.append(f"COUNT MISMATCH: {len(self.target_ids)} targets; expected {EXPECTED_COUNT}.")
        self.year_count = year_count
        # A common translation preserves distances, elevations and orientations.
        bounds = unary_union([s.polygon for s in self.solids]).bounds
        self.origin = np.array([(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2,
                                min(s.bottom for s in self.solids)])
        lon,lat=Transformer.from_crs(self.crs,4326,always_xy=True).transform(*self.origin[:2])
        self.convergence=Proj(self.crs).get_factors(lon,lat).meridian_convergence
        for solid in self.solids:
            solid.polygon = translate(solid.polygon, -self.origin[0], -self.origin[1])
            solid.bottom -= self.origin[2]
            solid.top -= self.origin[2]
        for wall in self.shading_walls:
            wall.vertices -= self.origin
        self.extent = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
        LOG.info("Loaded %s targets, %s context buildings; extracting walls", len(self.target_ids), len(self.buildings)-len(self.target_ids))
        self.extract_walls()
        LOG.info("Meshing %s solids for geometric obstruction tests", len(self.solids))
        self.meshes = [self.solid_mesh(s) for s in self.solids]
        wall_meshes = [trimesh.Trimesh(vertices=w.vertices, faces=[[0,1,2],[0,2,3]], process=False)
                       for w in self.shading_walls]
        # Source wall sheets are opaque on both sides, including open wall rings.
        self.mesh = trimesh.util.concatenate(self.meshes + wall_meshes)
        self.rays = trimesh.ray.ray_triangle.RayMeshIntersector(self.mesh)
        self.ray_lock=threading.Lock()
        _ = self.mesh.triangles_tree  # build the R-tree once, outside callbacks
        self.roof_traces = self.make_roof_traces()
        self.shading_trace = self.make_shading_trace()
        self.area = np.array([w.area for w in self.walls])
        self.normals = np.array([w.normal for w in self.walls])
        self.vertices = np.vstack([w.vertices for w in self.walls])
        self.faces = np.vstack([np.array([[0, 1, 2], [0, 2, 3]]) + i * 4 for i in range(len(self.walls))])
        self.sample_origins = self.wall_samples(samples)
        LOG.info("Ready: %s exposed target wall surfaces, %s rays/frame maximum", len(self.walls), len(self.sample_origins))

    def load_context_walls(self, transformer: Transformer) -> None:
        """Load every surveyed wall and recover closed missing context buildings.

        Never construct a convex hull or infer a roof height from floor count.
        Incomplete wall rings are explicitly reported, not silently filled.
        """
        features=json.loads(self.context_wall_file.read_text()).get('features',[])
        groups={}
        seen = set()
        for feature in features:
            prop=feature.get('properties',{})
            uid=prop.get(WALL_FIELDS['id'])
            if not uid:raise ValueError('Shading wall without building UUID')
            bottom,top=number(prop.get(WALL_FIELDS['bottom'])),number(prop.get(WALL_FIELDS['top']))
            if bottom is None or top is None or top<=bottom:
                raise ValueError(f'Missing elevation on contextual wall {uid}')
            geometry=transform(transformer.transform,shape(feature['geometry']))
            lines=[geometry] if geometry.geom_type=='LineString' else list(getattr(geometry,'geoms',[]))
            if not lines or any(line.geom_type!='LineString' for line in lines):
                raise ValueError(f'Unsupported shading wall geometry for {uid}')
            for line in lines:
                coordinates=np.asarray(line.coords)[:,:2]
                for part,(a,b) in enumerate(zip(coordinates[:-1],coordinates[1:])):
                    length=np.linalg.norm(b-a)
                    if length<=1e-7:continue
                    key=(tuple(sorted([tuple(a),tuple(b)])),bottom,top)
                    if key in seen:continue
                    seen.add(key)
                    tangent=(b-a)/length
                    normal=np.array([tangent[1],-tangent[0],0.0])
                    self.shading_walls.append(Wall(f'{prop.get("vaggid",len(self.shading_walls))}/{part}',uid,
                        np.array([[*a,bottom],[*b,bottom],[*b,top],[*a,top]]),normal,
                        math.degrees(math.atan2(normal[0],normal[1]))%360,length*(top-bottom)))
            if uid not in self.buildings:
                groups.setdefault((uid,bottom,top),[]).extend(lines)
        for (uid,bottom,top),lines in groups.items():
            candidates=list(polygonize(unary_union(lines)))
            if not candidates:
                self.warnings.append(f'Incomplete context wall ring: {uid}; using the actual wall sheets only')
                continue
            for poly in candidates:
                # A closed courtyard yields its own polygon as well as a polygon
                # with a hole; retain the outer component and its actual hole.
                if any(Polygon(other.exterior).contains(poly.representative_point()) for other in candidates if other is not poly):
                    continue
                self.solids.append(Solid(uid,orient(poly.simplify(1e-6,preserve_topology=True),sign=1),bottom,top))
            if uid not in self.buildings:
                self.buildings[uid]=Building(uid,None,None,top-bottom,'Context from surveyed walls',False)
                self.extra_context_count+=1

    def make_shading_trace(self) -> Optional[go.Mesh3d]:
        """Display context directly from the companion wall file, without roofs."""
        walls=[w for w in self.shading_walls if w.uid not in self.target_ids]
        if not walls:return None
        vertices=np.vstack([w.vertices for w in walls])
        faces=np.vstack([np.array([[0,1,2],[0,2,3]])+4*i for i in range(len(walls))])
        texts=[f'{w.uid}<br>Shading wall {w.surface_id}<br>Area {w.area:.1f} m2'
               f'<br>Elevation {w.vertices[0,2]+self.origin[2]:.2f} to {w.vertices[2,2]+self.origin[2]:.2f} m'
               for w in walls for _ in range(4)]
        return go.Mesh3d(x=vertices[:,0],y=vertices[:,1],z=vertices[:,2],i=faces[:,0],j=faces[:,1],k=faces[:,2],
                        color='#879598',opacity=.45,flatshading=True,text=texts,
                        hovertemplate='%{text}<extra></extra>',name='Surrounding shading walls',showlegend=False)

    @lru_cache(maxsize=96)
    def sunlight_paths(self, azimuth: float, altitude: float, selected: Optional[str]) -> dict:
        """Trace incoming sunlight to its FIRST opaque hit, never through a wall.

        Origins lie sunward of every mesh vertex. Display only the final 65 m of
        each incoming ray; dashed downstream paths are geometric guides, not light.
        The display is capped at 120 samples; irradiance uses every wall sample.
        """
        direction=sun_vector(azimuth,altitude)
        active=np.array([not selected or w.uid==selected for w in self.walls]) & (self.normals@direction>1e-7)
        indices=np.flatnonzero(np.repeat(active,self.samples**2)) if altitude>0 else np.array([],dtype=int)
        if len(indices)>120:indices=indices[np.linspace(0,len(indices)-1,120,dtype=int)]
        targets=self.sample_origins[indices]
        if not len(targets):return {'indices':indices,'targets':targets,'ends':targets,'starts':targets,'blocked':np.array([],dtype=bool)}
        distance=(self.mesh.vertices@direction).max()-targets@direction+10
        sources=targets+distance[:,None]*direction
        with self.ray_lock:
            locations,ray_ids,_=self.rays.intersects_location(sources,np.tile(-direction,(len(sources),1)),multiple_hits=False)
        ends=targets.copy()
        blocked=np.zeros(len(targets),dtype=bool)
        for location,index in zip(locations,ray_ids):
            if np.dot(location-targets[index],direction)>TOLERANCE:
                ends[index]=location
                blocked[index]=True
        return {'indices':indices,'targets':targets,'ends':ends,'starts':ends+65*direction,'blocked':blocked}

    def extract_walls(self) -> None:
        """Subtract neighbouring solid occupancy in wall-local (distance,Z).

        Boundary segments are split at contact intervals and neighbour roof/base
        heights. Thus a taller building's wall above a shared wall remains exposed.
        Courtyard rings have opposite winding and outward normals face the hole.
        """
        geoms = [s.polygon for s in self.solids]
        tree = STRtree(geoms)
        lookup = {id(g): i for i, g in enumerate(geoms)}
        self.walls: list[Wall] = []
        removed = 0.0
        for index, solid in enumerate(self.solids):
            if solid.uid not in self.target_ids:
                continue
            for ring in [solid.polygon.exterior, *solid.polygon.interiors]:
                coords = np.asarray(ring.coords)[:, :2]
                for a, b in zip(coords[:-1], coords[1:]):
                    length = np.linalg.norm(b - a)
                    if length <= TOLERANCE:
                        continue
                    tangent = (b-a) / length
                    normal = np.array([tangent[1], -tangent[0], 0.0])
                    edge = LineString([a, b])
                    exposed = box(0, solid.bottom, length, solid.top)
                    probe = translate(edge, normal[0]*TOLERANCE, normal[1]*TOLERANCE)
                    for candidate in tree.query(probe.buffer(TOLERANCE)):
                        j = int(candidate) if isinstance(candidate, (int, np.integer)) else lookup[id(candidate)]
                        if j == index:
                            continue
                        neighbour = self.solids[j]
                        bottom, top = max(solid.bottom, neighbour.bottom), min(solid.top, neighbour.top)
                        if top <= bottom:
                            continue
                        contact = probe.intersection(neighbour.polygon.buffer(TOLERANCE/4))
                        pieces = [contact] if contact.geom_type == "LineString" else getattr(contact, "geoms", [])
                        for piece in pieces:
                            if piece.geom_type != "LineString" or piece.length <= TOLERANCE:
                                continue
                            distances = [edge.project(shape({"type": "Point", "coordinates": p})) for p in piece.coords]
                            exposed = exposed.difference(box(min(distances), bottom, max(distances), top))
                    removed += length*(solid.top-solid.bottom)-exposed.area
                    for face in polygons(exposed):
                        # Axis-aligned cut rectangles can form nonrectangular unions;
                        # partition at every vertical boundary before constructing quads.
                        xs = sorted({p[0] for p in face.exterior.coords})
                        for left, right in zip(xs[:-1], xs[1:]):
                            if right-left <= TOLERANCE:
                                continue
                            for cell in polygons(face.intersection(box(left, solid.bottom, right, solid.top))):
                                x0,z0,x1,z1 = cell.bounds
                                if cell.area <= 0.01:
                                    continue
                                start,end = a+tangent*x0,a+tangent*x1
                                vertices = np.array([[*start,z0],[*end,z0],[*end,z1],[*start,z1]])
                                self.walls.append(Wall(f"{solid.uid}/wall-{len(self.walls):05d}",solid.uid,vertices,normal,
                                                       math.degrees(math.atan2(normal[0],normal[1]))%360,cell.area))
        self.shared_area_removed = removed

    @staticmethod
    def solid_mesh(solid: Solid) -> trimesh.Trimesh:
        mesh = trimesh.creation.extrude_polygon(solid.polygon, solid.top-solid.bottom, engine="earcut")
        mesh.update_faces(mesh.nondegenerate_faces(height=1e-7))
        mesh.remove_unreferenced_vertices()
        mesh.apply_translation([0,0,solid.bottom])
        if not mesh.is_watertight:
            raise ValueError(f"Non-watertight mesh for {solid.uid}")
        return mesh

    def make_roof_traces(self) -> list[go.Mesh3d]:
        traces = []
        for target in [False,True]:
            vertices, faces, labels, ids = [],[],[],[]
            for solid, mesh in zip(self.solids,self.meshes):
                b = self.buildings[solid.uid]
                if b.target != target:
                    continue
                selected = mesh.faces[mesh.face_normals[:,2] > .9] if target else mesh.faces
                offset = len(vertices)
                vertices.extend(mesh.vertices.tolist())
                faces.extend((selected+offset).tolist())
                labels.extend([f"{b.uid}<br>{b.address}<br>Built {b.year} | {b.height:.2f} m | Floors {b.floors}"]*len(mesh.vertices))
                ids.extend([b.uid]*len(mesh.vertices))
            if vertices:
                v,f=np.array(vertices),np.array(faces)
                traces.append(go.Mesh3d(x=v[:,0],y=v[:,1],z=v[:,2],i=f[:,0],j=f[:,1],k=f[:,2],
                                       color="#bad5d0" if target else "#adb4b8",opacity=1 if target else .3,
                                       text=labels,customdata=ids,hovertemplate="%{text}<extra></extra>",name="Target roofs" if target else "Context buildings",
                                       flatshading=True,showlegend=False,meta="target" if target else "context"))
        return traces

    def wall_samples(self, count: int) -> np.ndarray:
        q = (np.arange(count)+.5)/count
        u,v=np.meshgrid(q,q)
        samples=[]
        for wall in self.walls:
            a,b,_,d=wall.vertices
            samples.extend(a+u.ravel()[:,None]*(b-a)+v.ravel()[:,None]*(d-a)+TOLERANCE*wall.normal)
        return np.asarray(samples)

    @lru_cache(maxsize=96)
    def shading(self, azimuth: float, altitude: float) -> tuple[np.ndarray,np.ndarray]:
        direction = sun_vector(azimuth,altitude)
        incidence = np.clip(self.normals @ direction,0,1)
        fraction = np.ones(len(self.walls))
        if altitude <= 0:
            return incidence*0, fraction
        active = np.repeat(incidence>1e-7,self.samples**2)
        origins=self.sample_origins[active]+direction*TOLERANCE
        blocked=np.ones(len(self.sample_origins),dtype=bool)
        hits=[]
        # Bound ray batches to limit R-tree candidate memory. The source wall is
        # avoided by offsetting origins, not by excluding its entire building:
        # other wings of a concave building must still be allowed to cast shadows.
        for start in range(0,len(origins),256):
            rays=origins[start:start+256]
            with self.ray_lock:
                hits.extend(self.rays.intersects_any(rays,np.tile(direction,(len(rays),1))))
        blocked[active]=hits
        fraction=blocked.reshape(-1,self.samples**2).mean(axis=1)
        return incidence,fraction

    def report(self) -> dict:
        return {"dataset":str(self.path),"cohort":str(self.cohort) if self.cohort else "All year matches",
                "context_wall_file":str(self.context_wall_file),"additional_buildings_from_walls":self.extra_context_count,
                "context_wall_field_mapping":WALL_FIELDS,
                "shading_wall_segments":len(self.shading_walls),
                "field_mapping":self.mapping,"source_crs":self.source_crs.to_string(),"calculation_crs":self.crs.to_string(),
                "origin_m":self.origin.tolist(),"target_buildings":len(self.target_ids),"year_matches_in_full_dataset":self.year_count,
                "grid_convergence_degrees":self.convergence,
                "context_buildings":len(self.buildings)-len(self.target_ids),"solid_parts":len(self.solids),
                "wall_surfaces":len(self.walls),"exposed_wall_area_m2":float(self.area.sum()),
                "shared_wall_area_removed_m2":self.shared_area_removed,"warnings":self.warnings}


def sun_vector(azimuth: float, altitude: float) -> np.ndarray:
    """Unit vector toward sun: X east, Y north, Z up; azimuth clockwise from N."""
    az,el=np.radians([azimuth,altitude])
    return np.array([np.cos(el)*np.sin(az),np.cos(el)*np.cos(az),np.sin(el)])


class Weather:
    def __init__(self, path: Optional[Path]):
        self.path=path
        self.data=None
        self.meta=FALLBACK_LOCATION.copy()
        if path and path.exists():
            self.data,self.meta=pvlib.iotools.read_epw(path,coerce_year=2025)
        elif path:
            raise ValueError(f"EPW not found: {path}. Use --no-weather for explicitly labelled clear-sky estimates.")
        self.tz=timezone(timedelta(hours=float(self.meta["TZ"])))
        self.location=pvlib.location.Location(self.meta["latitude"],self.meta["longitude"],tz=float(self.meta["TZ"]),altitude=self.meta["altitude"])

    @lru_cache(maxsize=2048)
    def at(self,date: str,minute: int) -> dict:
        dt=pd.Timestamp(date).normalize()+pd.Timedelta(minutes=int(minute))
        dt=dt.tz_localize(self.tz)
        position=self.location.get_solarposition(pd.DatetimeIndex([dt])).iloc[0]
        result={"altitude":float(position["elevation"]),"azimuth":float(position["azimuth"]),"time":dt.strftime("%H:%M")}
        if self.data is not None:
            # EPW hour 1 represents the interval 00:00-01:00. pvlib indexes its
            # START at 00:00; use the containing hour, not interpolation pretending
            # to be measured subhourly weather. Radiation Wh/m2 over 1 h => W/m2.
            rows=self.data[(self.data.index.month==dt.month)&(self.data.index.day==dt.day)&(self.data.index.hour==dt.hour)]
            if len(rows)!=1:
                raise ValueError("EPW has no unique weather hour for selected date (Feb 29 is not in this TMY)")
            row=rows.iloc[0]
            dni,dhi=float(row["dni"]),float(row["dhi"])
            if not np.isfinite([dni,dhi]).all() or min(dni,dhi)<0 or max(dni,dhi)>=9999:
                raise ValueError("Missing/invalid DNI or DHI in EPW hour; no inaccurate substitution used")
            result["source"]="EPW hourly mean"
        else:
            clear=self.location.get_clearsky(pd.DatetimeIndex([dt])).iloc[0]
            dni,dhi=float(clear.dni),float(clear.dhi)
            result["source"]="CLEAR-SKY ESTIMATE (no EPW)"
        result.update(dni=dni if result["altitude"]>0 else 0,dhi=dhi if result["altitude"]>0 else 0)
        return result


def radiation(city: City, sun: dict) -> dict:
    """Direct W/m2 = DNI * max(n dot s,0) * (1 - blocked sample fraction).

    Optional diffuse = DHI/2 for a vertical plane with an isotropic unobstructed
    sky. Diffuse sky masking, reflections and glazing transmittance are NOT solved.
    """
    # SPA azimuth is true north; SWEREF grid north differs by meridian convergence.
    incidence,shaded=city.shading((sun["azimuth"]-city.convergence)%360,sun["altitude"])
    direct=sun["dni"]*incidence*(1-shaded)
    status=np.where(incidence<=1e-7,"Away from sun",np.where(shaded>=1,"Obstructed",np.where(shaded>0,"Partly sunlit","Sunlit")))
    if sun["altitude"]<=0:
        status[:]='Night'
    sunlit=(1-shaded)*(incidence>0)
    return {"direct":direct,"total":direct+sun["dhi"]/2,"shaded":shaded,"status":status,"incidence":incidence,
            "sunlit_area":float(city.area@sunlit),"shaded_area":float(city.area@(1-sunlit)),
            "mean":float(city.area@direct/city.area.sum())}


def ground_shadows(city: City, sun: dict) -> list[go.Mesh3d]:
    """Project opaque prism meshes onto a horizontal z=0 plane (not terrain)."""
    if sun['altitude']<=0:
        return []
    direction=sun_vector(sun['azimuth']-city.convergence,sun['altitude'])
    v=city.mesh.vertices.copy()
    v[:,:2]-=v[:,2,None]*direction[None,:2]/direction[2]
    v[:,2]=-.03
    f=city.mesh.faces
    return [go.Mesh3d(x=v[:,0],y=v[:,1],z=v[:,2],i=f[:,0],j=f[:,1],k=f[:,2],color='#bcc4c8',
                      opacity=.22,hoverinfo='skip',name='Horizontal-plane shadows',showlegend=False)]


def sunlight_traces(city: City, sun: dict, selected: Optional[str]) -> list:
    """Yellow incident rays, orange obstruction hits, grey shadow-path guides."""
    if sun['dni']<=0:return []
    paths=city.sunlight_paths(sun['azimuth']-city.convergence,sun['altitude'],selected)
    if not len(paths['indices']):return []
    def segments(starts,ends,color,name,dash='solid'):
        points=np.array([point for a,b in zip(starts,ends) for point in (a,b,[np.nan]*3)])
        return go.Scatter3d(x=points[:,0],y=points[:,1],z=points[:,2],mode='lines',
                            line=dict(color=color,width=3,dash=dash),hoverinfo='skip',name=name)
    traces=[segments(paths['starts'],paths['ends'],'#e4b400','Incoming sunlight')]
    blocked=paths['blocked']
    if blocked.any():
        traces.append(segments(paths['ends'][blocked],paths['targets'][blocked],'#849199','Blocked path (no light)','dash'))
    for mask,color,name in [(blocked,'#dd642b','Blocked at surface'),(~blocked,'#e4b400','Reaches target facade')]:
        if not mask.any():continue
        points=paths['ends'][mask]
        labels=[f'Target: {city.walls[int(i)//city.samples**2].surface_id}<br>{name}' for i in paths['indices'][mask]]
        traces.append(go.Scatter3d(x=points[:,0],y=points[:,1],z=points[:,2],mode='markers',
                                  marker=dict(color=color,size=4),text=labels,hovertemplate='%{text}<extra></extra>',name=name))
    direction=-sun_vector(sun['azimuth']-city.convergence,sun['altitude'])
    points=paths['ends']-direction*10
    traces.append(go.Cone(x=points[:,0],y=points[:,1],z=points[:,2],u=np.full(len(points),direction[0]),
                          v=np.full(len(points),direction[1]),w=np.full(len(points),direction[2]),
                          sizemode='absolute',sizeref=1.8,colorscale=[[0,'#e4b400'],[1,'#e4b400']],
                          showscale=False,hoverinfo='skip',name='Incoming ray direction',showlegend=False))
    return traces


def make_figure(city: City,sun: dict,result: dict,mode: str,visibility: str,layers: list[str],
                selected: Optional[str],reset: int,focus: bool=False) -> go.Figure:
    fig=go.Figure()
    focused=bool(focus and selected)
    bounds=unary_union([s.polygon for s in city.solids if not focused or s.uid==selected]).bounds
    x0,y0,x1,y1=bounds
    view_extent=max(x1-x0,y1-y0)
    if 'ground' in layers:
        for trace in ground_shadows(city,sun):fig.add_trace(trace)
    for trace in city.roof_traces:
        if visibility=='targets' and trace.meta=='context':continue
        if visibility=='context' and trace.meta=='target':continue
        if 'shading' in layers and trace.meta=='context':continue
        fig.add_trace(trace)
    if 'shading' in layers and visibility!='targets' and city.shading_trace is not None:
        fig.add_trace(city.shading_trace)
    if 'rays' in layers and visibility!='context':
        for trace in sunlight_traces(city,sun,selected):fig.add_trace(trace)
    if not focused and visibility!='context':
        points=[];ids=[];texts=[]
        for uid in sorted(city.target_ids):
            solids=[s for s in city.solids if s.uid==uid]
            centre=unary_union([s.polygon for s in solids]).centroid
            b=city.buildings[uid]
            mask=np.array([w.uid==uid for w in city.walls])
            mean=float(city.area[mask]@result['direct'][mask]/city.area[mask].sum()) if mask.any() else 0
            points.append([centre.x,centre.y,max(s.top for s in solids)+1]);ids.append(uid)
            texts.append(f'{uid}<br>{b.address}<br>Built {b.year} | {b.height:.2f} m | {b.floors} floors<br>Mean facade direct: {mean:.1f} W/m2')
        points=np.array(points)
        fig.add_trace(go.Scatter3d(x=points[:,0],y=points[:,1],z=points[:,2],customdata=ids,text=texts,
                                  mode='markers',marker=dict(size=3,color='#327c77',opacity=.9),
                                  hovertemplate='%{text}<extra></extra>',showlegend=False,name='Target building locations'))
    if visibility!='context':
        v,f=city.vertices,city.faces
        texts=[]
        ids=[]
        for i,w in enumerate(city.walls):
            b=city.buildings[w.uid]
            texts.extend([f'{b.uid}<br>{b.address}<br>Built {b.year} | Height {b.height:.2f} m | Floors {b.floors}'
                          f'<br>{w.surface_id}<br>Azimuth {w.azimuth:.1f} deg | Area {w.area:.1f} m2'
                          f'<br>{result["status"][i]} | Shaded {result["shaded"][i]:.0%}'
                          f'<br>Direct {result["direct"][i]:.1f} W/m2']*4)
            ids.extend([w.uid]*4)
        kwargs={}
        if mode=='status':
            kwargs['facecolor']=[STATUS_COLORS[s] for s in result['status'] for _ in range(2)]
        else:
            values=result['direct'] if mode=='direct' else result['total']
            kwargs.update(intensity=np.repeat(values,2),intensitymode='cell',colorscale=COLORS,cmin=0,cmax=1000,
                          showscale=True,colorbar=dict(title='W/m2',thickness=12,len=.55,x=1.01))
        fig.add_trace(go.Mesh3d(x=v[:,0],y=v[:,1],z=v[:,2],i=f[:,0],j=f[:,1],k=f[:,2],
                               text=texts,customdata=ids,hovertemplate='%{text}<extra></extra>',name='Target facades',
                               flatshading=True,lighting=dict(ambient=1,diffuse=0,specular=0),**kwargs))
        if mode=='status':
            for name,color in STATUS_COLORS.items():
                fig.add_trace(go.Scatter3d(x=[None],y=[None],z=[None],mode='markers',marker=dict(color=color,size=6),name=name))
    if selected in city.buildings:
        x,y,z=[],[],[]
        for s in city.solids:
            if s.uid!=selected:continue
            for ring in [s.polygon.exterior,*s.polygon.interiors]:
                for altitude in [s.bottom,s.top]:
                    c=np.asarray(ring.coords)
                    x.extend([*c[:,0],None]);y.extend([*c[:,1],None]);z.extend([*[altitude]*len(c),None])
        fig.add_trace(go.Scatter3d(x=x,y=y,z=z,mode='lines',line=dict(color='#d12b73',width=7),hoverinfo='skip',name='Selected',showlegend=False))
    if 'normals' in layers:
        walls=[w for w in city.walls if not selected or w.uid==selected]
        centres=np.array([w.vertices.mean(axis=0) for w in walls]);normals=np.array([w.normal for w in walls])
        if len(walls):
            fig.add_trace(go.Cone(x=centres[:,0],y=centres[:,1],z=centres[:,2],u=normals[:,0],v=normals[:,1],w=normals[:,2],
                                  sizemode='absolute',sizeref=3,colorscale=[[0,'#8757a6'],[1,'#8757a6']],showscale=False,hoverinfo='skip'))
    if 'sun' in layers:
        direction=sun_vector(sun['azimuth']-city.convergence,sun['altitude'])
        tops=[s.top for s in city.solids if not focused or s.uid==selected]
        start=np.array([(x0+x1)/2,(y0+y1)/2,max(tops)+10])
        arrow_length=max(15,view_extent*(.35 if focused else .025))
        end=start+direction*arrow_length
        fig.add_trace(go.Scatter3d(x=[start[0],end[0]],y=[start[1],end[1]],z=[start[2],end[2]],mode='lines+text',
                                  text=['','Sun'],textposition='top center',line=dict(color='#d7a125',width=7),hoverinfo='skip',showlegend=False))
        fig.add_trace(go.Cone(x=[end[0]],y=[end[1]],z=[end[2]],u=[direction[0]],v=[direction[1]],w=[direction[2]],
                              sizemode='absolute',sizeref=arrow_length*.15,showscale=False,colorscale=[[0,'#d7a125'],[1,'#d7a125']],hoverinfo='skip'))
    fig.update_layout(template='plotly_white',margin=dict(l=0,r=45,t=5,b=5),paper_bgcolor='white',
                      font=dict(family='Arial, sans-serif',size=11,color='#3c484e'),uirevision=f'camera-{reset}',
                      legend=dict(orientation='h',y=-.02,x=0,font=dict(size=10)),scene=dict(aspectmode='data',dragmode='orbit',
                      camera=dict(eye=dict(x=1.45,y=-1.8,z=1.8),up=dict(x=0,y=0,z=1)),
                      xaxis=dict(title='East (m)',showbackground=False,gridcolor='#eef0f2',zeroline=False),
                      yaxis=dict(title='North (m)',showbackground=False,gridcolor='#eef0f2',zeroline=False),
                      zaxis=dict(title='Elevation (m)',showbackground=False,gridcolor='#eef0f2',zeroline=False)))
    if focused:
        nearby=[s for s in city.solids if s.uid==selected]
        x0,y0,x1,y1=unary_union([s.polygon for s in nearby]).bounds
        padding=max(70,(x1-x0+y1-y0)*.6)
        fig.update_layout(uirevision=f'focus-{selected}-{reset}',scene=dict(
            xaxis=dict(range=[x0-padding,x1+padding]),yaxis=dict(range=[y0-padding,y1+padding]),
            zaxis=dict(range=[min(s.bottom for s in nearby)-2,max(s.top for s in nearby)+max(70 if 'rays' in layers else 25,arrow_length if 'sun' in layers else 25)])))
        xr,yr,zr=fig.layout.scene.xaxis.range,fig.layout.scene.yaxis.range,fig.layout.scene.zaxis.range
    else:
        padding=view_extent*.03
        xr,yr=[x0-padding,x1+padding],[y0-padding,y1+padding]
        zr=[-2,max(s.top for s in city.solids)+view_extent*.03]
        fig.update_layout(scene=dict(xaxis=dict(range=xr),yaxis=dict(range=yr),zaxis=dict(range=zr,showticklabels=False,title='')))
    # Normalize all axes by the SAME distance. Plotly's automatic data-aspect
    # normalization can crop a city that is kilometres wide and metres tall.
    scale=max(xr[1]-xr[0],yr[1]-yr[0])
    fig.update_layout(scene=dict(aspectmode='manual',aspectratio=dict(x=(xr[1]-xr[0])/scale,y=(yr[1]-yr[0])/scale,z=(zr[1]-zr[0])/scale),
                                 camera=dict(eye=dict(x=.65,y=-.8,z=.9))))
    return fig


CSS = """
*{box-sizing:border-box}body{margin:0;background:#f5f7f8;color:#26353b;font-family:Arial,sans-serif;font-size:13px;letter-spacing:0}
header{height:68px;background:white;border-bottom:1px solid #dce2e5;display:flex;align-items:center;padding:0 26px;gap:15px}
.brand{font-size:21px;font-weight:700}.tag{color:#527c7b;font-size:12px;border-left:1px solid #dce2e5;padding-left:15px}
.workspace{display:grid;grid-template-columns:280px minmax(0,1fr);min-height:calc(100vh - 68px)}
aside{background:#fff;border-right:1px solid #dce2e5;padding:22px 18px}h2{font-size:14px;margin:0 0 18px}label,.label{display:block;font-size:11px;font-weight:600;color:#5b6970;margin:20px 0 8px}
.subtle{color:#728087;font-size:11px;line-height:1.6}.controls-row{display:flex;gap:8px;align-items:center}
button{border:1px solid #cad4d9;background:#fff;color:#35474d;border-radius:4px;padding:9px 12px;cursor:pointer;font-size:13px}button:hover{background:#edf3f4}
.play{background:#246d71;color:white;border-color:#246d71}.play:hover{background:#1e5e61}
main{min-width:0;padding:18px 20px}.metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-bottom:14px}
.metric{background:white;border:1px solid #e1e6e9;border-radius:4px;padding:12px;min-width:0}.metric strong{display:block;font-size:19px;font-weight:500;margin-top:8px}.metric span{font-size:11px;color:#66757d}
.viewer{background:white;border:1px solid #e1e6e9}.viewer-head{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #edf0f2;gap:10px}
.viewer-title{font-weight:600;font-size:14px}.graph{height:calc(100vh - 295px);min-height:460px}.status{padding:10px 16px;color:#597079;font-size:11px;border-top:1px solid #edf0f2;min-height:34px}
.graph .js-plotly-plot,.graph .plot-container{height:100%!important}
.warning{color:#915119;background:#fff2df;padding:10px;border:1px solid #f0d5ad;border-radius:4px;margin-bottom:12px;font-size:12px}
.selection{padding:12px 0;overflow-wrap:anywhere;line-height:1.7}.selection strong{color:#9b2864}details{margin-top:12px;line-height:1.7}summary{cursor:pointer;color:#397377}pre{white-space:pre-wrap;font-size:11px;overflow-wrap:anywhere}
input[type=date]{padding:8px;border:1px solid #cbd5db;border-radius:4px;width:100%;font:inherit}.layer-list label{font-size:12px;font-weight:400;margin:10px 0}.layer-list input{margin-right:7px}
.time-value{font-size:22px;font-variant-numeric:tabular-nums;margin:10px 0 20px}.rc-slider{margin:0 8px 20px;width:calc(100% - 16px)}
@media(max-width:1050px){.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.workspace{grid-template-columns:245px minmax(0,1fr)}main{padding:12px}.graph{height:580px}}
@media(max-width:650px){header{padding:0 15px}.tag{display:none}.workspace{display:flex;flex-direction:column}aside{border-right:0;border-bottom:1px solid #dce2e5;padding:15px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.graph{height:480px;min-height:480px}main{padding:10px}.viewer-head{flex-wrap:wrap}}
"""


def build_dashboard(city: City, weather: Weather) -> Dash:
    app=Dash(__name__,title='MUBES | Solar explorer',update_title='Calculating solar exposure...')
    app.index_string='<!DOCTYPE html><html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}<style>'+CSS+'</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>'
    options=[{'label':f'{b.address or b.uid[:12]} | {b.year} | {b.uid}', 'value':b.uid}
             for b in city.buildings.values() if b.target]
    warning=' '.join(city.warnings)
    app.layout=html.Div([
        html.Header([html.Div('MUBES',className='brand'),html.Div('SOLAR EXPLORER',className='tag'),html.Div('Stockholm / 1965-1975',className='subtle')]),
        html.Div(className='workspace',children=[
            html.Aside([
                html.H2('Solar & shading'),html.Div(f'{len(city.target_ids)} target buildings / {len(city.buildings)-len(city.target_ids)} context',className='subtle'),
                html.Div(f'Saved simulation cohort: {len(city.target_ids)} of {city.year_count} year matches' if city.cohort else f'All {city.year_count} year matches',className='subtle'),
                html.Label('BUILDING'),dcc.Dropdown(id='building',options=options,placeholder='Search address or UUID',clearable=True),
                html.Div(id='selection',className='selection'),html.Label('DATE / LOCAL STANDARD TIME'),
                dcc.DatePickerSingle(id='date',date='2025-06-21',display_format='DD MMM YYYY',initial_visible_month='2025-06-01'),
                html.Div('UTC+01:00, no daylight saving',className='subtle'),
                html.Div(id='time-label',className='time-value'),
                dcc.Slider(id='minute',min=0,max=1435,step=5,value=720,marks={0:'00',360:'06',720:'12',1080:'18'}),
                html.Label('ANIMATION STEP'),dcc.Dropdown(id='step',options=[{'label':f'{n} minutes','value':n} for n in [5,15,30,60]],value=30,clearable=False),
                html.Div([html.Button('Play',id='play',className='play',title='Play or pause selected day'),html.Button('Reset camera',id='reset',title='Restore camera in the current extent')],className='controls-row',style={'marginTop':'14px'}),
                dcc.Checklist(id='focus',options=[{'label':'Focus selected neighborhood','value':'focus'}],value=['focus'],className='layer-list'),
                html.Label('FACADE DISPLAY'),dcc.Dropdown(id='mode',options=[{'label':'Direct irradiance (W/m2)','value':'direct'},
                    {'label':'Direct + diffuse estimate','value':'total'},{'label':'Sunlit / shaded','value':'status'}],value='direct',clearable=False),
                html.Label('BUILDING LAYERS'),dcc.RadioItems(id='visibility',options=[{'label':'All buildings','value':'all'},
                    {'label':'Targets only','value':'targets'},{'label':'Context only','value':'context'}],value='all',className='layer-list'),
                dcc.Checklist(id='layers',options=[{'label':'Sun direction','value':'sun'},{'label':'Surface normals','value':'normals'},
                    {'label':'Surrounding wall sheets','value':'shading'},{'label':'Sunlight rays','value':'rays'},
                    {'label':'Ground shadows','value':'ground'}],value=['sun','shading','rays'],className='layer-list'),
                html.Div('Visibility changes do not remove buildings from obstruction calculations.',className='subtle'),
            ]),
            html.Main([
                html.Div(warning,className='warning',style={'display':'block' if warning else 'none'}),
                html.Div(id='metrics',className='metrics'),
                html.Div(className='viewer',children=[
                    html.Div([html.Div('Facade solar exposure',className='viewer-title'),html.Div(id='weather-label',className='subtle')],className='viewer-head'),
                    dcc.Loading(dcc.Graph(id='city',className='graph',responsive=True,style={'height':'calc(100vh - 295px)','minHeight':'460px'},config={'displaylogo':False,'scrollZoom':True,'responsive':True,
                        'toImageButtonOptions':{'format':'png','filename':'mubes-solar','scale':3}}),type='circle'),
                    html.Div(id='status',className='status',role='status'),
                ]),
                html.Details([html.Summary('Calculation method & data provenance'),
                    html.P(f'Facade direct irradiance = DNI x max(normal dot sun direction, 0) x sunlit fraction, in W/m2. '
                           f'{city.samples**2} equal-area rays per wall; R-tree indexed triangle intersections. '
                           'Shaded area includes away-facing and night-time surfaces. Summary irradiance is area-weighted direct radiation.'),
                    html.P('Surrounding wall sheets use the companion Walls.geojson endpoints and zmin/zmax elevations. '
                           'Both these opaque wall sheets and building envelopes participate in ray intersections. '
                           'Yellow lines show incoming sunlight ending at its first opaque surface; orange points mark obstruction. '
                           'Dashed grey paths behind obstructions carry no direct sunlight. Visible rays are capped at 120 samples '
                           'and their incoming lengths are clipped to 65 m; the irradiance calculation is not downsampled.'),
                    html.P('Optional diffuse estimate adds DHI/2 for vertical walls. Sky obstruction of diffuse radiation, reflections, '
                           'trees, terrain shading and glazing transmission are not modelled. Ground shadows project onto a horizontal '
                           'plane at the lowest building base; they are not terrain-corrected. Context is limited to this input dataset. '
                           'Raw surveyed envelopes are extruded with flat roofs; no Atemp geometry correction is applied.'),
                    html.P('EPW supplies hourly mean radiation; finer time controls change solar direction and ray shading, not weather resolution. '
                           'Sun uses pvlib NREL SPA. EPW local standard time excludes daylight-saving shifts. '
                           '3D envelope heights take precedence over the rounded height property. Facade azimuth is clockwise from grid north; '
                           'solar directions include the SWEREF meridian convergence correction.'),
                    html.Pre(json.dumps(city.report(),indent=2)),
                    html.P(f'Weather: {weather.path or "Stockholm fallback / explicitly estimated clear sky"}'),
                ]),
            ]),
        ]),dcc.Interval(id='tick',interval=2500,disabled=True),dcc.Store(id='busy',data=False),
    ])

    @app.callback(Output('minute','value'),Output('tick','disabled'),Output('play','children'),
                  Input('tick','n_intervals'),Input('play','n_clicks'),State('minute','value'),State('step','value'),State('tick','disabled'),State('busy','data'),prevent_initial_call=True)
    def animate(ticks,clicks,minute,step,paused,busy):
        if ctx.triggered_id=='play':return no_update,not paused,'Play' if not paused else 'Pause'
        if busy:return no_update,no_update,no_update
        value=minute+step
        return (0,True,'Play') if value>=1440 else (value,False,'Pause')

    @app.callback(Output('building','value'),Input('city','clickData'),prevent_initial_call=True)
    def select_wall(click):
        if click and click.get('points'):
            uid=click['points'][0].get('customdata')
            if uid in city.target_ids:return uid
        return no_update

    @app.callback(Output('city','figure'),Output('metrics','children'),Output('status','children'),
                  Output('time-label','children'),Output('weather-label','children'),Output('selection','children'),
                  Input('date','date'),Input('minute','value'),Input('mode','value'),Input('visibility','value'),
                  Input('layers','value'),Input('building','value'),Input('reset','n_clicks'),Input('focus','value'),
                  running=[(Output('busy','data'),True,False)])
    def update(date,minute,mode,visibility,layers,selected,reset,focus):
        started=time.perf_counter()
        try:
            sun=weather.at(date,minute)
            result=radiation(city,sun)
            figure=make_figure(city,sun,result,mode,visibility,layers,selected,reset or 0,bool(focus))
            stats=[('Target buildings',str(len(city.target_ids))),('Wall surfaces',f'{len(city.walls):,}'),
                   ('Sun altitude / azimuth',f'{sun["altitude"]:.1f} / {sun["azimuth"]:.1f} deg'),
                   ('Sunlit facade area',f'{result["sunlit_area"]:,.0f} m2'),('Shaded facade area',f'{result["shaded_area"]:,.0f} m2'),
                   ('Mean direct irradiance',f'{result["mean"]:.1f} W/m2')]
            cards=[html.Div([html.Span(k),html.Strong(v)],className='metric') for k,v in stats]
            b=city.buildings.get(selected)
            selection=[html.Strong(b.uid),html.Div(f'{b.address} | {b.year} | {b.height:.2f} m | {b.floors} floors')] if b else 'All target buildings'
            status=f'Calculated in {time.perf_counter()-started:.2f} s | {city.samples**2} rays/wall | '+('Sun below horizon' if sun['altitude']<=0 else 'Geometric shading active')
            return figure,cards,status,sun['time'],f'{sun["source"]} | DNI {sun["dni"]:.0f} / DHI {sun["dhi"]:.0f} W/m2',selection
        except Exception as exc:
            LOG.exception('Dashboard calculation failed')
            return no_update,no_update,f'ERROR: {exc}. Display remains at the last successful time.',no_update,no_update,no_update
    return app


def validate(city: City,weather: Weather) -> dict:
    """Physics and data checks using real buildings; no fabricated city inputs."""
    for solid,mesh in zip(city.solids,city.meshes):
        assert mesh.is_watertight
        assert abs(abs(mesh.volume)-solid.polygon.area*(solid.top-solid.bottom))<max(.01,abs(mesh.volume)*1e-7)
    # Independently verify selected actual rays against 2D polygon entry/exit
    # intervals and prism elevations, without using the triangle intersector.
    def prism_hit(origin: np.ndarray,direction: np.ndarray) -> bool:
        horizontal=np.linalg.norm(direction[:2])
        distance=city.extent*3
        ray=LineString([origin[:2],origin[:2]+direction[:2]/horizontal*distance])
        for solid in city.solids:
            intersection=solid.polygon.intersection(ray)
            pieces=[intersection] if intersection.geom_type=='LineString' else getattr(intersection,'geoms',[])
            for part in pieces:
                if part.geom_type!='LineString' or part.length<1e-7:continue
                distances=[ray.project(shape({'type':'Point','coordinates':p})) for p in part.coords]
                lo,hi=min(distances)/horizontal,max(distances)/horizontal
                if origin[2]+lo*direction[2]<solid.top-1e-6 and origin[2]+hi*direction[2]>solid.bottom+1e-6:
                    return True
        return False
    direction=sun_vector(70-city.convergence,14)
    origins=city.sample_origins[(np.repeat(city.normals@direction>0,city.samples**2))][::149]+direction*TOLERANCE
    mesh_hits=city.rays.intersects_any(origins,np.tile(direction,(len(origins),1)))
    independent_hits=np.array([prism_hit(p,direction) for p in origins])
    assert np.array_equal(mesh_hits,independent_hits),'Prism and triangle ray tests disagree'
    records=[]
    for minute in [300,720,1080,0]:
        sun=weather.at('2025-06-21',minute)
        start=time.perf_counter();result=radiation(city,sun)
        assert np.all((result['shaded']>=0)&(result['shaded']<=1))
        assert np.all(result['direct']>=0)
        assert np.all(result['direct']<=sun['dni']*result['incidence']+1e-7)
        assert abs(result['sunlit_area']+result['shaded_area']-city.area.sum())<.01
        if sun['altitude']<=0:assert np.all(result['direct']==0)
        cardinal=np.array([[0,1,0],[1,0,0],[0,-1,0],[-1,0,0]])@sun_vector(sun['azimuth'],sun['altitude'])
        if minute==720:assert cardinal[2]>0 and cardinal[0]<0
        if minute==300:assert cardinal[1]>0 and cardinal[3]<0
        if minute==1080:assert cardinal[3]>0 and cardinal[1]<0
        active=result['incidence']>1e-6
        blocked=active&(result['shaded']>0)
        if sun['dni']>0 and blocked.any():
            assert np.all(result['direct'][blocked] < (sun['dni']*result['incidence'])[blocked])
        paths=city.sunlight_paths(sun['azimuth']-city.convergence,sun['altitude'],None)
        if sun['altitude']<=0:
            assert not len(paths['indices'])
        elif len(paths['indices']):
            direction=sun_vector(sun['azimuth']-city.convergence,sun['altitude'])
            forward=city.rays.intersects_any(paths['targets']+TOLERANCE*direction,
                                           np.tile(direction,(len(paths['targets']),1)))
            assert np.array_equal(forward,paths['blocked']),'Visible rays disagree with shading tests'
            if paths['blocked'].any():
                _,distances,_=city.mesh.nearest.on_surface(paths['ends'][paths['blocked']])
                assert np.all(distances<1e-6),'Visible hit is not on an opaque surface'
        records.append(dict(sun,seconds=time.perf_counter()-start,mean_direct=result['mean'],
                            sunlit_area=result['sunlit_area'],obstructed_facing_walls=int(blocked.sum()),
                            clear_facing_walls=int((active&(result['shaded']==0)).sum())))
    return {'data':city.report(),'conditions':records,'independent_rays_checked':len(origins),
            'validation':'Passed watertightness, volume, independent ray, numerical and orientation assertions'}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=DATASET)
    parser.add_argument('--cohort',type=Path,default=COHORT_FILE)
    parser.add_argument('--all-years',action='store_true',help='Use every year-matching building, not the saved simulation cohort')
    parser.add_argument('--crs',help='Override input CRS; calculations use EPSG:3006')
    parser.add_argument('--fields',default='{}',help='JSON mapping of id/year/height/floors/address fields')
    parser.add_argument('--epw',type=Path,default=EPW_FILE)
    parser.add_argument('--no-weather',action='store_true',help='Explicit Stockholm clear-sky fallback; not measured weather')
    parser.add_argument('--samples',type=int,default=SAMPLES,choices=range(2,9),help='Number of samples along each wall dimension')
    parser.add_argument('--port',type=int,default=8057)
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='[%(levelname)s] %(message)s')
    try:
        mapping={**FIELD_OVERRIDES,**json.loads(args.fields)}
        city=City(args.dataset,None if args.all_years else args.cohort,args.crs,mapping,args.samples)
        weather=Weather(None if args.no_weather else args.epw)
        print(json.dumps(city.report(),indent=2))
        if args.validate:
            print(json.dumps(validate(city,weather),indent=2))
            return
        build_dashboard(city,weather).run(host='127.0.0.1',port=args.port,debug=False)
    except Exception as exc:
        LOG.exception('Startup failed: %s',exc)
        raise SystemExit(1) from exc


if __name__ == '__main__':
    main()
