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

hazard_subtype_kw_searc ={
                        'Drought': r"drought.*|dry spell.*",
                        'Wildfire': r"fire.*|forestfire.*|wildfire.*|landfire.*|bushfire.*|forest fire.*|wild fire.*|land fire.*|bush fire.*" ,
                        'Earthquake' : r"ground movement.|tsunami.",
                        'Mass movement': r"avalanche.|land slide.*|landslide.*|rockfall.*|sudden subsidence.|mudslide.|mass movement.*",
                        'Volcanic activity' : r"ash fall.|lava flow.|pyroclastic flow.|lahar",
                        'Flood': r"flood.*|inundation.*|coastal flood.|flash flood.|riverine flood.|ice jam flood.",
                        'Wave action' : r"rogue wave.|seiche",
                        'Extreme temperature' : r"cold wave.*|coldwave.*|cold spell.*|heat wave.*|heatwave.*|heat episode.*|((heat|hot) spell).*|heat stress.*|severe winter conditions.",
                        'Storm' : r"derecho.|hail.|lightning.|winterstorm.|storm surge.|tornado.|winter storm.|extra-tropical storm.|tropical storm.|typhoon.|hurricane.|storm.*|superstorm.*|windstorm.*|snowstorm.*|blizzard.*|thunderstorm.*" }

#impact types dict
impact_types_dict = {
    "infrastructures": ["roads", "healthcare", "hospitals", "schools", "powerplants", "bridges"],
    "population" : ["displaced", "affected", "deaths", "injured"]

}
impact_cat_list = ["Human Impacts","Transportation Infrastructure",
                   "Healthcare Infrastructure","IT and Communication Infrastructure",
                   "Residential Buildings","Informal Settlements","Education Infrastructure"]
impact_cat_desc_dict = {
    "Human impacts": "The impacts on the human population resulting from the event. Look for words such as 'Affected People', 'Injured People', 'Displaced People','Homeless People', 'Missing People', 'Human Deaths'.",
    "Transportation Infrastructure": "The impacts on the transportation infrastructures resulting from the event. Look for words such as 'roads', 'bridges', 'railways', and 'highways'.",
    "Water, Sanitation, and Hygiene Infrastructure": "The impacts on the water, sanitation, and hygiene infrastructure resulting from the event. Look for words such as 'sewage networks', 'drainage systems', 'wastewater treatment plants', etc.",
    "Healthcare Infrastructure": "The impacts on the healthcare infrastructure resulting from the event. Look for words such as 'hospitals', 'healthcare centers', 'pharmacies', 'clinics', etc.",
    "IT and Communication Infrastructure": "The impacts on the IT and communication infrastructure resulting from the event. Look for words such as 'data centers', 'communication towers', 'cables', etc.",
    "Residential Buildings": "The impacts on the residential buildings resulting from the event.",
    "Informal Settlements": "The impacts on informal settlements resulting from the event. Look for words such as 'refugee camps', 'slums', 'tents', etc.",
    "Education Infrastructure": "The impacts on education infrastructure resulting from the event. Look for words such as 'schools', 'universities', etc."
}

#Countries
import pycountry
import re
unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern_country = '|'.join(map(re.escape, unique_country_names))
