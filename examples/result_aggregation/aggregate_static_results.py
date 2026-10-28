"""Convert static component savings JSON to one row per UUID and ECM.

Usage: python3 aggregate_static_results.py --input /path/to/Static.json
Optional: --output /path/to/integrated_static_results.csv

Expected input: a JSON list with UUID, EP_Area, WindowLoss, WallLoss,
RoofLoss and HeatRecovery. Values represent changes: negative means savings.
Output retains the signed Source_Value and defines Heat_Saving = -Source_Value.
Both use the source units; no energy/area conversion is applied. Positive
source values therefore remain negative savings (increases in demand).

BaseHeatDemand is not used: zero is not evidence of actual baseline demand.
Only four individual ECMs are exported. Combined savings and post-retrofit
demand are not inferred. No third-party Python packages are required.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from uuid import UUID

# Edit the raw-data directory and JSON filename here.
RAW_DATA_DIR = Path("/Users/alizad/PycharmProjects/NewWorking-MUBES/examples/1965-1975/Analysis_Temp")
RAW_DATA_FILENAME = "Static_SvB.json"
OUTPUT_FILE = Path(__file__).resolve().parent / "integrated_static_results.csv"


ECMS = {'SvB_Window': 'WindowLoss', 'SvB_Wall': 'WallLoss',
        'SvB_Roof': 'RoofLoss', 'SvB_HeatRecovery': 'HeatRecovery'}


def aggregate(source, output):
    source, output = source.resolve(), output.resolve()
    if source == output:
        raise ValueError('Output must not overwrite the source JSON')
    records = json.loads(source.read_text(encoding='utf-8-sig'))
    if not isinstance(records, list) or not records:
        raise ValueError('Expected a nonempty JSON list of building records')
    rows, seen = [], set()
    for index, record in enumerate(records):
        try:
            uuid = str(UUID(record['UUID']))
            if uuid in seen:
                raise ValueError(f'Duplicate UUID: {uuid}')
            seen.add(uuid)
            area = float(record['EP_Area'])
            if not math.isfinite(area) or area <= 0:
                raise ValueError('EP_Area must be finite and positive')
            for scenario, field in ECMS.items():
                value = float(record[field])
                if not math.isfinite(value):
                    raise ValueError(f'{field} must be finite')
                rows.append({'UUID': uuid, 'Scenario': scenario,
                             'Scenario_Type': 'ECM', 'EP_Area': area,
                             'Source_Field': field, 'Source_Value': value,
                             'Heat_Saving': -value if value else 0.0,
                             'Source_JSON': str(source)})
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            raise ValueError(f'{source}, record {index + 1}: {error}') from error
    rows.sort(key=lambda r: (r['Scenario'], r['UUID']))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.tmp')
    with temporary.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with temporary.open(newline='', encoding='utf-8-sig') as stream:
        saved = list(csv.DictReader(stream))
    if len(saved) != len(rows) or len({(r['UUID'], r['Scenario']) for r in saved}) != len(rows):
        raise ValueError('CSV row count or uniqueness verification failed')
    for original, written in zip(rows, saved):
        if float(written['Heat_Saving']) != -original['Source_Value']:
            raise ValueError('CSV savings verification failed')
    temporary.replace(output)
    print(f'Wrote {len(rows)} rows: {len(seen)} buildings x {len(ECMS)} ECMs to {output}')
    print('Heat_Saving = -Source_Value; units unchanged from input.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=RAW_DATA_DIR / RAW_DATA_FILENAME, help='Static savings JSON')
    parser.add_argument('--output', type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    try:
        aggregate(args.input.expanduser(), args.output.expanduser())
    except (ValueError, OSError) as error:
        parser.exit(1, f'Error: {error}\n')
