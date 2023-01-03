# MUBES_UBEM
MUBES_UBEM propose a workflow that creates automatic building energy models for EnergyPlus software.
All inputs are dealt with an external *.yml file.  
Several thermal zoning options are proposed from single heated and non heated zones up to core and perimeter zones for each building floor.
It can launch simulations using parallel computing or can automatically creates FMUs of each building in order to make co-simulation afterward (the co-simulation process, using FMPy, is validated in Windows, Mac and Linux (Ubuntu)).  
The main input file is in a geojson format. It contains the footprint including height (3D vertexes, or 2D vertexes and height as an attribut) of each building's surface as well as some propreties taken from several databases (EPCs, and others).  
__Rq__:  The platform is continually under development, newcomers are welcome to join by forking and proposing changes.  

![Minneberg](Minneberg.jpg)

## Environments
It is a python script based UBEM simulation tool using EnergyPlus (EP) as the core engine.
It has been developed in Python 3.7 with EP 9.1 on Windows and has been successfully tested with EP 9.4 and python 3.9. on Windows and python 3.8 on Ubuntu 20.04 (tested on Oracle Virtual Machine) and with python 3.9 and EP 9.5 on OS x 11.5.2.
It is based on 2 main packages: [EPPY](https://github.com/santoshphilip/eppy) and [GeomEppy](https://github.com/jamiebull1/geomeppy).

## Installation process
The needed packages are given in the requirements.txt file : *__pip__ __install__ __-r__ __requirements.txt__*  
__Note__ : GeomEppy packages uses a specific branch made from the original package.  
The FMUs creation option uses the [EnergyPlusToFMU-v3.1.0](https://simulationresearch.lbl.gov/fmu/EnergyPlus/export/userGuide/download.html) toolkit developed by LNBL. This toolkit should be downloaded and installed at the same level as MUBES_UBEM under a folder named __FMUsKit__ (see BuildFMUs.buildEplusFMU() in the CoreFile folder).  
The portability of FMUs (used on another computer than the one used to generate them) is valid but currently only when no external files are used as error are encountered when relative paths are defined.  
/!\ On Windows 10, some time delay had to be introduced in the original FMU toolkit code to enable to remove the intermediate files and make the FMU reach its end properly (https://github.com/lbl-srg/EnergyPlusToFMU/issues/54).  
  
## Folder organization
The MUBES_UBEM main folder contains several subfolders:  
__bin__  : contains all the core python scripts organized in different field of concern. The main running function is mubes_run.py.  
__default__  : contains the default *.yml configuration files. the env.default can be copied paste and renamed env.yml to change the pathways according to the current computer. It also contains the times series of cold water input temperature for the Domestic Hot Water needs as well as the water taps in l/min. The latter is an output from an other packages ([StROBe](https://github.com/open-ideas/StROBe)) that enables to create stochastics outputs for residential occupancy.    
__examples__ : contains contains several examples that can be first ran in order to get a global insight of what the plateform can do. Just launch the following command line : python.exe ~\bin\mubes_run.py ~\examples\Ex-***. It uses the data given in the ~\examples\minneberg folder)  


## Run simulation case
__First__ __thing__ : Change the path to EnergyPlus and (if needed) to the Data (geojson files) in the env.yml file (created from env.default.yml).  

*__python__ __mubes_run.py__* will launch the simulation using the *DefaultConfig.yml* file is in __default\config__.    
*__python__ __mubes_run.py__ __-yml__ __path_to_config.yml__* will launch the simulation using the information given in the path_to_config.yml. The latter can contain only the changes wanted from the DefaultConfig.yml.  
*__python__ __mubes_run.py__ __-CONFIG__ __{JSON Format}__* will launch the simulation using the information given in the {JSON Format} as arguments. The latter can contain only the changes wanted from the DefaultConfig.yml.  

Examples are given in the __examples__ folder, just launch each example using the wording above with the path to each yml example file.  

__Note__ : *ConfigFile.yml* are systematically saved in the result folder and can thus be used afterward with the *-yml* argument

__Outputs_Template.txt__  in __bin\outputs__ : This file proposes a list of available outputs from EP. It has been build from a .rdd file from EP. The required outputs should be indicated in this file. It also indicates at which frequency the modeler wants his outputs.  

## Creating a shadowing wall file
*__python__ __MakeShadowingWallFile.py__* will built a .json file out of the geojson files in the same location, given in the *Config.yml*.  
*__python__ __MakeShadowingWallFile.py__ __-yml__ __path_to_config.yml__* will built a .json file out of the geojson files in the same location, given in the *path_to_config.yml*.  
*__python__ __MakeShadowingWallFile.py__ __-geojson__ __path_to_geojson.geojson__* will built a .json file out of the geojson files in the same location.  
Extra argument can be given to choose shadowing resolution with simple neighborhood, extended neighborhood (higher buildings are considered even if behind others), and all surfaces from all buildings.  
Can be added to the above command line :  *__-ShadeLimits__ __SimpleSurf__* or *__-ShadeLimits__ __AllSurf__* .  The default option is extended with higher buildings considered.  
The more shadowing walls are considered the more warnings can be raised by EnergyPlus afterward.  

## FMU examples
__FMPySimPlayGroundEx1.py__ and __FMPySimPlayGroundEx2.py__: it uses FMPy package and as been successfully tested for controlling temperature's setpoints, internal loads, or watertaps at each time steps of the simulation. For one who'd like to make co-simulation, a deep understanding is still needed on the EP side as inputs and ouputs are to be defined.  
FMU construction are realized if *CreateFMU* is set to True in *LocalConfig.yml*. 
The two examples (Ex1 and Ex2) :  
Ex1 : proposes a simple offset on the temperature setPoints. Every two hours a new building sees its setpoint decreases from 21degC to 18degC. the frequency of changes for each building thus depends on the size of the district that is considered. The internal Loads are also modified depending on working and nonworking hours  
Ex2 : proposes a couple temperature setpoints and water taps controls for each building, keeping the hourly based internal load inputs. It reads an external file to feed the water taps at each time step, and depending on a threshold of water taps' flow, the temperature's setpoints are changed.  
*__python__ __FMPySimPlayGroundEx1.py.py__* will load the fmu and launch simulation from CaseName given in the *LocalConfig.yml*.  
*__python__ __FMPySimPlayGroundEx1.py__ __-yml__ __path_to_config.yml__* will load the fmu and launch simulation from CaseName given in the *path_to_config.yml*.  
*__python__ __FMPySimPlayGroundEx1.py__ __-Case__ __CaseName__* will load the fmu and launch simulation from CaseName.  
  

## Engine structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation's parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all elements needed at the zone level),
- output level (deals with outpouts variables and frequency).

## Credits
This work is developed within KTH/SEED/RIE/Urban Team, funded by MUBES' project.  
It has been developed with passion and is still in progress with passion.  
Hope you'll enjoy :)

## Citation
Faure, X.; Johansson, T.; Pasichnyi, O. The Impact of Detail, Shadowing and Thermal Zoning Levels on Urban Building Energy Modelling (UBEM) on a District Scale. Energies 2022, 15, 1525. https://doi.org/10.3390/en15041525

