"""Combine CEA Total_demand.csv files into one row per building and scenario.

Run: python3 aggregate_cea_results.py
Optional: --root /path/to/scenarios --output /path/to/integrated_cea_results.csv

Reads only the building identifier and Qhs_MWhyr. Demand remains in MWh/year
(total per building, NOT kWh/m2/year). No construction-loss estimates are made.
UUIDs are extracted from CEA names of the form B<UUID> or plain <UUID>.
SvB_Base is the baseline; SvB_Base_NoVent is a separate baseline variant.
Directories without a demand file are reported and skipped. Malformed files,
duplicate UUIDs, nonfinite/negative demand, and coverage differences fail before
the destination is replaced. Uses only the Python standard library.
"""

import argparse
import csv
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

# Edit this path to the folder containing the CEA scenario directories.
RAW_DATA_DIR = Path("/Users/alizad/PycharmProjects/CityEnergyAnalyst/CityEnergyAnalyst-GUI/SvB_CEA_Sim")
OUTPUT_FILE = Path(__file__).resolve().parent / "integrated_cea_results.csv"


def aggregate(root, output):
    root, output = root.resolve(), output.resolve()
    if not root.is_dir():
        raise ValueError(f'Scenario directory does not exist: {root}')
    rows, coverage = [], {}
    scenarios = sorted(root.iterdir(), key=lambda p: (p.name != 'SvB_Base', p.name))
    for scenario in scenarios:
        if not scenario.is_dir() or scenario.name.startswith('.') or scenario.name == '__pycache__':
            continue
        candidates = [scenario / directory / 'data/demand/Total_demand.csv'
                      for directory in ('outputs', 'output')]
        files = [p for p in candidates if p.is_file()]
        if not files:
            print(f'Skipped {scenario.name}: no Total_demand.csv', file=sys.stderr)
            continue
        if len(files) != 1:
            raise ValueError(f'{scenario}: ambiguous output and outputs demand files')
        source = files[0]
        ids = set()
        with source.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            name_column = 'name' if 'name' in headers else 'Name'
            if name_column not in headers or 'Qhs_MWhyr' not in headers:
                raise ValueError(f'{source}: requires name/Name and Qhs_MWhyr columns')
            for line, record in enumerate(reader, start=2):
                try:
                    name = record[name_column].strip()
                    identifier = name[1:] if name.startswith('B') else name
                    uuid = str(UUID(identifier))
                    if uuid in ids:
                        raise ValueError(f'Duplicate UUID {uuid}')
                    value = record['Qhs_MWhyr'].strip()
                    demand = Decimal(value)
                    if not demand.is_finite() or demand < 0:
                        raise ValueError(f'Invalid Qhs_MWhyr: {value}')
                except (ValueError, InvalidOperation, AttributeError) as error:
                    raise ValueError(f'{source}, row {line}: {error}') from error
                ids.add(uuid)
                scenario_type = ('Baseline' if scenario.name == 'SvB_Base' else
                                 'Baseline_NoVent' if scenario.name == 'SvB_Base_NoVent' else
                                 'ECM' if scenario.name.startswith('SvB_') else 'Other')
                rows.append({'UUID': uuid, 'Scenario': scenario.name,
                             'Scenario_Type': scenario_type, 'Qhs_MWhyr': value,
                             'CEA_Name': name, 'Source_CSV': source.relative_to(root).as_posix()})
        if not ids:
            raise ValueError(f'{source}: contains no building results')
        coverage[scenario.name] = ids
        print(f'{scenario.name}: {len(ids)} buildings')
    if 'SvB_Base' not in coverage:
        raise ValueError('Missing SvB_Base demand results')
    baseline = coverage['SvB_Base']
    for scenario, ids in coverage.items():
        if ids != baseline:
            raise ValueError(f'{scenario}: {len(baseline - ids)} missing and '
                             f'{len(ids - baseline)} additional UUIDs versus SvB_Base')
    rows.sort(key=lambda r: (r['Scenario'] != 'SvB_Base', r['Scenario'], r['UUID']))
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + '.tmp')
    with temp.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with temp.open(newline='', encoding='utf-8-sig') as stream:
        saved = list(csv.DictReader(stream))
    if saved != rows:
        raise ValueError('CSV round-trip verification failed')
    temp.replace(output)
    print(f'Wrote {len(rows)} rows across {len(coverage)} scenarios to {output}')
    print('Scenario types:', dict(Counter(r['Scenario_Type'] for r in rows)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=RAW_DATA_DIR)
    parser.add_argument('--output', type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    try:
        aggregate(args.root.expanduser(), args.output.expanduser())
    except (ValueError, OSError) as error:
        parser.exit(1, f'Error: {error}\n')
