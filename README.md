# MUBES UBEM
MUBES UBEM is a simulation tool for bottom–up physical urban building energy modelling (UBEM). In a nutshell, it is a Python script-based framework for the automatic generation and management of many dynamic building physics models that are simulated using the thermal engine of [EnergyPlus (EP)](https://energyplus.net).

![Minneberg](docs/Minneberg.jpg)

It can launch simulations using parallel computing or can automatically creates FMUs of each building in order to make co-simulation afterward (the co-simulation process, using FMPy, is validated in Windows, Mac and Linux (Ubuntu)).

## Environment
It is a Python script-based UBEM simulation tool using EnergyPlus (EP) as the thermal engine.
It has been developed in Python 3.7 with EP 9.1 on Windows and has been successfully tested with EP 9.4 and python 3.9. on Windows and python 3.8 on Ubuntu 20.04 (tested on Oracle Virtual Machine) and with python 3.9 and EP 9.5 on OS x 11.5.2.
It is based on 2 main packages: [EPPY](https://github.com/santoshphilip/eppy) and [GeomEppy](https://github.com/jamiebull1/geomeppy).

## Installation
1. Clone the repository to your local machine.
2. Install the required Python packages provided in the **requirements.txt** file:

`pip install -r requirements.txt`  

__Note__ : A customized version of GeomEppy package is used.

The FMUs creation option uses the [EnergyPlusToFMU-v3.1.0](https://simulationresearch.lbl.gov/fmu/EnergyPlus/export/userGuide/download.html) toolkit developed by LNBL. This toolkit should be downloaded and installed at the same level as MUBES_UBEM under a folder named __FMUsKit__ (see BuildFMUs.buildEplusFMU() in the CoreFile folder).  
The portability of FMUs (used on another computer than the one used to generate them) is valid but currently only when no external files are used as error are encountered when relative paths are defined.  
/!\ On Windows 10, some time delay had to be introduced in the original FMU toolkit code to enable to remove the intermediate files and make the FMU reach its end properly (https://github.com/lbl-srg/EnergyPlusToFMU/issues/54).

## Documentation

### Inputs
All inputs are dealt with an external *.yml file.  
Several thermal zoning options are proposed from single heated and non-heated zones up to core and perimeter zones for each building floor.
The main input file is in a geojson format. It contains the footprint including height (3D vertexes, or 2D vertexes and height as an attribut) of each building's surface as well as some propreties taken from several databases (EPCs, and others).

### Model structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation's parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all elements needed at the zone level),
- output level (deals with outpouts variables and frequency).

### Folder organization
The MUBES_UBEM main folder contains several subfolders:  
__CoreFile__  : contains all the core python scripts for the several levels of the building design process.  
__ExternalFiles__  : contains commun external files that one would use for all the buildings considered in the process. It currently contains the times series of cold water input temperature for the Domestic Hot Water needs as well as the water taps in l/min. The latter is an output from an other packages ([StROBe](https://github.com/open-ideas/StROBe)) that enables to create stochastics outputs for residential occupancy.    
__BuildObject__  : contains the building class object, filters to skip building from the input file and some geometric utilities used.  
__ModelerFolder__ : contains the *runMUBES.py* file as well as two examples of FMU simulations. An example of geojson is also provided. *MakeShadowingWallFile.py* enables to create a Json input file for further shadowing effect consideration.  
__ReadResults__ : contains one template to read the results and some functions for post-processing in the Utilities.py file.  

## Examples
You can get started through running the sample models provided in the [examples](examples) folder.

### Running a simulation case
__First__ __thing__ : Change the path to EnergyPlus and (if needed) to the Data (geojson files).  
Simply change the path in the *LocalConfig_Template.yml* file in __ModelerFolder__ and give it another name (for further updates).  
(Note: see *CoreFile/DefaultConfig.yml* to see all possible changes in  *xxx.yml* files).  

*__python__ __runMUBES.py__* will launch the simulation using the *DefaultConfig.yml* modified by *LocalConfig.yml* file is in __ModelerFolder__.   
*__python__ __runMUBES.py__ __-yml__ __path_to_config.yml__* will launch the simulation using the information given in the path_to_config.yml. The latter can contain only the changes wanted from the DefaultConfig.yml.  
*__python__ __runMUBES.py__ __-CONFIG__ __{JSON Format}__* will launch the simulation using the information given in the {JSON Format} as arguments. The latter can contain only the changes wanted from the DefaultConfig.yml.  

__Note__ : *ConfigFile.yml* are systematically saved in the result folder and can thus be used afterward with the *-yml* argument

__Outputs_Template.txt__ : This file proposes a list of available outputs from EP. It has been build from a .rdd file from EP. The required outputs should be indicated in this file. It also indicates at which frequency the modeler wants his outputs.

### Reading the outputs  
The __ReadResults__ folder contains also a template for post-processing the results :  
*ReadOutputs_Template.py* proposes a basic post-processing stage including reading the data, ploting the areas of footprint and the energy needs as well as some times series for specific building number. Its works for simulation done with or without FMUs.  
*Utilities.py* contains several useful functions for the post-processing stage. The *getData()* is highly helpful. It gathers all the pickle files present in a directory into one dictionnary. It can deal with several CaseNames and overplots results for same Building's Ids by simply appending the path's list.   
*__python__ __ReadOutputs_Template.py__* will load the results from CaseName given in the *LocalConfig.yml*.  
*__python__ __ReadOutputs_Template.py__ __-yml__ __path_to_config.yml__* will load the results from CaseName given in the *path_to_config.yml*.  
*__python__ __ReadOutputs_Template.py__ __-Case__ __[CaseName1,CaseName2,...]__* will load the results from CaseName1 and CaseName2.  

### Creating a shadowing wall file
*__python__ __MakeShadowingWallFile.py__* will built a .json file out of the geojson files in the same location, given in the *LocalConfig.yml*.  
*__python__ __MakeShadowingWallFile.py__ __-yml__ __path_to_config.yml__* will built a .json file out of the geojson files in the same location, given in the *path_to_config.yml*.  
*__python__ __MakeShadowingWallFile.py__ __-geojson__ __path_to_geojson.geojson__* will built a .json file out of the geojson files in the same location.  
Extra argument can be given to choose shadowing resolution with simple neighborhood, extended neighborhood (higher buildings are considered even if behind others), and all surfaces from all buildings.  
Can be added to the above command line :  *__-ShadeLimits__ __SimpleSurf__* or *__-ShadeLimits__ __AllSurf__* .  The default option is extended with higher buildings considered.  
The more shadowing walls are considered the more warnings can be raised by EnergyPlus.  

### FMU examples
__FMPySimPlayGroundEx1.py__ and __FMPySimPlayGroundEx2.py__: it uses FMPy package and as been successfully tested for controlling temperature's setpoints, internal loads, or watertaps at each time steps of the simulation. For one who'd like to make co-simulation, a deep understanding is still needed on the EP side as inputs and ouputs are to be defined.  
FMU construction are realized if *CreateFMU* is set to True in *LocalConfig.yml*. 
The two examples (Ex1 and Ex2) :  
Ex1 : proposes a simple offset on the temperature setPoints. Every two hours a new building sees its setpoint decreases from 21degC to 18degC. the frequency of changes for each building thus depends on the size of the district that is considered. The internal Loads are also modified depending on working and nonworking hours  
Ex2 : proposes a couple temperature setpoints and water taps controls for each building, keeping the hourly based internal load inputs. It reads an external file to feed the water taps at each time step, and depending on a threshold of water taps' flow, the temperature's setpoints are changed.  
*__python__ __FMPySimPlayGroundEx1.py.py__* will load the fmu and launch simulation from CaseName given in the *LocalConfig.yml*.  
*__python__ __FMPySimPlayGroundEx1.py__ __-yml__ __path_to_config.yml__* will load the fmu and launch simulation from CaseName given in the *path_to_config.yml*.  
*__python__ __FMPySimPlayGroundEx1.py__ __-Case__ __CaseName__* will load the fmu and launch simulation from CaseName.  


## Development and contribution
While the base version of the platform is stable now, it is under further continous development, newcomers are welcome to join by forking and proposing changes. The platform has been developed with passion and is still in progress with passion.  

Hope you'll enjoy it as well :)

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