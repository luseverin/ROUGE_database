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
                                    "Extreme cold temperature", "Convective Storm", "Extra-tropical storm",
                                    "Tropical storm", "Epidemic"]

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


