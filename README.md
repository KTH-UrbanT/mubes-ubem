# MUBES UBEM
MUBES UBEM is a simulation tool for bottom–up physical urban building energy modelling (UBEM). In a nutshell, it is a Python script-based framework for the automatic generation and management of many dynamic building physics models that are simulated using the thermal engine of [EnergyPlus (EP)](https://energyplus.net).

![Minneberg](docs/districts.jpg)

MUBES UBEM allows to:
* all main features
* should come
* here

It can launch simulations using parallel computing or can automatically creates FMUs of each building in order to make co-simulation afterward (the co-simulation process, using FMPy).


## Installation
MUBES UBEM is a multi-platform framework that can be run on Windows, Mac or Linux (Ubuntu).

### Base environment
1. Install Python 3.7 or higher, use of virtual environment is highly recommended. 
2. Install EnergyPlus 9.1 or higher.
3. Clone the repository to your local machine.
4. Install the required Python packages provided in the **requirements.txt** file:

`pip install -r requirements.txt`

5. Rename the [env.default.yml](default/config/env.default.yml) in [default/config](default/config/) folder into env.yml and change the line with a path to EnergyPlus to your local one: 

`PATH_TO_ENERGYPLUS : C:/EnergyPlusV9-1-0`

### Co-simulation 
The FMUs creation option uses the [EnergyPlusToFMU-v3.1.0](https://simulationresearch.lbl.gov/fmu/EnergyPlus/export/userGuide/download.html) toolkit developed by LNBL. This toolkit should be downloaded and installed at the same level as MUBES UBEM under a folder named __FMUsKit__ (see build-fmus.buildEplusFMU() in the [bin](bin) folder).

The portability of FMUs (use at another computer than the one used to generate them) is valid. However, as for now it is only possible when no external files are used as errors are encountered when relative paths are defined.  

⚠️ On Windows 10, a time delay had to be introduced in the original FMU toolkit code to ensure that the intermediate files are removed and the FMU can finish properly (https://github.com/lbl-srg/EnergyPlusToFMU/issues/54).

## Examples
You can get started through running the sample scripts provided in the [examples](examples/examples.md) folder.

## Documentation
More details on the structure of UBEM can be found  [here](docs/documentation.md).

## Development and contribution
While the base version of the platform is stable now, it is under further continous development. Newcomers are welcome to join by forking and proposing changes. The platform has been developed with passion, hope you'll enjoy it as well 🙂

## Credits
This work has been developed within KTH/SEED/REI/UrbanT, funded by the MUBES project (No 46896-1, E2B2 research programme, Swedish Energy Agency).

## Citation
If you rely on this package in academic work, and would like to include a citation (which we greatly appreciate), please refer to this publication:

* Faure, X.; Johansson, T.; Pasichnyi, O. The Impact of Detail, Shadowing and Thermal Zoning Levels on Urban Building Energy Modelling (UBEM) on a District Scale. Energies 2022, 15, 1525. https://doi.org/10.3390/en15041525

```
@Article{FaureJohanssonPasichnyi2022,
  author={Faure, Xavier and Johansson, Tim and Pasichnyi, Oleksii},
  title   =  {The Impact of Detail, Shadowing and Thermal Zoning Levels on Urban Building Energy Modelling (UBEM) on a District Scale},
  journal =  {Energies},
  volume  =  {15},
  number  =  {4},
  pages   =  {1525},
  year    =  {2022},
  doi     =  {10.3390/en15041525},
  url     = "https://doi.org/10.3390/en15041525"
}
```

or this package directly:
* Xavier Faure, Tim Johansson, Oleksii Pasichnyi. MUBES UBEM, version 1.0 https://github.com/KTH-UrbanT/mubes-ubem [Online; accessed 20xx-xx-xx].

```
 @Misc{FaureJohanssonPasichnyi2021, title={MUBES UBEM}, author={Faure, Xavier and Johansson, Tim and Pasichnyi, Oleksii}, url={https://github.com/KTH-UrbanT/mubes-ubem}, version={1.0} 
```