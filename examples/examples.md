# Examples

## Running a simulation case
__First__ __thing__ : Change the path to EnergyPlus and (if needed) to the Data (geojson files).  
Simply change the path in the *LocalConfig_Template.yml* file in __ModelerFolder__ and give it another name (for further updates).  
(Note: see *CoreFile/DefaultConfig.yml* to see all possible changes in  *xxx.yml* files).  

*__python__ __runMUBES.py__* will launch the simulation using the *DefaultConfig.yml* modified by *LocalConfig.yml* file is in __ModelerFolder__.   
*__python__ __runMUBES.py__ __-yml__ __path_to_config.yml__* will launch the simulation using the information given in the path_to_config.yml. The latter can contain only the changes wanted from the DefaultConfig.yml.  
*__python__ __runMUBES.py__ __-CONFIG__ __{JSON Format}__* will launch the simulation using the information given in the {JSON Format} as arguments. The latter can contain only the changes wanted from the DefaultConfig.yml.  

__Note__ : *ConfigFile.yml* are systematically saved in the result folder and can thus be used afterward with the *-yml* argument

__Outputs_Template.txt__ : This file proposes a list of available outputs from EP. It has been build from a .rdd file from EP. The required outputs should be indicated in this file. It also indicates at which frequency the modeler wants his outputs.

## Reading the outputs  
The __ReadResults__ folder contains also a template for post-processing the results :  
*ReadOutputs_Template.py* proposes a basic post-processing stage including reading the data, ploting the areas of footprint and the energy needs as well as some times series for specific building number. Its works for simulation done with or without FMUs.  
*Utilities.py* contains several useful functions for the post-processing stage. The *getData()* is highly helpful. It gathers all the pickle files present in a directory into one dictionnary. It can deal with several CaseNames and overplots results for same Building's Ids by simply appending the path's list.   
*__python__ __ReadOutputs_Template.py__* will load the results from CaseName given in the *LocalConfig.yml*.  
*__python__ __ReadOutputs_Template.py__ __-yml__ __path_to_config.yml__* will load the results from CaseName given in the *path_to_config.yml*.  
*__python__ __ReadOutputs_Template.py__ __-Case__ __[CaseName1,CaseName2,...]__* will load the results from CaseName1 and CaseName2.  

## Creating a shadowing wall file
*__python__ __MakeShadowingWallFile.py__* will built a .json file out of the geojson files in the same location, given in the *LocalConfig.yml*.  
*__python__ __MakeShadowingWallFile.py__ __-yml__ __path_to_config.yml__* will built a .json file out of the geojson files in the same location, given in the *path_to_config.yml*.  
*__python__ __MakeShadowingWallFile.py__ __-geojson__ __path_to_geojson.geojson__* will built a .json file out of the geojson files in the same location.  
Extra argument can be given to choose shadowing resolution with simple neighborhood, extended neighborhood (higher buildings are considered even if behind others), and all surfaces from all buildings.  
Can be added to the above command line :  *__-ShadeLimits__ __SimpleSurf__* or *__-ShadeLimits__ __AllSurf__* .  The default option is extended with higher buildings considered.  
The more shadowing walls are considered the more warnings can be raised by EnergyPlus.  

## FMU examples
__FMPySimPlayGroundEx1.py__ and __FMPySimPlayGroundEx2.py__: it uses FMPy package and as been successfully tested for controlling temperature's setpoints, internal loads, or watertaps at each time steps of the simulation. For one who'd like to make co-simulation, a deep understanding is still needed on the EP side as inputs and ouputs are to be defined.  
FMU construction are realized if *CreateFMU* is set to True in *LocalConfig.yml*. 
The two examples (Ex1 and Ex2) :  
Ex1 : proposes a simple offset on the temperature setPoints. Every two hours a new building sees its setpoint decreases from 21degC to 18degC. the frequency of changes for each building thus depends on the size of the district that is considered. The internal Loads are also modified depending on working and nonworking hours  
Ex2 : proposes a couple temperature setpoints and water taps controls for each building, keeping the hourly based internal load inputs. It reads an external file to feed the water taps at each time step, and depending on a threshold of water taps' flow, the temperature's setpoints are changed.  
*__python__ __FMPySimPlayGroundEx1.py.py__* will load the fmu and launch simulation from CaseName given in the *LocalConfig.yml*.  
*__python__ __FMPySimPlayGroundEx1.py__ __-yml__ __path_to_config.yml__* will load the fmu and launch simulation from CaseName given in the *path_to_config.yml*.  
*__python__ __FMPySimPlayGroundEx1.py__ __-Case__ __CaseName__* will load the fmu and launch simulation from CaseName.  
