# Define unit conversion mapping

METRIC_UNIT_MAPPING = {
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
METRIC_UNIT_KW_RECLASS = {
                    'km' : [r"(?<!\b(squared?)\b)\s\b(kilometers?|kilometres?|kms?)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2)\b)"],
                    'km**2' : [r"\b(squared?)\s+(kilometers?|kilometres?|kms?)\b",
                            r"\b(kilometers?|kilometres?|kms?)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'm**2' : [r"\b(squared?)\s+(meters?|metres?|m)\b",
                            r"\b(meters?|metres?|m)\s?(\*\*\s*2|\*\*2|\^2|²|square|squared|2)\b(?<!\.\d)"],
                    'mi**2' : [r"\b(squared?)\s+(mile|miles|mi)\b",
                            r"\b(mile|miles|mi)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'ft**2' : [r"\b(squared?)\s+(feet|foot|ft)\b",
                            r"\b(feet|foot|ft)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'kg' : [r"\b(kgs?|kilograms?)\b"],
                    'm**3' : [r"\b(?<=(cube|cubic))\s*(meters?|metres?|m)\b",
                            r"\b(meters?|metres?|m)s?\s?(\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)\b(?<!\.\d)"],
                    "acre": [r"\b(acres?|acers?)\b"],
                    "feet": [r"(?<!\b(squared?|cube|cubic)\s*)\b(feet|foot|ft)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)|\s+\d+(\.\d+)?)"],
                    "hectare": [r"\b(hectares?|ha|hectors?)\b"],
                    "ton": [r"\b(?<!\b(metric)\s*)(ton|tons)\b"],
                    "tonne": [r"\b(tonne|tonnes|metric tons?|mt)\b"],
                    "pound": [r"\b(pounds|lbs?)\b"],
                    "meter": [r"(?<!\b(squared?|cube|cubic)\s*)\b(meters?|metres?|m)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)|\s+\d+(\.\d+)?)"],
                    "liter": [r"\b(liters?|litres?|l)\b"],
                    "miles": [r"(?<!\b(squared?|cube|cubic)\s*)\b(miles?|mi)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)|\s+\d+(\.\d+)?)"],
                    "gallon": [r"\b(gallons|gal)\b"],
}



#reclassify units
UNIT_CONVERTER = {
    r"\b(families)\b" : (3, "people"),
    r"\b(villages)\b": (1000, "people"),
    r"\b(communities)\b": (100, "people"),
    }

PEOPLE_NORMALIZER = r"\b(people|deaths|cases|injuries|displaced|missings|homelesses)\b"
UNIT_TYPE_KW_RECLASS = {
                        'km' : r"\b(?:kilometer|kilometre|km)s?(?!\s*(?:\*\*\s*2|\*\*2|\^2|²|square|squared|2))\b",
                        'km**2' : r"\b(?:kilometer|kilometre|km)s?\s*(?:\*\*\s*2|\*\*2|\^2|²|square|squared|2)\b",
                        'kg' : r"\b(kg|kilograms?)\b",
                        'm**3' : r"\b(?:meter|metre|m)s?\s?(?:\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)\b",
                        '%' : r"\b(%|perc\.?|per(\s)?cent(s)?|percentages?)\b",
}
HARMONIZE_UNITS_KW = {
    'people': r"\b(people|persons?|individuals?|residents?)\b",
    'families' : r"\b(family|families|households?)\b",
    'communities' : r"\b(community|communities)\b",
    'villages' : r"\b(villages?|hamlets?)\b",
    'roads': r"\b(roads?|routes?|bridges?|highways?|motorways?)\b",
    'vehicles' : r"\b(vehicles?|motor vehicles?|cars?|trucks?|vessels?|boats?)\b",
    'structures' : r"\b(facilities|facility|buildings?|(infra)?structures?|buildings?|utilities?)\b",
    'homes' : r"\b(residences?|houses?|homes?|housing units?|dwellings?|properties?)\b",
    '%' : r"\b(%|perc\.?|per(\s)?cent(s)?|percentages?)\b",

}
UNIT_KW_RECLASS = {
    'people': r"\b(people)\b",
    'deaths' : r"\b(fatalities?|deaths?|lives|loss(es)? of life|deceased|dead)\b",
    'displaced' : r"\b(displaced|evacuees?|evacuated|idps?)\b",
    'homelesses' : r"\b(homeless(es)?|homeless people)\b",
    'injuries' : r"\b(injuries|injured|injury|casualties|casualty)\b",
    'missings' : r"\b(missing|missing persons?|missing individuals?|missing residents?|missing people|disappeared)\b",
    'cases' : r"\b(cases?|cases of|cases of illness|infected)\b",
    'roads' : r"\b(roads)\b",
    'transportation structures': r"\b(rail(way|road)?s?|train tracks?|airports?|vehicles?|seaports?)\b",
    'WASH structures': r"\b((water|sanitation|hygiene|wastewater) (structures|sources?|plants?|treatment plants?|systems?|supply|supplies)|latrines?|wells?|taps?|reservoirs?|aqueducts?|toilets?)\b",
    'healthcare structures': r"\b((health(care)?|medical) (centers?|centres?|units?|structures?)|hospitals?|clinics?|maternit(y|ies)|posts?)\b",
    'IT and communication structures': r"\b((tele)?communication(s)? (structures?|center?|lines?)|radios?|tv|cell towers?|antennas?)\b",
    'power and energy production structures': r"\b((power|energy|wind|solar|hydro) structures?|generators?|dams?|electric poles?|lines?|supply|supplies)\b",
    'homes': r"\b(residential structures|homes?)\b",
    'education structures': r"\b(education(al|learning)? (centers?|centres?|units?|structures?|institutions?)|schools?|universit(y|ies)|colleges?)\b",
    'undefined structures' : r"\b((critical|public) (structures|units?)|^structures$|of structures)\b",
    'crop production and forestry': r"\b(crops?|(farm)?lands?|fields?|forests?|trees?|bananas?|coffee|cocoa|cotton|maize|rice|sorghum|soybeans?|sugar|tobacco|wheat)\b",
    'agricultural structures': r"\b(irrigation|barns?|farms?)\b",
    'affected animals': r"\b(livestock|animals?|fish|cows?|sheep|poultr(y|ies)|cattle|goats?|pigs?|chickens?|horses?|heads?)\b",
    'informal settlements': r"\b(camps?|tents?|refuge(e|es)|settlements?|shelters?|idp sites?|huts?)\b",
    'EUR' : r"\b(euro?s?|€)\b",
    'businesses' : r"\b(business(es)?|companies?|industries?|sectors?|enterprises?)\b",
    'null' : r"\b(null|none|nan|np.nan)\b",
}

ALL_POSSIBLE_UNITS = {} #dictionary of all possible units
[ALL_POSSIBLE_UNITS.update(d) for d in [METRIC_UNIT_KW_RECLASS, HARMONIZE_UNITS_KW, UNIT_KW_RECLASS]]

