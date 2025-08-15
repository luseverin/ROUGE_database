#Constants for hazard definition

#hazard subtypes directly taken from EMDAT
hazard_all_subtype_emdat = ["drought", "wildfire", "forest fire", "land fire",
                            "ground movement", "tsunami", "avalanche", "landslide",
                            "rockfall", "sudden subsidence", "mudslide", "ash fall",
                            "lava flow", "pyroclastic flow", "lahar", "coastal flood",
                            "flash flood", "riverine flood", "ice jam flood", "rogue wave",
                            "seiche", "coldwave", "heatwave", "severe winter conditions",
                            "derecho", "hail", "lightning", "winterstorm", "storm surge",
                            "tornado", "extra-tropical storm", "tropical storm" ]

hazard_main_types_emdat_extended = ["Drought", "Wildfire", "Earthquake", "Mass movement",
                                    "Volcanic activity", "Flood", "Wave action", "Extreme warm temperature",
                                    "Extreme cold temperature", "Other storm",
                                    "Tropical storm", "Epidemic", "Conflict"]

hazard_main_types_emdat_desc = {
    "Drought": "Prolonged lack of precipitation",
    "Wildfire": "Uncontrolled natural fires",
    "Earthquake": "Sudden tectonic shifting. Include as well tsunami",
    "Mass movement": "Any type of downslope movement of earth materials. Includes Landslides and rockfalls",
    "Volcanic activity": "Eruptions and related phenomena",
    "Flood": "River, coastal, flash and ice jam flooding",
    "Wave action": "Wind-generated surface waves (e.g. Rogue waves, seiche)",
    "Extreme warm temperature": "Prolonged, abnormally high heat, heatwaves",
    "Extreme cold temperature": "Prolonged, abnormally low cold temperatures, coldwaves",
    "Convective storm": "Convective storms (e.g. tornadoes, thunderstorms, derechos, hailstorms...)",
    "Other storm": "Any type of storm which does not correspond to a tropical cyclone or a convective storm (e.g. extra-tropical storm, snow storm, ...)",
    "Tropical storm": "Tropical cyclonic storms (also includes hurricanes, typhoons)",
    "Epidemic": "Widespread occurrence of an infectious disease in a community",
    "Conflict": "Disagreements or disputes between different groups, organizations, or states"
}

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


