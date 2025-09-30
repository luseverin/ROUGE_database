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

#hazard_main_types_emdat_extended = ["Drought", "Wildfire", "Earthquake", "Mass movement",
#                                    "Volcanic activity", "Flood", "Wave action", "Extreme warm temperature",
#                                    "Extreme cold temperature", "Other storm",
#                                    "Tropical storm", "Epidemic", "Conflict"]

hazard_kw_reclass = {
    'Drought': r"\bdrought.*|\bdry\s+spell.*",
    'Wildfire': r"\b(forest\s*fire|wild\s*fire|land\s*fire|bush\s*fire|wildfire|landfire|bushfire|fire)s?\b.*",
    'Earthquake': r"\b(earthquake|ground\s+movement|tsunami)s?\b.*",
    'Mass movement': r"\b(mass\s+movement|avalanche|land\s*slide|landslide|rockfall|sudden\s+subsidence|mudslide|rockslide)s?\b.*",
    'Volcanic activity': r"\b(volcanic|ash\s+fall|lava\s+flow|pyroclastic\s+flow|lahar)s?\b.*",
    'Flood': r"\b(flood|inundation|coastal\s+flood|flash\s+flood|riverine\s+flood|ice\s+jam\s+flood|heavy rain)s?\b.*",
    'Wave action': r"\b(wave|rogue\s+wave|seiche)\b.*",
    'Extreme cold temperature': r"\b(extreme\s+cold\s+temperature|cold\s+wave|coldwave|cold\s+spell|severe\s+winter\s+conditions)s?\b.*",
    'Extreme warm temperature': r"\b(extreme\s+warm\s+temperature|heat\s+wave|heatwave|heat\s+episode|(?:heat|hot)\s+spell|heat\s+stress)s?\b.*",
    'Tropical storm': r"\b(tropical\s+storm|typhoon|hurricane|cyclonic\s+storm)s?\b.*",
    'Convective storm': r"\b(convective\s+storm|derecho|hail|lightning|tornado|superstorm|thunderstorm)s?\b.*",
    'Other storm': r"\b(extra-?tropical\s+storm|winter\s*storm|storm\s+surge|windstorm|snowstorm|blizzard)s?\b.*",
    'Epidemic': r"\b(cholera|dengue|outbreak|epidemic)s?\b.*",
    'Conflict': r"\b(conflict|war|terrorism|unrest)s?\b.*"
}

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

hazard_mapping_emdat = {'Drought': ['Drought'],
                        'Wildfire': ['Wildfire', 'forest fire', "Forest fire", 'land fire', "Land fire", "fire"],
                        'Earthquake': ['Earthquake', "Tsunami"],
                        'Mass movement': ['Mass movement', 'Mass movement (dry)', 'Mass movement (wet)', "Landslide", "Mud flow/slide", "Avalanche",
                                          "Alluvion", "Coastal erosion", "Subsidence", "Erosion", "Sedimentation"],
                        'Volcanic activity': ['Volcanic activity', "Eruption", "Liquefaction", "Lahar"],
                        'Flood': ['Flood', 'Glacial lake outburst flood', "Flash flood", "Riverine flood", "Coastal flood", "Ice jam flood",
                                  "Rain", "Heavy rain", "Heavy rains", "Overflow"],
                        'Wave action': ['rogue wave', 'seiche'],
                        'Extreme temperature': ['Extreme warm temperature', 'Extreme cold temperature', 'Extreme temperature', "Cold wave", "Heat wave",
                                                "Severe winter conditions", "Frost"],
                        'Storm': ['Storm', 'Other storm', 'Tropical storm', 'Convective storm', "Extra-tropical cyclone", "Severe local storm",
                                  "Violent wind", "Lightning", "Hail", "Storm surge", "Storm tides", "Tornado", "Tropical cyclone", "Fog", "Blizzard",
                                  "Windstorm", "Electric storm", "Snowstorm", "Hail storm", "Cyclone", "Surge", "Cond.Atmosph.", "Atmospheric cond.",
                                  "Sandstorm", "Tropical depression", "Atmosphcondition", "Strong wind"]}

emdat_undrr_to_name = {
    # Cold wave
    "nat-met-ext-col": "Cold wave",
    "MH0040": "Cold wave",

    # Drought
    "nat-cli-dro-dro": "Drought",
    "MH0035": "Drought",

    # Earthquake & subtypes
    "nat-geo-ear-gro": "Earthquake",
    "GH0001": "Earthquake",
    "GH0002": "Earthquake",#"Ground shaking",
    "GH0003": "Earthquake",#"Liquefaction",
    "GH0004": "Earthquake",#"Surface rupture",
    "GH0005": "Earthquake",#"Subsidence and uplift",

    # Epidemics
    "nat-bio-epi-vir": "Disease", #"Viral diseases",
    "nat-bio-epi-bac": "Disease",#"Bacterial diseases",
    "nat-bio-epi-par": "Disease",#"Parasitic diseases",
    "nat-bio-epi-fun": "Disease",#"Fungal diseases",
    "nat-bio-epi-pri": "Disease",#"Prion diseases",
    "nat-bio-epi-dis": "Disease",#"General infectious disease",
    "BI0016": "Disease",#"General infectious disease",

    # Extra-tropical cyclone/storm
    "nat-met-sto-ext": "Extra-tropical cyclone",
    "MH0031": "Extra-tropical cyclone",
    "MH0099": "Extra-tropical cyclone",#"Extra-tropical storm",

    # Floods
    "nat-hyd-flo-fla": "Flash flood",
    "MH0006": "Flash flood",
    "nat-hyd-flo-riv": "Riverine flood",
    "MH0007": "Riverine flood",
    "nat-hyd-flo-coa": "Coastal flood",
    "MH0004": "Coastal flood",
    "nat-hyd-flo-flo": "Flood",
    "MH0012": "Flood",#"General flood",
    "MH0008": "Flood",#"Groundwater flood",
    "MH0010": "Flood",#"Ponding flood",
    "MH0011": "Flood",#"Snowmelt flood",
    "nat-hyd-flo-ice": "Ice jam flood",
    "MH0009": "Ice jam flood",
    "nat-cli-glo-glo": "Glacial lake outburst flood",
    "MH0013": "Glacial lake outburst flood",
    "tec-mis-col-col": "Flood",#"Dam/levee break flood",
    "TL0009": "Flood",#"Dam/levee break flood",

    # Heat wave
    "nat-met-ext-hea": "Heat wave",
    "MH0047": "Heat wave",

    # Insect infestations
    "nat-bio-inf-loc": "Infection",#Insect pest / Locust infestation",
    "nat-bio-inf-gra": "Infection",#"Grasshopper infestation",
    "nat-bio-inf-wor": "Infection",#"Worms infestation",
    "nat-bio-inf-inf": "Infection",#"General infestation",
    "BI0002": "Infection",#"General insect infestation",
    "BI0003": "Infection",#"Locust infestation",

    # Landslides
    "nat-geo-mmd-lan": "Landslide",
    "nat-hyd-mmw-lan": "Landslide",
    "GH0007": "Landslide",
    "GH0014": "Landslide",#"Volcanic triggered landslide",

    # Mudflow
    "nat-hyd-mmw-mud": "Mud flow/slide",
    "MH0051": "Mud flow/slide",

    # Severe local storms
    "nat-met-sto-sto": "Severe local storm",
    "MH0003": "Severe local storm",
    "MH0060": "Violent wind",
    "nat-met-sto-lig": "Lightning",
    "MH0002": "Lightning",
    "nat-met-sto-hai": "Hail",
    "MH0036": "Hail",

    # Avalanches
    "nat-geo-mmd-ava": "Avalanche", #"Avalanche (dry)",
    "nat-hyd-mmw-ava": "Avalanche", #"Avalanche (wet)",
    "MH0050": "Avalanche",

    # Storm surge/tides
    "nat-met-sto-sur": "Storm surge",
    "MH0027": "Storm surge",
    "nat-hyd-wav-rog": "Storm tides",
    "MH0028": "Storm tides",

    # Tornado & tropical cyclones
    "nat-met-sto-tor": "Tornado",
    "MH0059": "Tornado",
    "nat-met-sto-tro": "Tropical cyclone",
    "MH0057": "Tropical cyclone",
    "MH0058": "Tropical cyclone",#"Tropical storm",
    "MH0030": "Tropical cyclone",#"Depression or cyclone",
    "MH0032": "Tropical cyclone",#"Sub-tropical cyclone",

    # Tsunami
    "nat-geo-ear-tsu": "Tsunami",
    "MH0029": "Tsunami",#"Tsunami (general)",
    "GH0006": "Tsunami",#"Tsunami (earthquake)",
    "GH0017": "Tsunami",#"Tsunami (volcanic)",
    "GH0035": "Tsunami",#"Tsunami (submarine landslide)",

    # Volcano
    "nat-geo-vol-lav": 'Volcanic activity',#"Lava flows",
    "GH0009": 'Volcanic activity',#"Lava flows / Volcanic activity",
    "nat-geo-vol-ash": 'Volcanic activity',#"Ash/tephra fall",
    "GH0010": 'Volcanic activity',#"Ash/tephra fall",
    "nat-geo-vol-vol": 'Volcanic activity',#"Volcanic activity / Volcanic gases",
    "GH0016": 'Volcanic activity',#"Volcanic gases",
    "nat-geo-vol-pyr": 'Volcanic activity',#"Pyroclastic flow",
    "GH0012": 'Volcanic activity',#"Pyroclastic flow",
    "nat-geo-vol-lah": 'Volcanic activity',#"Lahar",
    "GH0013": 'Volcanic activity',#"Lahar",

    # Wildfires
    "nat-cli-wil-for": "Forest fire",
    "nat-cli-wil-lan": "Land fire",
    "nat-cli-wil-wil": "Wildfire",
    "EN0013": "Wildfire",

    # Conflict
    "Multiple codes": "Conflict",#"Conflict / Civil unrest / Armed conflict",
    "SO0001": "Conflict",#"International armed conflict",
    "SO0002": "Conflict",#"Non-international armed conflict",
    "SO0003": "Conflict",#"Civil unrest",
    "SO0004": "Conflict",#"Explosive remnants of war",
    "SO0005": "Conflict",#"Environmental degradation from conflict",

    # Other
    "nat-met-fog-fog": "Fog",
    "MH0016": "Fog",
    "nat-met-ext-sev": "Severe winter conditions",
    "MH0041": "Severe winter conditions",
    "MH0042": "Severe winter conditions",#"Freeze",
    "MH0043": "Severe winter conditions",#"Frost",
    "MH0044": "Severe winter conditions",#"Freezing rain",
    "MH0045": "Severe winter conditions",#"Glaze",
    "MH0046": "Severe winter conditions",#"Ground frost",
    "MH0048": "Severe winter conditions",#"Icing",
    "MH0049": "Severe winter conditions",#"Thaw",
    "nat-met-sto-bli": "Blizzard",
    "MH0034": "Blizzard",
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

#hazard_subtype_kw_searc ={
#                        'Drought': r"drought.*|dry spell.*",
#                        'Wildfire': r"fire.*|forestfire.*|wildfire.*|landfire.*|bushfire.*|forest fire.*|wild fire.*|land fire.*|bush fire.*" ,
#                        'Earthquake' : r"ground movement.|tsunami.",
#                        'Mass movement': r"avalanche.|land slide.*|landslide.*|rockfall.*|sudden subsidence.|mudslide.|mass movement.*",
#                        'Volcanic activity' : r"ash fall.|lava flow.|pyroclastic flow.|lahar",
#                        'Flood': r"flood.*|inundation.*|coastal flood.|flash flood.|riverine flood.|ice jam flood.",
#                        'Wave action' : r"rogue wave.|seiche",
#                        'Extreme temperature' : r"cold wave.*|coldwave.*|cold spell.*|heat wave.*|heatwave.*|heat episode.*|((heat|hot) spell).*|heat stress.*|severe winter conditions.",
#                        'Storm' : r"derecho.|hail.|lightning.|winterstorm.|storm surge.|tornado.|winter storm.|extra-tropical storm.|tropical storm.|typhoon.|hurricane.|storm.*|superstorm.*|windstorm.*|snowstorm.*|blizzard.*|thunderstorm.*" }
