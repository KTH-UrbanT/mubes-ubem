"""Extract Solkartan annual PV for the solarvisualization.py cohort. Run from repo root."""
import concurrent.futures, json, math, re, sys
from pathlib import Path
from datetime import datetime, timezone
import requests
from pyproj import Transformer
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import transform, unary_union
from shapely.validation import make_valid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from solarvisualization import extract_solids, DATASET, COHORT_FILE
OUT=Path(__file__).resolve().parent
URL='https://gis.miljo.stockholm.se/server/rest/services/Solinstr%C3%A5lning/FeatureServer/2/query'
ids=set(re.findall(r'50A_UUID\s*:\s*([\da-fA-F-]{36})',COHORT_FILE.read_text()))
tr=Transformer.from_crs(3006,3011,always_xy=True)
ll=Transformer.from_crs(3011,4326,always_xy=True)
buildings=[]
for f in json.loads(DATASET.read_text())['features']:
 p=f['properties']; uid=p['50A_UUID']
 if uid not in ids or not 1965<=int(p['43S_BYGGAR'])<=1975: continue
 geom=unary_union([s.polygon for s in extract_solids(f,uid,None,tr,[])])
 buildings.append((uid,p,geom))
assert len(buildings)==159, len(buildings)
(OUT/'raw').mkdir(exist_ok=True)
def fetch(b):
 uid,p,g=b; cache=OUT/'raw'/f'{uid}.json'
 if cache.exists(): return json.loads(cache.read_text())
 params=dict(f='geojson',where='1=1',geometry=','.join(map(str,g.bounds)),geometryType='esriGeometryEnvelope',inSR=3011,outSR=3011,spatialRel='esriSpatialRelIntersects',outFields='*',returnGeometry='true')
 r=requests.get(URL,params=params,timeout=60);r.raise_for_status();d=r.json()
 if 'error' in d or 'features' not in d or d.get('exceededTransferLimit'): raise RuntimeError(d)
 cache.write_text(json.dumps(d));return d
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: data=list(pool.map(fetch,buildings))
roofs={}
for d in data:
 for f in d['features']: roofs[f['properties']['FID']]=f
matches=[]
for uid,p,g in buildings:
 found=[]
 for fid,f in roofs.items():
  roof=make_valid(shape(f['geometry'])); a=g.intersection(roof).area
  if a>1 and (a/g.area>.5 or a/roof.area>.1): found.append((fid,a,a/g.area,a/roof.area,roof))
 matches.append(found)
usage={fid:sum(any(x[0]==fid for x in m) for m in matches) for fid in roofs}
rows=[]
for (uid,p,g),mm in zip(buildings,matches):
 parts=[]
 for fid,a,bfrac,rfrac,roof in mm:
  attrs=roofs[fid]['properties']; vals=[attrs.get(k) for k in ['tak_1000','tak_950_10','sol_1000','sol_950_10']]
  valid=all(v is not None and math.isfinite(float(v)) and v>=0 for v in vals)
  pv=sum(min(math.floor(.8*area+.5),.8*area)*irr*.144 for area,irr in [(vals[0],vals[2]),(vals[1],vals[3])]) if valid else None
  parts.append(dict(fid=fid,roof_overlap_fraction=rfrac,building_overlap_fraction=bfrac,shared_with_selected_buildings=usage[fid],pv_kwh_year=pv,source_attributes=attrs))
 coverage=g.intersection(unary_union([m[4] for m in mm])).area/g.area if mm else 0
 status='matched' if coverage>=.65 and all(x['roof_overlap_fraction']>=.65 and x['shared_with_selected_buildings']==1 and x['pv_kwh_year'] is not None for x in parts) else ('unmatched' if not mm else 'allocated_estimate')
 lon,lat=ll.transform(*g.representative_point().coords[0])
 estimate=sum(x['pv_kwh_year']*x['roof_overlap_fraction'] for x in parts) if parts and all(x['pv_kwh_year'] is not None for x in parts) else None
 rows.append(dict(annual_pv_kwh_year=sum(x['pv_kwh_year'] for x in parts) if status=='matched' else estimate,uuid=uid,address=p.get('IdAdr'),year=p['43S_BYGGAR'],longitude=lon,latitude=lat,footprint_m2=g.area,coverage=coverage,status=status,pv_kwh_year=sum(x['pv_kwh_year'] for x in parts) if status=='matched' else None,roofs=parts))
# Keep roof coverage fields alongside annual PV on every extraction.
for row in rows:
 roof_area = panel_area = 0.0
 for part in row['roofs']:
  attrs = part['source_attributes']
  weight = 1.0 if row['status'] == 'matched' else part['roof_overlap_fraction']
  roof_area += weight * attrs['takyta_a']
  panel_area += weight * sum(min(math.floor(.8 * attrs[key] + .5), .8 * attrs[key]) for key in ['tak_1000', 'tak_950_10'])
 row['roof_area_m2'] = roof_area
 row['potential_panel_area_m2'] = panel_area
 row['coverage_percent'] = 100 * panel_area / roof_area if roof_area > 0 else None
summary=dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),source=URL,cohort=str(COHORT_FILE.relative_to(ROOT)),count=len(rows),status_counts={s:sum(r['status']==s for r in rows) for s in ['matched','allocated_estimate','unmatched']},matched_total_kwh_year=sum(r['pv_kwh_year'] or 0 for r in rows),note='PV follows website default integer panel-area rounding, capped at 80%, factor 0.144; low-potential category excluded. Shared/larger roof polygons are allocated by intersection area / solar polygon area, assuming uniform PV potential. Allocated values are estimates, not website building-specific readings.')
summary['estimated_cohort_total_kwh_year']=sum(r['annual_pv_kwh_year'] or 0 for r in rows)
summary['allocated_total_kwh_year']=sum(r['annual_pv_kwh_year'] or 0 for r in rows if r['status']=='allocated_estimate')
summary['total_roof_area_m2'] = sum(r['roof_area_m2'] for r in rows)
summary['total_potential_panel_area_m2'] = sum(r['potential_panel_area_m2'] for r in rows)
summary['area_weighted_coverage_percent'] = 100 * summary['total_potential_panel_area_m2'] / summary['total_roof_area_m2']
valid_coverage = [r['coverage_percent'] for r in rows if r['coverage_percent'] is not None]
summary['mean_building_coverage_percent'] = sum(valid_coverage) / len(valid_coverage) if valid_coverage else None
summary['panel_coverage_definition'] = 'Potential panel area under the map default calculator, not installed PV. Roof denominator is takyta_a, the website Total Takyta. Same allocation weights as annual PV extraction. Flat-roof tilted-row spacing adjustment not applied.'
(OUT/'annual_pv_potential.json').write_text(json.dumps(dict(summary=summary,buildings=rows),indent=2))
(OUT/'matched_roofs.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=list(roofs.values()),crs=dict(type='name',properties=dict(name='EPSG:3011')))))
print(json.dumps(summary,indent=2))
for r in rows:
 if r['status']!='matched':print(r['address'],r['status'],round(r['coverage'],3),[(p['fid'],round(p['roof_overlap_fraction'],3),p['shared_with_selected_buildings']) for p in r['roofs']])

lines=['# Annual PV potential — 159 selected buildings', '', 'Source: [Stockholms solkarta](https://solkartan.miljo.stockholm.se/stockholms-solkarta/). Retrieved '+summary['retrieved_utc'][:10]+'.', '', f"Combined estimate: **{summary['estimated_cohort_total_kwh_year']:,.0f} kWh/year**. Directly matched subtotal: {summary['matched_total_kwh_year']:,.0f} kWh/year. Allocated subtotal: {summary['allocated_total_kwh_year']:,.0f} kWh/year.", '', 'Matched: full solar-map roof value where footprint coverage and roof overlap each exceed 65%, with no roof shared by selected buildings. Allocated estimate: full source roof PV multiplied by its overlap fraction with the selected footprint; assumes uniform potential within that source polygon. These estimates need roof-level refinement before design use.', '', 'Default map assumptions: up to 80% usable area, 16% module efficiency and 10% system losses (14.4% net). Only the >1000 and 950–1000 kWh/m²/year roof categories contribute. The website rounds default panel areas to integer m²; this extraction reproduces that rounding but retains unrounded energy internally. Source values are modelled annual potential, not measured production or a forecast for 2026. The map advises halving usable area for tilted panel rows on flat roofs; that additional adjustment has NOT been applied, matching the default calculator. Source survey year was not established.', '', 'The JSON preserves UUIDs, coordinates, raw source attributes, roof IDs, match coverage, direct values and allocated estimates. annual_pv_kwh_year is the usable combined column; pv_kwh_year is null when no individual direct value can be established. No existing simulation inputs were modified.', '', '| Building UUID | Address | Annual PV (kWh/year) | Method |', '|---|---|---:|---|']
for r in sorted(rows,key=lambda r:r['address'] or ''):
 lines.append(f"| {r['uuid']} | {r['address']} | {r['annual_pv_kwh_year']:,.0f} | {r['status']} |")
(OUT/'annual_pv_potential.md').write_text('\n'.join(lines)+'\n')
