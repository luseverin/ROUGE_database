#hazard subtypes directly taken from EMDAT
hazard_all_subtype_emdat = """["drought", "wildfire", "forest fire", "land fire", "ground movement", "tsunami", "avalanche", "landslide", "rockfall", "sudden subsidence", "mudslide", "ash fall", "lava flow", "pyroclastic flow", "lahar", "coastal flood", "flash flood", "riverine flood", "ice jam flood", "rogue wave", "seiche", "coldwave", "heatwave", "severe winter conditions", "derecho", "hail", "lightning", "winterstorm", "storm surge", "tornado", "extra-tropical storm", "tropical storm" ]"""

#dict to match emdat maintypes to there subtypes
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
  'tropical storm']}

#impact types dict
impact_types_dict = {
    "infrastructures": ["roads", "healthcare", "hospitals", "schools", "powerplants", "bridges"],
    "population" : ["displaced", "affected", "deaths", "injured"]

}
impact_cat_list = ["Human Impacts","Transportation Infrastructure",
                   "Healthcare Infrastructure","IT and Communication Infrastructure",
                   "Residential Buildings","Informal Settlements","Education Infrastructure"]

#Countries
import pycountry
import re
unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern_country = '|'.join(map(re.escape, unique_country_names))
