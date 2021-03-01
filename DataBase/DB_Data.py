SimuData = \
 {  'Begin_Day_of_Month' : 1,
    'Begin_Month' : 1,
    'End_Day_of_Month' : 31,
    'End_Month' : 12,
    'SaveLogFiles' : False, #computing folder is not removed thus all energyplus outpus files are preserved
    'FloorZoningLevel' : True,  #1 zone per floor, if False --> 1 zone per building bloc
 }

WeatherFile = \
 {'Loc' : "SWE_Stockholm.Arlanda.024600_IWEC"
  }

#Thisdict gives all the materials characteristics.
# There are 2 layer maximum, the word Inertia and Insulation or key factor further in the code. If one layer is wanted, just comment the other one.
#the basement is considered not heated and thus never insulated layer
BaseMaterial = \
 {'Window' : {'UFactor' :  1.9,
            'Solar_Heat_Gain_Coefficient' : 0.7,
            'Visible_Transmittance' : 0.8,
            },
'Wall Inertia' : {'Thickness' : 0.2,                   #this layer will be considered also for the basement walls
                  'Conductivity' : 0.9,
                'Roughness' : "Rough",
                'Density' : 2300,
                'Specific_Heat' : 1000,
                },
'Wall Insulation' : {'Thickness' : 0.2,
            'Conductivity' : 0.03,
            'Roughness' : "Rough",
            'Density' : 150,
            'Specific_Heat' : 1000,
            },
'Basement Floor' : {'Thickness' : 0.1,     #this layer will be considered also for the basement floor
            'Conductivity' : 0.9,
            'Roughness' : "Rough",
            'Density' : 2300,
            'Specific_Heat' : 1000,
            },
# 'Basement Floor Insulation' : {'Thickness' : 0.05,    #not needed as even without basement the Heated1rstFloor is taken for the first floor
#             'Conductivity' : 0.25*0.1,
#             'Roughness' : "Rough",
#             'Density' : 1000,
#             'Specific_Heat' : 1000,
#             },
# 'Roof Inertia' : {'Thickness' : 0.05,
#             'Conductivity' : 0.15*0.1,
#             'Roughness' : "Rough",
#             'Density' : 1000,
#             'Specific_Heat' : 1000,
#             },
'Roof Insulation' : {'Thickness' : 0.3,
            'Conductivity' : 0.03,
            'Roughness' : "Rough",
            'Density' : 150,
            'Specific_Heat' : 1000,
            },
'Heated1rstFloor Inertia' : {'Thickness' : 0.1,
            'Conductivity' : 0.9,
            'Roughness' : "Rough",
            'Density' : 2300,
            'Specific_Heat' : 1000,
            },
'Heated1rstFloor Insulation' : {'Thickness' : 0.15,
            'Conductivity' : 0.035,
            'Roughness' : "Rough",
            'Density' : 150,
            'Specific_Heat' : 1000,
            },
  }

#this dict is for specification of internalMass equivalence.
#the material should represent the overwhole mean material of all partition and furnitures
#the weight par zone area gives the quentity and the Average thickness enable to compute the surface for heat transfer
#the mass gives a volume thanks to the density that gives a surface thanks to the average thickness
InternalMass = \
 {'HeatedZoneIntMass' : {
        'Thickness' : 0.1, #m this will define the surface in contact with the zone
        'Conductivity' : 0.3,
        'Roughness' : "Rough",
        'Density' : 600,
        'Specific_Heat' : 1400,
        'WeightperZoneArea' : 40, #kg/m2
    },
'NonHeatedZoneIntMass' : {
        'Thickness' : 0.1, #m this will define the surface in contact with the zone
        'Conductivity' : 0.3,
        'Roughness' : "Rough",
        'Density' : 600,
        'Specific_Heat' : 1400,
        'WeightperZoneArea' : 40, #kg/m2
    },
  }


#this dict is for the shading paradigm. There are two files that we need. the firt one is the main geojson that contains all buildings and their propreties
#the other one contains for each shading surface id the vertex point and the building Id in order to catch the height of it.
#to externalize as much as possible, these elements are reported in the dict below
GeomElement = \
 {'BuildIDKey' : ['50A_UUID', 'FormularId'],
  'ShadingIdKey' : 'vaggid',
  'BuildingIdKey' : 'byggnadsid',
  'VertexKey':'geometries',
  'MaxShadingDist': 300,
  }
#this dict gives information on occupancy times each day. If DCV = True, the airflow will follow the number of person
# and the schedule. if not it will be based only on the extra airflow rate but without schedule (all the time)
#if some separation (ventilation and people) is needed than people heat generation should be converted inteo Electric Load as thus ariflow can be
# related to a schedule, other wise...impossible
BasisElement = \
{'Office_Open': '08:00',
 'Office_Close': '18:00',
 'DemandControlledVentilation' : True,
 'OccupBasedFlowRate': 7,  # l/s/person
 'OccupHeatRate' : 70, #W per person
 'EnvLeak': 0.5,# l/s/m2 at 50Pa
 'BasementAirLeak': 1, #in Air change rate [vol/hour]
 'wwr': 0.3,
 'ExternalInsulation' : False,
 'IntLoadType' : 'winter', #change either by 'Cste', 'winter', or 'summer' for reversed sigmoid or sigmoid this will generate hourly values file in the InputFiles folder
 'IntLoadMultiplier': 1, #this is a multiplier the modeler would like to play with for calibration
 'OffOccRandom' : False,
 'AreaBasedFlowRate' : 0.35, #l/s/m2
 'setTempUpL' : 25,
 'setTempLoL' : 21,
 'ACH_freecool' :4,     #this the the vol/hr of extra ventilation when free cooling is on
 'intT_freecool' : 26,  #internal temperature threshold for free coolong (opening windows with fixed ACH)
 'dT_freeCool': 1,      #Tint-Text to authorize free cooling to be turned on
 }

# definition of person/m2...complytely abritrary, but we still need some vaalues
# these proposales are taken from Marc Nohra report and from personnal suggestions
# to be enhanced !!!!!BBR gives also some
OccupType = \
 {'Residential_key' : 'EgenAtempBostad',      'Residential_Rate': [0.02, 0.02],
  'Hotel_key' : 'EgenAtempHotell',            'Hotel_Rate': [0.01, 0.02],
  'Restaurant_key' : 'EgenAtempRestaurang',   'Restaurant_Rate': [0.01, 0.09],
  'Office_key' : 'EgenAtempKontor',           'Office_Rate': [0.01, 0.09],
  'FoodMarket_key' : 'EgenAtempLivsmedel',    'FoodMarket_Rate': [0.01, 0.09],
  'GoodsMarket_key' : 'EgenAtempButik',       'GoodsMarket_Rate': [0.01, 0.09],
  'Shopping_key' : 'EgenAtempKopcentrum',     'Shopping_Rate': [0.01, 0.09], #'I still wonder what is the difference with goods'
  'Hospital24h_key' : 'EgenAtempVard',        'Hospital24h_Rate': [0.01, 0.09],
  'Hospitalday_key' : 'EgenAtempHotell',      'Hospitalday_Rate': [0.01, 0.09],
  'School_key' : 'EgenAtempSkolor',           'School_Rate': [0.01, 0.1],
  'IndoorSports_key' : 'EgenAtempBad',        'IndoorSports_Rate': [0.01, 0.1],
  'Other_key' : 'EgenAtempOvrig',             'Other_Rate': [0.01, 0.1],
  'AssmbPlace_key' : 'EgenAtempTeater',       'AssmbPlace_Rate': [0.01, 0.2],
  # 'OccupRate': OccupRate,
   }

#this dict deals with the ventilation systems
VentSyst = \
 {'BalX' : 'VentTypFTX',
  'Exh' : 'VentTypF',
  'Bal' : 'VentTypFT',
  'Nat' : 'VentTypSjalvdrag',
  'ExhX' : 'VentTypFmed',
 }


#this dict defines the acceptable limits for the element precised as well as the swedish key for the DataBase
DBLimits = \
{'surface_key': 'EgenAtemp',                   'surface_lim':      [0, 10000],
 'nbfloor_key': 'EgenAntalPlan',               'nbfloor_lim':      [0, 100],
 'nbBasefloor_key': 'EgenAntalKallarplan',     'nbBasefloor_lim':  [0, 4],
 'year_key': 'EgenNybyggAr',                   'year_lim':         [0, 2022],
 'nbAppartments_key': 'EgenAntalBolgh',        'nbAppartments_lim':[0, 100],
 'height_key': 'height',                       'height_lim':       [0, 100],
 'AreaBasedFlowRate_key': 'EgenProjVentFlode', 'AreaBasedFlowRate_lim':     [0.35, 10],
 'nbStairwell_key': 'EgenAntalTrapphus',       'nbStairwell_lim': [0, 100],
 }

#this dict defines the EPC measured key word
EPCMeters = \
 {'Heating':
   {'OilHeating_key' : 'EgiOljaUPPV',               'OilHeatingCOP' : 0.85,
    'GasHeating_key' : 'EgiGasUPPV',                'GasHeatingCOP' : 0.9,
    'WoodHeating_key' : 'EgiVedUPPV',               'WoodHeatingCOP' : 0.75,
    'PelletHeating_key' : 'EgiFlisUPPV',            'PelletHeatingCOP' : 0.75,
    'BioFuelHeating_key' : 'EgiOvrBiobransleUPPV',  'BioFuelHeatingCOP' : 0.75,
    'ElecWHeating_key' : 'EgiElVattenUPPV',         'ElecWHeatingCOP' : 1,
    'ElecHeating_key' : 'EgiElDirektUPPV',          'ElecHeatingCOP' : 1,
    'GSHPHeating_key' : 'EgiPumpMarkUPPV',          'GSHPHeatingCOP' : 3,
    'EASHPHeating_key' : 'EgiPumpFranluftUPPV',     'EASHPHeatingCOP' : 2,
    'AASHPHeating_key' : 'EgiPumpLuftLuftUPPV',     'AASHPHeatingCOP' : 2.5,
    'AWSHPHeating_key' : 'EgiPumpLuftVattenUPPV',   'AWSHPHeatingCOP' : 3,
   },
  'DHW' :
   {'OilHeating_key' : 'EgiOljaVV',                 'OilHeatingCOP' : 0.85,
    'GasHeating_key' : 'EgiGasVV',                  'GasHeatingCOP' : 0.9,
    'WoodHeating_key' : 'EgiVedVV',                 'WoodHeatingCOP' : 0.75,
    'PelletHeating_key' : 'EgiFlisVV',              'PelletHeatingCOP' : 0.75,
    'BioFuelHeating_key' : 'EgiOvrBiobransleVV',    'BioFuelHeatingCOP' : 0.75,
    'ElecHeating_key' : 'EgiElVV',                  'ElecHeatingCOP' : 1,
   },
  'Cooling':
   {'DistCooling_key': 'EgiFjarrkyla',              'DistCoolingCOP' : 1,
    'ElecCooling_key' : 'EgiKomfort',               'ElecCoolingCOP' : 1,  #should be HP no?!
    },
  'ElecLoad':
   {'BuildingLev_key' : 'EgiFastighet',             'BuildingLevCOP' : 1,
    'HousholdLev_key' : 'EgiHushall',               'HousholdLevCOP' : 1,
    'OperationLev_key' : 'EgiVerksamhet',           'OperationLevCOP' : 1,
    },
  'NRJandClass':
   {'WeatherCorrectedNRJ_key': 'EgiEnergianvandning',     'WeatherCorrectedNRJCOP' : 1,
    'WeatherCorrectedPNRJ_key': 'EgiPrimarenergianvandning',     'WeatherCorrectedPNRJCOP' : 1,
    'EnClasseVersion_key' : 'EgiVersion',     'EnClasseVersionCOP' : 1,
    'NRJ_Class_key' : 'EgiEnergiklass',     'NRJ_ClassCOP' : 1,
   }
 }