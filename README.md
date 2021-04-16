# MUBES_UBEM
MUBES_UBEM propose a workflow that creates automatic building energy model for EnergyPlus software.
Several thermal zoning options are proposed from single heated and non heated zones up to core and perimeter zones in for each building floor.
It can launch simulations using parallele computing or can automatically creates FMUs of each building in order to make Co-Simulation afterward.
The main input file is in a geojson format. It contains the footprint including height of each building surfaces as well as some propreties taken from several databases (EPCs, and others)

## Environments
it is a python script based UBEM simulation tool using EnergyPlus (EP) as the core engine.
It has been developed in Python 3.7 with EP 9.1 and has been successfully tested with EP 9.4.
It is based on 2 main packages: [EPPY](https://github.com/santoshphilip/eppy) and [GeomEppy](https://github.com/jamiebull1/geomeppy).

## Installation process
EPPY can be installed directly from pip (eppy 0.5.53), see the requirements.txt file.
GeomEppy needs to be taken from https://github.com/xavfa/geomeppy and make sure it is pointing on the correct branch (MultiFloor_complexe_Building) as many changes have be done in order to comply with more complex building footprints.
Besides, other changes might be also needed as MUBES_UBEM is just at the beginning of its development.

## Folder organization
The MUBES_UBEM main folder contains several subfolder:
CoreFile folder: contains all the core python scripts for the severals levels of the building design process.
ExternalFiles Folder : contains commun external files that one would use for all the buildings considered in the process. It currently contains the times series of input cold water temperature for the Domestic Hot Water needs as well as the water tps in l/min. The latter is an output of an other packages (StROBe) that enables to create stochastics ouputs for residential occupancy. The file present is a sum of 40 apartements simulated with StROBe package.
BuildObject Folder : contains the building class object as well as the defaults choice for missing inputs. The latter might be modified by the modeler depending on its studied cases.
ModelerFolder : contains severals templates to build the process, select the required ouputs, and paths for the process to be launched.

## Run simulation case
The ModelerFolder is the playground of the Modeler. Within this folder, severals templates are proposed. These are to be copy\paste in order to enable modification from the templates without altering your local environements.
the templates are :
Pathways_Template.txt : This file gives the paths to your local path of energyplus and to the needed geojson intputs files (one file for the buildings and one file for the shadins walls of the surrounding environement of each building). Its name is given as parameter in the builder file(see below).
Outputs_Template.txt : This file proposes a list of available outputs from EP. It should be named Outputs.txt. It has been build from a .rdd file from EP. The required outputs should be indicated in this file. It also indicate at which frequency the modeler wants his ouputs.
CaseBuilder_Template.py : this is the main builder file. This templates gives an example for a full process to be launched (having a input goejson file though !). ReadCarefuly the comments below the if __name__ == '__main__' : as important choices are to be done here by the modeler before launching a simulation.
This file deals with the construction of the .idf file for each building and either launches the parallele computing option for all or create the FMUs of all buildings. It will automatically create a folder (at the same level of main MUBES_UBEM folder) that will be called SimResults and that will have subfolder for each case that is launched. The subfolder will be named as the CaseName in the CaseBuilder scripts (see comments below the if __name__ == '__main__' : ).
ReadOutputs_Template.py : this script propose a basic post-treatment stage including reading the data, ploting the areas of footprint and the related energy as well as some times series for specific building number.
Some few other file are present in this folder :
Utilities.py :contains several function useful for the post-treatement stage. The getData mainly is helpful, it gathered all the pickle file present in a directory.
PlotBuilder.py : enable to make 3D Matplotlib figures out of the idf files. It will plot all the buildings that are considered or each building appart depending on the option.
Example of plots from Minneberg District, Stockholm, Sweden
![Minneberg](Minneberg.png)

## Engine structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all element needed at the zone level), and then 
- output levels (deals with outpouts variables and frequency).

## Credits
This work is develped within KTH/SEED/RIE/Urban Team, funded by MUBES' project.

