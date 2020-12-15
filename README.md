# MUBES_UBEM
Python Script based UBEM simulation tool using EnergyPlus as the core engine.
It as been developped in python 3.7 with EP9.1 and has been successfully tried with EP9.4.
It is based on 2 main packages : EPPY (https://github.com/santoshphilip/eppy) and GEOMEPPY ( https://github.com/jamiebull1/geomeppy).

Installation process :
EPPY can be installed directly from pip (eppy 0.5.53) see requirement file.
GeomEppy needs to be taken from https://github.com/xavfa/geomeppy as many changes have be done in order to comply with more complex building footprints.
Besides, other changes might be also needed as MUBES_UBEM is just at the beginning of its development.

Path for the data base geojson files (buildings and walls) are currently written in hard. These are not part of the suite.
The file LaunchDataBase.py is the master file that organizes everything.

The paradigm rely on different level : simulation level (deals with simulation parameters), building level (deals with geometry, envelope and material),
the zone level (deals with internal loads, HVAC and all element needed at the zone level) and then the output levels (deals with outpouts variables and frequency).
