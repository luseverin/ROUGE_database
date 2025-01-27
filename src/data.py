##paths and variables
DATA_PATH = '../Data_backup/'
DATA_IN_PATH = '../Data_backup/report_jsons/'
DATA_OUT_PATH = '../Data_backup/results_llm/'

#hazard subtypes directly taken from EMDAT
hazard_all_subtype_emdat = """["drought", "forest fire", "land fire", "ground movement", "tsunami", "avalanche", "landslide", "rockfall", "sudden subsidence", "mudslide", "ash fall", "lava flow", "pyroclastic flow", "lahar", "coastal flood", "flash flood", "riverine flood", "ice jam flood", "rogue wave", "seiche", "coldwave", "heatwave", "severe winter conditions", "derecho", "hail", "lightning/thunderstorm", "sand/dust storm", "winter storm/blizzard", "storm surge", "tornado", "extra-tropical storm", "tropical cyclone" ]"""

#dict to match emdat maintypes to there subtypes
global maintype_to_subytpe_emdat
maintype_to_subytpe_emdat = {'Drought': ['drought'],
 'Wildfire': ['wildfire', 'forest fire', 'land fire'],
 'Earthquake': ['ground movement', 'tsunami'],
 'Mass movement': ['avalanche',
  'landslide',
  'rockfall',
  'sudden subsidence',
  'mudslide'],
 'Volcanic activity': ['ash fall', 'lava flow', 'pyroclastic flow', 'lahar'],
 'Flood': ['\\b(coastal flood',
  'flash flood',
  'riverine flood',
  'ice jam flood)\\b'],
 'Wave action': ['rogue wave', 'seiche'],
 'Extreme temperature': ['coldwave', 'heatwave', 'severe winter conditions'],
 'Storm': ['derecho',
  'hail',
  'lightning',
  'winterstorm',
  'storm surge',
  'tornado',
  'winter storm',
  'extra-tropical storm',
  'tropical storm',
  'typhoon',
  'hurricane']}

global example_location
example_location =     """ {"hazardLocation": [
    {
      "country": "Brazil",
      "region": "",
      "state": "Ceará",
      "city": "Fortaleza, Bela Cruz",
      "locationAnnotation": ""
     },
    {
      "country": "United States",
      "region": "",
      "state": "California, Arizona",
      "city": "",
      "locationAnnotation": ""
     },
     {
      "country": "Colombia",
      "region": "",
      "state": "",
      "city": "",
      "locationAnnotation": ""
     }
     ]
     }
    """
global example_date
example_date =     """{"hazardDate": [
    {
      "startYear": "2017",
      "startMonth": "8",
      "startDay": "30",
      "endYear": "2017",
      "endMonth": "9",
      "endDay": "13",
      "hazardName": "Hurricane Irma"
     },
     {
      "startYear": "2017",
      "startMonth": "9",
      "startDay": "16",
      "endYear": "2017",
      "endMonth": "9",
      "endDay": "30",
      "hazardName": "Hurricane Maria"
     }
     ]
     }
    """
global example_subtypes
example_subtypes = """{"hazardSubtypes": [
    [
     "tornado",
     "lightning",
     "hail"
    ]
    ]
    }"""

global example_impacts
example_impacts = """{"impactSubtypes": [
    {
     "Population" : "[affected, displaced]"
     "Infrastructures" : "[roads, bridges]",
     "impactsAnnotation :""
     }
    ]
    }"""
