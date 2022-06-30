# Documentation
## Technological stack
MUBES UBEM is a Python script-based simulation tool using EnergyPlus (EP) as the thermal engine.
It has been developed in Python 3.7 with EP 9.1 on Windows and has been successfully tested with EP 9.4 and python 3.9. on Windows and python 3.8 on Ubuntu 20.04 (tested on Oracle Virtual Machine) and with python 3.9 and EP 9.5 on OS x 11.5.2.
It is based on 2 main packages: [EPPY](https://github.com/santoshphilip/eppy) and [GeomEppy](https://github.com/jamiebull1/geomeppy).

__️Note__: GeomEppy package was adjusted for the purpose of MUBES UBEM, hence only its [customized version](https://github.com/xavfa/geomeppy) should be used.

## Inputs
All inputs are dealt with an external *.yml file.  
Several thermal zoning options are proposed from single heated and non-heated zones up to core and perimeter zones for each building floor.
The main input file is in a geojson format. It contains the footprint including height (3D vertexes, or 2D vertexes and height as an attribut) of each building's surface as well as some propreties taken from several databases (EPCs, and others).

## Model structure
The paradigm of simulation engine is to automate simulation on several different levels :
- simulation level (deals with simulation's parameters),
- building level (deals with geometry, envelope and material),
- zone level (deals with internal loads, HVAC and all elements needed at the zone level),
- output level (deals with outpouts variables and frequency).

## Folder organization
The MUBES_UBEM main folder contains several subfolders:  
__bin__  : contains all the core python scripts for the several levels of the building design process.

__bin/building-geometry__ : contains the building class object, filters to skip building from the input file and some geometric utilities used.

__bin/output__ : contains one template to read the results and some functions for post-processing in the output-utilities.py file.  

__default__  : contains common external files that one would use for all the buildings considered in the process. It currently contains the times series of cold water input temperature for the Domestic Hot Water needs as well as the water taps in l/min. The latter is an output from an other packages ([StROBe](https://github.com/open-ideas/StROBe)) that enables to create stochastics outputs for residential occupancy.

__examples__ : contains the *mubes-run.py* file as well as two examples of FMU simulations. An example of GeoJSON is also provided. *MakeShadowingWallFile.py* enables to create a JSON input file for further shadowing effect consideration.