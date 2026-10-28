"""Extract annual scenario results through Utilities.GetData.

Run with the project's Python environment. Only load trusted MUBES pickles.
See integrated_results_README.md for column definitions and units.
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path


# Edit these paths when your raw data or MUBES installation moves.
RAW_DATA_DIR = Path("/Users/alizad/PycharmProjects/NewWorking-MUBES/examples/1965-1975/Final_Sim_Results")
MUBES_PROJECT_DIR = Path("/Users/alizad/PycharmProjects/NewWorking-MUBES")
GEOJSON_FILE = MUBES_PROJECT_DIR / "default/data/Case_Study/SvB 1965-1975/SvB_1965_1975_Buildings.geojson"
OUTPUT_FILE = Path(__file__).resolve().parent / "integrated_results.csv"


# Location, variable name, stored unit. Output follows OutPutHandling.ipynb.
SERIES = [
    ('Other', 'Electric Load Center Produced Electricity Energy', 'J'),
    ('Other', 'ElectricitySurplusSold:Facility', 'J'),
    ('HeatedArea', 'Zone Windows Total Heat Loss Energy', 'J'),
    ('HeatedArea', 'Surface Inside Face Conduction Heat Loss Rate On Vertical Walls', 'W'),
    ('HeatedArea', 'Surface Inside Face Conduction Heat Loss Rate On Roofs', 'W'),
    ('HeatedArea', 'Zone Ideal Loads Heat Recovery Total Heating Energy', 'J'),
    ('HeatedArea', 'Surface Outside Face Incident Solar Radiation Rate per Area On Vertical Walls', 'W/m2'),
]


def status(value):
    if value is True or str(value).strip().lower() in {'ja', 'true', '1'}:
        return 'Ja'
    if value is False or str(value).strip().lower() in {'nej', 'false', '0'}:
        return 'Nej'
    return 'Unknown'


def recovery(exhx, balx):
    if 'Ja' in (exhx, balx):
        return 'Ja'
    return 'Nej' if exhx == balx == 'Nej' else 'Unknown'


def annual_value(result, location, name, unit, area):
    data = result[location]
    values = data['Data_' + name]
    if data['Unit_' + name] != unit:
        raise ValueError(f'Unexpected unit for {name}: {data["Unit_" + name]}')
    if data['TimeStep_' + name] != 'Hourly' or len(values) not in (8760, 8784):
        raise ValueError(f'Expected full-year hourly series: {name}')
    total = math.fsum(values)
    if not math.isfinite(total):
        raise ValueError(f'Non-finite data: {name}')
    if unit == 'J':
        return total / 3_600_000 / area
    if unit == 'W':
        return total / 1000 / area  # Hourly average W × 1 hour.
    return total / 1000  # Solar series already per unit wall area.


def aggregate(root, geojson, output, mubes_project=MUBES_PROJECT_DIR):
    utility = mubes_project.expanduser().resolve() / 'bin/outputs/output_utilities.py'
    if not utility.is_file():
        raise ValueError(f'MUBES utility not found: {utility}. Set MUBES_PROJECT_DIR or --mubes-project.')
    sys.path.insert(0, str(utility.parents[1]))
    from outputs import output_utilities as Utilities
    root, geojson, output = root.resolve(), geojson.resolve(), output.resolve()
    features = json.loads(geojson.read_text())['features']
    properties = {}
    for feature in features:
        props = feature['properties']
        uuid = props['50A_UUID']
        if uuid in properties:
            raise ValueError(f'Duplicate source UUID: {uuid}')
        properties[uuid] = props
    scenarios = sorted(p for p in root.iterdir() if p.is_dir() and (p / 'Sim_Results').is_dir())
    scenarios.sort(key=lambda p: p.name != 'SvB_Base')
    rows, seen, coverage = [], set(), {}
    for scenario in scenarios:
        ids = set()
        paths = sorted((scenario / 'Sim_Results').glob('*.pickle'))
        if not paths:
            raise ValueError(f'No completed results: {scenario}')
        # GetData is the authoritative first processing step. Restore cwd because
        # the utility changes it internally. Request the nested series as extras.
        previous_cwd = Path.cwd()
        try:
            res = Utilities.GetData(str(scenario / 'Sim_Results'),
                                    extravariables=['HeatedArea', 'Other', 'VentSyst'])
        finally:
            os.chdir(previous_cwd)
        required = ['BuildID', 'DB_Surf', 'EP_Area', 'EP_Heat', 'EPC_Heat',
                    'SimNum', 'HeatedArea', 'Other', 'VentSyst']
        if any(len(res[k]) != len(paths) for k in required):
            raise ValueError(f'{scenario}: GetData returned incomplete or misaligned results')
        paths_by_number = {}
        for path in paths:
            number = int(path.stem.split('_')[1].split('v')[0])
            if number in paths_by_number:
                raise ValueError(f'{scenario}: multiple runs for building {number}')
            paths_by_number[number] = path
        for index, build_id in enumerate(res['BuildID']):
            path = paths_by_number[res['SimNum'][index]]
            try:
                result = {k: res[k][index] for k in ['HeatedArea', 'Other']}
                uuid = build_id[build_id['BldIDKey']]
                props = properties[uuid]
                key = (scenario.name, uuid)
                if key in seen:
                    raise ValueError(f'Duplicate scenario/UUID: {key}')
                seen.add(key)
                ids.add(uuid)
                area, db_area = float(res['EP_Area'][index]), float(res['DB_Surf'][index])
                if not (area > 0 and db_area > 0):
                    raise ValueError('Non-positive area')
                # Source EPC flags identify pre-existing recovery, independently of ECMs.
                exhx, balx = status(props.get('VentTypFmed')), status(props.get('VentTypFTX'))
                vent = res['VentSyst'][index]
                row = {
                    'UUID': uuid,
                    'Scenario': scenario.name,
                    'Scenario_Type': 'Baseline' if scenario.name == 'SvB_Base' else 'ECM',
                    'DB_Surf': db_area,
                    'EP_Area': area,
                    'EP_Heat': float(res['EP_Heat'][index]),
                    'EPC_Heat': float(res['EPC_Heat'][index]),
                }
                for location, name, unit in SERIES:
                    row['Data_' + name] = annual_value(result, location, name, unit, area)
                row.update({
                    'AntalPlan': float(props['EgenAntalPlan']),
                    'AntalTrapphus': float(props['EgenAntalTrapphus']),
                    'ExhX': exhx,
                    'BalX': balx,
                    'Heat_Recovery_Existing': recovery(exhx, balx),
                    'Scenario_ExhX': status(vent.get('ExhX')),
                    'Scenario_BalX': status(vent.get('BalX')),
                    'Heat_Recovery_Scenario': recovery(status(vent.get('ExhX')), status(vent.get('BalX'))),
                    'Source_Pickle': path.relative_to(root.parent).as_posix(),
                })
                if any(value == '' for value in row.values()):
                    raise ValueError('Missing requested value or unrecognized recovery status')
                rows.append(row)
            except Exception as error:
                raise ValueError(f'{path}: {error}') from error
        coverage[scenario.name] = ids
        print(f'{scenario.name}: {len(paths)} results', flush=True)
    baseline = coverage['SvB_Base']
    for scenario, ids in coverage.items():
        if ids != baseline:
            raise ValueError(f'{scenario}: UUID coverage differs from baseline')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix('.csv.tmp')
    with temp.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(output)
    with output.open(newline='', encoding='utf-8-sig') as stream:
        saved = list(csv.DictReader(stream))
    assert len(saved) == len(rows)
    assert len({(r['Scenario'], r['UUID']) for r in saved}) == len(rows)
    print(f'Wrote {len(rows)} rows, {len(rows[0])} columns to {output}')
    print('Baseline existing recovery:', dict(Counter(r['Heat_Recovery_Existing'] for r in rows if r['Scenario_Type'] == 'Baseline')))


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=RAW_DATA_DIR)
    parser.add_argument('--geojson', type=Path, default=GEOJSON_FILE)
    parser.add_argument('--output', type=Path, default=OUTPUT_FILE)
    parser.add_argument('--mubes-project', type=Path, default=MUBES_PROJECT_DIR)
    args = parser.parse_args()
    aggregate(args.results.expanduser(), args.geojson.expanduser(), args.output.expanduser(), args.mubes_project)
