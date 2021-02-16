# MUBES_UBEM
Python Script based UBEM simulation tool using EnergyPlus (EP) as the core engine.
It has been developed in Python 3.7 with EP 9.1 and has been successfully tested with EP 9.4.
It is based on 2 main packages: [EPPY](https://github.com/santoshphilip/eppy) and [GeomEppy](https://github.com/jamiebull1/geomeppy).

## Installation process
EPPY can be installed directly from pip (eppy 0.5.53), see the requirements.txt file.
GeomEppy needs to be taken from https://github.com/xavfa/geomeppy and make sure it is pointing on the correct branch (MultiFloor_complexe_Building)
as many changes have be done in order to comply with more complex building footprints.
Besides, other changes might be also needed as MUBES_UBEM is just at the beginning of its development.

## Run simulation case
several templates are proposed. These needs to be copy/paste to your local space, keeping the copy in the ModelerFolder. The local files will thus be your playground
while the templates remain unchanged and enable to be pulled again if major modification were proposed.
The copy of Pathway_Template.txt needs to be named Pathways.txt. as shown in the template it gives the paths to the goejson files as well as
to the energy plus folder.
The copy of Outputs_Template.txt needs to be named Outputs.txt. As written in the file, the wanted ouputs just haev to be marked by double hashtags with space in front of their name.
Both copies of CaseBuilder_Template and ReadOutputs_Template should be renamed as one wishes. the Templates gives example of builder files, simulation runs and post-treatment analyses.

New folders are created during the process inside 'ModelerFolder':
'RunningFolder' contains the inputs file of each case to be simulated. A subfolder 'Sim_Results' will contain pickle files of each simulated run (for each input case file).
During each run, a specific subfoler is created and then removed after its simulation ends.
Thus, at the end of the full process, a new folder remains with, for each run, the .idf and .pickles files (EnergyPlus input file and the building object with its parameters from the geojson file).
A subfolder 'Sim_Results' contains all the results in .pickle files (but .csv are also possible). the name of this new folder is to be specified in the builder (see template)

The simulation process uses multiprocessing package, thus a maximum CPU factor is to be specified in the builder (see template). in the case of 1 single core, the factor should be fixed to 1.

## Engine structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all element needed at the zone level), and then 
- output levels (deals with outpouts variables and frequency).
