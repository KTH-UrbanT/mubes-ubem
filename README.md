# MUBES_UBEM
Python Script based UBEM simulation tool using EnergyPlus (EP) as the core engine.
It has been developed in Python 3.7 with EP 9.1 and has been successfully tested with EP 9.4.
It is based on 2 main packages: [EPPY](https://github.com/santoshphilip/eppy) and [GeomEppy](https://github.com/jamiebull1/geomeppy).

## Installation process
EPPY can be installed directly from pip (eppy 0.5.53), see the requirements.txt file.
GeomEppy needs to be taken from https://github.com/xavfa/geomeppy as many changes have be done in order to comply with more complex building footprints.
Besides, other changes might be also needed as MUBES_UBEM is just at the beginning of its development.

## Run simulation case
the file CaseBuilder.py handles the input file creation and launches the simulation in multicore mode. The % of CPU capacity can be modified in the script.
The if __name__ == '__main__' (in CaseBuilder.py) gives an example with pathes to geojson files written in hard. These are not part of the suite.
It highlights were can be introduced specific changes in the building parameters. The paradigm of input files creation rely on a 'for' loop for the moment. Thus, some object's deepcopy should be introduced if ones wants to make several cases with same geometry for example.
New folders are created during the process :
'CaseFile' contains the inputs file of each case to be simulated. A subfolder 'Sim_Results' will contain pickle files of each simulated run (for each input case file).
During each run, a specific subfoler is created and then removed after its simulation ends.
Thus, at the end of the full process, the 'CaseFile' folder remains with, for each run, the .idf and .pickles files (EnergyPlus input file and the building object with its parameters from the geojson file).
A subfolder 'Sim_Results' contains all the results in .pickle files (but .csv are also possible).

Note : The file LaunchDataBase.py is no more usefull even though it is still present. It will be removed in future updates.


## Engine structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all element needed at the zone level), and then 
- output levels (deals with outpouts variables and frequency).
