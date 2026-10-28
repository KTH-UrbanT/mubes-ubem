# Integrated 1965–1975 scenario results

`integrated_results.csv` contains one row per UUID per scenario. `SvB_Base`
is the baseline; all other scenarios are ECM cases. Requested column names
are retained. The `Data_` columns contain annual aggregates, not hourly arrays.

## Sources and units

- First processing step for every scenario:
  `Utilities.GetData(path, extravariables=['HeatedArea', 'Other', 'VentSyst'])`,
  where `Utilities` is `outputs.output_utilities`. UUIDs, areas, `EP_Heat`,
  and `EPC_Heat` are taken directly from its returned arrays. Annual series
  aggregation is performed afterward on its `HeatedArea` and `Other` results.
- Results: `Final_Sim_Results/<scenario>/Sim_Results/*.pickle`.
  Input/template pickles outside `Sim_Results` are excluded.
- `UUID`: `BuildDB.BuildID`, using its `BldIDKey`.
- `DB_Surf` (m²): EPC area stored in `BuildDB.DB_Surf`. MUBES may have
  apportioned this area among buildings sharing an EPC; it is not necessarily
  the unadjusted source EPC area.
- `EP_Area` (m²): `BuildDB.EPHeatedArea`.
- `EP_Heat` (kWh/m²/year): `GlobRes.Heating['District Heating [GJ]']`
  × 1000 / 3.6 / `EP_Area`, following `bin/outputs/output_utilities.py`.
- `EPC_Heat` (kWh/m²/year): sum of `BuildDB.EPCMeters.Heating` / `DB_Surf`,
  following the same utility. This is the stored EPC heating input.
- Produced electricity and surplus sold (kWh/m²/year): annual sum of
  the `Other` energy series in joules / 3,600,000 / `EP_Area`.
- Window losses and recovered heating (kWh/m²/year): annual sum of the
  `HeatedArea` energy series in joules / 3,600,000 / `EP_Area`.
- Wall and roof conduction losses (kWh/m²/year): annual sum of the hourly
  average `HeatedArea` power series in watts × 1 hour / 1000 / `EP_Area`.
  Despite their retained “Rate” column names, CSV values are annual energies.
- Incident solar radiation (kWh/m²/year of the stored wall-area series):
  annual sum of the hourly `HeatedArea` W/m² series × 1 hour / 1000.
  It is not divided by floor area. The surface aggregation already present
  in the pickle is preserved; this script does not reweight wall surfaces.

These series conversions follow `bin/outputs/OutPutHandling.ipynb`.
The extractor checks units, hourly frequency, full-year length, and finite sums.

## Building attributes and heat recovery

Attributes are joined by `50A_UUID` from
`default/data/Case_Study/SvB 1965-1975/SvB_1965_1975_Buildings.geojson`:

- `AntalPlan`: `EgenAntalPlan` (source EPC floor count).
- `AntalTrapphus`: `EgenAntalTrapphus` (source EPC stairwell count).
- `ExhX`: `VentTypFmed`, as mapped by `default/config/DefaultConfig.yml`.
- `BalX`: `VentTypFTX`, as mapped by the same configuration.
- `Heat_Recovery_Existing`: `Ja` if `ExhX == Ja` OR `BalX == Ja`, otherwise
  `Nej` when both flags are `Nej`. Missing flags produce `Unknown` unless the
  other flag is `Ja`. This describes existing EPC equipment and stays fixed
  across scenarios.
- `Scenario_ExhX`, `Scenario_BalX`: flags from that scenario's
  `BuildDB.VentSyst`, converted from booleans to `Ja`/`Nej`.
- `Heat_Recovery_Scenario`: OR of those scenario flags. This records model
  configuration; it does not independently prove equipment operation.
- `Source_Pickle`: relative path from the parent of RAW_DATA_DIR for traceability.

## Regenerate

With the project's Python environment, from the repository root:

```sh
venv/bin/python examples/result_aggregation/aggregate_results.py
```

Optional arguments: `--results`, `--geojson`, `--mubes-project`, `--output`.
Input path settings are editable at the top of the script; see `README.md`.
Only use trusted pickle files. The script imports the repository's utility
module and uses its normal pickle-loading and result-processing workflow.
It rejects duplicate scenario/UUID rows, missing requested values, and scenario
coverage differing from baseline, then writes the CSV atomically with UTF-8 BOM.
