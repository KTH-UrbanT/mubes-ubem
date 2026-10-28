# Result aggregation scripts

This folder can be moved independently of the raw data. Edit the path settings
near the top of each script, then run it. All outputs default to this folder.
Raw data stays in its original location.

| Script | Settings to edit | Output |
| --- | --- | --- |
| `aggregate_results.py` | `RAW_DATA_DIR`, `MUBES_PROJECT_DIR`, `GEOJSON_FILE` | `integrated_results.csv` |
| `aggregate_cea_results.py` | `RAW_DATA_DIR` | `integrated_cea_results.csv` |
| `aggregate_static_results.py` | `RAW_DATA_DIR`, `RAW_DATA_FILENAME` | `integrated_static_results.csv` |

Use absolute paths. Paths initially point to the existing data on this machine.
Change them if the raw data moves. `OUTPUT_FILE` can also be edited.

Run from this folder:

```sh
/Users/alizad/PycharmProjects/NewWorking-MUBES/venv/bin/python aggregate_results.py
python3 aggregate_cea_results.py
python3 aggregate_static_results.py
```

MUBES requires its project Python environment and its repository: it still calls
`Utilities.GetData` first. CEA and Static require only Python's standard library.

Command-line paths override the settings:

```sh
python3 aggregate_results.py --results /data/Final_Sim_Results --mubes-project /code/MUBES --geojson /data/buildings.geojson --output /results/mubes.csv
python3 aggregate_cea_results.py --root /data/SvB_CEA_Sim --output /results/cea.csv
python3 aggregate_static_results.py --input /data/Static.json --output /results/static.csv
```

MUBES energy intensities are annual kWh/m²; CEA `Qhs_MWhyr` remains total MWh/year.
Static values remain in source units, with `Heat_Saving = -Source_Value`.
See `integrated_results_README.md` for MUBES column definitions.
