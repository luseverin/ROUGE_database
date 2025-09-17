# Define unit conversion mapping
unit_mapping = {
    'km': 'km',
    'km**2': 'km**2',
    'miles': 'km',
    'kg': 'kg',
    'm**3': 'm**3',
    "acre": "km**2",
    "feet": "km",
    "meter": "km",
    "hectare": "km**2",
    "ha": "km**2",
    "mi**2": "km**2",
    "m**2": "km**2",
    "ft**2": "km**2",
    "pound": "kg",
    "ton": "kg",
    "tonne": "kg",
    "liter": "m**3",
    "l": "m**3",
    "gallon": "m**3",
}
std_unit_kw_reclass = {
                    'km' : [r"(?<!\b(squared?)\b)\s\b(kilometers?|kilometres?|kms?)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2)\b)"],
                    'km**2' : [r"\b(?<=(squared?))\s*(kilometers?|kilometres?|kms?)\b",
                            r"\b(kilometers?|kilometres?|kms?)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'm**2' : [r"\b(?<=(squared?)\b)\s*\b(meters?|metres?|m)\b",
                            r"\b(meters?|metres?|m)\s?\b\b(\*\*\s*2|\*\*2|\^2|²|square|squared|2)\b(?<!\.\d)"],
                    'mi**2' : [r"\b(?<=(squared?))\s*(mile|miles|mi)\b",
                            r"\b(mile|miles|mi)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'ft**2' : [r"\b(?<=(squared?))\s*(feet|foot|ft)\b",
                            r"\b(feet|foot|ft)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'kg' : [r"\b(kgs?|kilograms?)\b"],
                    'm**3' : [r"\b(?<=(cube|cubic))\s*(meters?|metres?|m)\b",
                            r"\b(meters?|metres?|m)s?\s?(\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)\b(?<!\.\d)"],
                    "acre": [r"\b(acres?)\b"],
                    "feet": [r"(?<!\b(squared?|cube|cubic)\s*)\b(feet|foot|ft)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3))\b(?!\s+\d+(\.\d+)?)"],
                    "hectare": [r"\b(hectares?|ha|hectors?)\b"],
                    "ton": [r"\b(?<!\b(metric)\s*)(ton|tons)\b"],
                    "tonne": [r"\b(tonne|tonnes|metric ton|metric tons)\b"],
                    "pound": [r"\b(pounds|lbs?)\b"],
                    "meter": [r"(?<!\b(squared?|cube|cubic)\s*)\b(meters?|metres?|m)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3))\b(?!\s+\d+(\.\d+)?)"],
                    "liter": [r"\b(liters?|litres?|l)\b"],
                    "miles": [r"(?<!\b(squared?|cube|cubic)\s*)\b(miles?|mi)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3))\b(?!\s+\d+(\.\d+)?)"],
                    "gallon": [r"\b(gallons|gal)\b"],
}

#reclassify units
unit_converter = {"families" : (3, "people"),
                  "households": (3, "people"),
                  "village": (1000, "people"),
                  "communities": (100, "people"),
                  }

unit_type_kw_reclass = {
                        'km' : r"\b(kilometer|kilometre|km)s?(?!\s*(\*\*\s*2|\^2|²|square|squared|2))",
                        'km**2' : r"\b(kilometer|kilometre|km)s?\s?(\*\*\s*2|\*\*2|\^2|²|square|squared|2)",
                        'kg' : r"(kg.*|.*kilogram.*)",
                        'm**3' : r"\b(meter|metre|m)s?\s?(\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)",
                        '%' : r"(%|perc.*)",
}
#unit_kw_reclass = {
#                        'people': r"people|persons?|individuals?|residents?|evacuees?",#women.*|men.*|child.*|adult.*|elder.*|infant.*
#                        'roads' : r"road.*|route.*|bridge.*|highway.*|motorway.*",#r"(?<!kilometer|kilometre|km).*(road.*|route.*|.*bridge.*|.*highway.*|.*motorway.*)",
#                        'transportation facilities' : r"rail.*|train track.*|airport.*|\scar.*|railway.*|train.*|buse?s?\b|taxi.*|taxicab.*|truck.*",
#                        'water, sanitation and hygiene facilities' : r"water.*|sanitation.*|hygiene.*|latrine.*|well.*|tap.*|reservoir.*|aqueduct.*",
#                        'healthcare facilities' : r"health|hospitals?\b|clinic.*|maternity.*|medical",
#                        'IT and communication facilities' : r"communication.*|radio.*|tv.*|cell tower.*|antenna.*",
#                        'power and energy production infrastructure facilities' : r"power.*|energy.*|generator.*|wind.*|solar.*|hydro.*|dams?",
#                        'homes' : r"residential.*|residence.|hous.*|home.*|building.*",
#                        'education facilities' : r"education.*|school.*|university.*|college.*",
#                        'crop production and forestry' : r"crop.*|field.*|forest.*|tree.*|banana.*|coffee.*|cocoa.*|cotton.*|maize.*|rice.*|sorghum.*|soybean.*|sugar.*|tobacco.*|wheat.*",
#                        'agricultural facilities' : r"irrigation.*|barn.*|farm.*",
#                        'affected animals' : r"livestock.*|animal.*|fish.*|cow.*|sheep.*|poult.*|cattle.*|goat.*|pig.*|chick.*|horse.*|heads?",
#                        'informal settlements' : r"camp.?|tent.?|refuge.?|settlement.?"
#                         }

unit_kw_reclass = {
    'people': r"\b(people|persons?|individuals?|residents?|evacuees?)\b",

    'roads': r"\b(roads?|routes?|bridges?|highways?|motorways?)\b",

    'transportation facilities': r"\b(rail(way|road)?s?|train tracks?|airports?|cars?|buses?|bus|taxi(cab)?s?|trucks?)\b",

    'water, sanitation and hygiene facilities': r"\b(water|sanitation|hygiene|latrines?|wells?|taps?|reservoirs?|aqueducts?)\b",

    'healthcare facilities': r"\b(health(care)?|hospitals?|clinics?|maternit(y|ies)|medical)\b",

    'IT and communication facilities': r"\b(communication(s)?|radios?|tv|cell towers?|antennas?)\b",

    'power and energy production infrastructure facilities': r"\b(power|energy|generators?|wind|solar|hydro|dams?)\b",

    'homes': r"\b(residential|residences?|houses?|homes?|buildings?)\b",

    'education facilities': r"\b(education(al)?|schools?|universit(y|ies)|colleges?)\b",

    'crop production and forestry': r"\b(crops?|fields?|forests?|trees?|bananas?|coffee|cocoa|cotton|maize|rice|sorghum|soybeans?|sugar|tobacco|wheat)\b",

    'agricultural facilities': r"\b(irrigation|barns?|farms?)\b",

    'affected animals': r"\b(livestock|animals?|fish|cows?|sheep|poultr(y|ies)|cattle|goats?|pigs?|chickens?|horses?|heads?)\b",

    'informal settlements': r"\b(camps?|tents?|refuge(e|es)|settlements?)\b"
}


expected_unit_subtype = {
    "Affected People": "people",
    "Injured People": "people",
    "Displaced People": "people",
    "Homeless People": "people",
    "Missing People": "people",
    "Human Deaths": "people",
    "Residential Buildings": "homes",
    "Informal settlements": "informal settlements",
    "Education Infrastructure": "education facilities",
    "Human Health and Wellbeing" : "unknown",
    "Infected and Ill People": "people",
    "Road Infrastructure" : "roads",
    "Other Transportation Infrastructure" : "transportation facilities",
    "Water, Sanitation, and Hygiene Infrastructure": "water, sanitation and hygiene facilities",
    "Healthcare Infrastructure": "healthcare facilities",
    "IT and Communication Infrastructure": "IT and communication facilities",
    "Power and Energy Production Infrastructure" : "power and energy production infrastructure facilities",
    "Agriculture Infrastructure": "agricultural facilities",
    "Affected Livestock and Animals": "affected animals",
    "Recreation, Tourism, and Culture": "unknown",
    "Economy and Market": "unknown",
    "Access to Healthcare": "people",
    "Access to transport and Mobility": "people",
    "Access to Food": "people",
    "Access to Water, Sanitation, and Hygiene": "people",
    "Other Human Impacts": "unknown",
    "Other Infrastructure Impacts": "unknown",
    "Other Agricultural Impacts": "unknown",
    "Other Service Access Impacts": "people",
}
default_subtype_unit = {
    'Affected People': "people",
    'Injured People': "people",
    'Displaced People': "people",
    'Homeless People': "people",
    'Missing People': "people",
    'Human Deaths': "people",
    'Residential Buildings': "homes",
    'Informal settlements': "undefined informal settlements",
    'Education Infrastructure': "schools",
    'Human Health and Wellbeing' : "unknown",
    'Infected and Ill People': "people",
    'Road Infrastructure' : "roads",
    'Other Transportation Infrastructure' : "undefined other transportation infrastructure",
    'Water, Sanitation, and Hygiene Infrastructure': "undefined WASH facilities",
    'Healthcare Infrastructure': "undefined healthcare facilities",
    'IT and Communication Infrastructure': "undefined IT and communication facilities",
    'Education Infrastructure': "schools",
    'Power and Energy Production Infrastructure' : "undefined power and energy production infrastructure facilities",
    'Agriculture Infrastructure': "undefined agricultural facilities",
    'Crop Production and Forestry': "undefined crop production and forestry",
    'Affected Livestock and Animals': "undefined affected animals",
    'Other Economic and Livelihood Impacts': "CHF",
    'Recreation, Tourism, and Culture' : "unknown",
    'Access to Healthcare': "people",
    'Access to transport and Mobility': "people",
    'Water Quality and Availability' : "unknown",
    'Access to Education':"people",
    'Access to Power and Energy':"people",
    'Access to Food':"people",
    'Access to Water, Sanitation, and Hygiene':"people",
    'Other Human Impacts': "unknown",
    'Other Infrastructure Impacts': "unknown",
    'Other Agricultural Impacts': "unknown",
    'Other Service Access Impacts': "people"
}

#impactUnitType_list = ["count", "distance", "area", "weight", "volume"]

#impact_subtypes_unit_dict = {
#        "Affected People": ["people"],
#        "Injured People": ["people"],
#        "Displaced People": ["people"],
#        "Homeless People": ["people"],
#        "Missing People": ["people"],
#        "Human Deaths": ["people"],
#        "Human Health and Wellbeing": ["people", "cases"],
#        "Roads" : ["roads", "km of roads", "CHF"],
#        "Other transportation infrastructure" : ["transportation facilities", "km of transportation facilities", "CHF"],
#        "Water, Sanitation, and Hygiene Infrastructure": ["WASH facilities","CHF"],
#        "Healthcare Infrastructure": ["healthcare facilities","CHF"],
#        "IT and Communication Infrastructure": ["IT and communication facilities","CHF"],
#        "Residential Buildings": ["houses","CHF"],
#        "Informal Settlements": ["informal settlements","CHF"],
#        "Education Infrastructure": ["education facilities","CHF"],
#        "Agricultural Infrastructure": ["agricultural facilities","CHF"],
#        "Power and Energy Production Infrastructure": ["power and energy production facilities","CHF"],
#        "Crop Production and Forestry": ["kg of crops", "km**2 of crops", "trees", "CHF"],
#        "Affected Livestock and Animals": ["affected animals","CHF"],
#        "Recreation, Tourism, and Culture": ["recreation, tourisme and culture facilities", "CHF"],
#        "Economy and Market": ["CHF"],
#        "Access to Healthcare": ["people"],
#        "Access to transport and Mobility": ["people"],
#        "Water Quality and Availability": ["people", "m**3"],
#        "Access to Education": ["people"],
#        "Access to Power and Energy": ["people"],
#        }