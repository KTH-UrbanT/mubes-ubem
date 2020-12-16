# MUBES_UBEM
Python Script based UBEM simulation tool using EnergyPlus (EP) as the core engine.
It has been developed in Python 3.7 with EP 9.1 and has been successfully tested with EP 9.4.
It is based on 2 main packages:
- [EPPY] (https://github.com/santoshphilip/eppy), and
- [GeomEppy] ( https://github.com/jamiebull1/geomeppy).

## Installation process
EPPY can be installed directly from pip (eppy 0.5.53), see the requirements.txt file.
GeomEppy needs to be taken from https://github.com/xavfa/geomeppy as many changes have be done in order to comply with more complex building footprints.
Besides, other changes might be also needed as MUBES_UBEM is just at the beginning of its development.

Path for the data base geojson files (buildings and walls) are currently written in hard. These are not part of the suite.
The file LaunchDataBase.py is the master file that organizes everything.

## Engine structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all element needed at the zone level), and then 
- output levels (deals with outpouts variables and frequency).
