#this dict gives the U value for each type of walls\facade element
#only one type of element is possible now. if several we should check for boundary layer conditions and the necesseary
# reversed contruction
BaseMaterial = \
{'Wall': 0.21,
 'Basement Floor': 0.25,
 'Roof': 0.15,
 'Window': 1.9,
 'Heated2NonHeated': 0.05,
  }
#this dict is for the shading paradigm. There are two files that we need. the firt one if the main geojson that contains all buildings and their propreties
#the other one contains for each shading surface id the vertex point and the building Id in order to catch the height of it.
#to externalize as much as possible, these elements are reported in the dict below
GeomElement = \
 {'ShadingIdKey' : 'vaggid',
  'BuildingIdKey' : 'byggnadsid',
  'VertexKey':'geometries',
  'MaxShadingDist': 300,
  }
#this dict gives information on occupancy times each day. If DCV = True, the airflow will follow the number of person
# and the schedule. if not it will be based only on the extra airflow rate but without schedule (all the time)
#if some separation (ventilation and people) is needed than people heat generation should be converted inteo Electric Load as thus ariflow can be
# related to a schedule, other wise...impossible
BasisElement = \
{'Office_Open': '08:00',                   'Office_Close': '18:00',
 'DemandControlledVentilation' : True,
 'OccupBasedFlowRate': 7,  # l/s/person
 'EnvLeak': 0.8,# l/s/m2 at 50Pa
 'WindowWallRatio': 0.15,
 'OffOccRandom' : True
 }

# definition of person/m2...complytely abritrary, but we still need some vaalues
# these proposales are taken from Marc Nohra report and from personnal suggestions
# to be enhanced !!!!!BBR gives also some
OccupRate = \
 {'Residential': 0.02,'Hotel': 0.02, 'Restaurant': 0.09,
  'Office': 0.09, 'FoodMarket': 0.09,'GoodsMarket': 0.09,
  'Shopping': 0.09, 'Hospital24h': 0.09, 'Hospitalday': 0.09,
  'School': 0.1, 'IndoorSports': 0.1,'AssmbPlace': 0.2,
  'Other': 0.1,
  # 'OccupRate': OccupRate,
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


