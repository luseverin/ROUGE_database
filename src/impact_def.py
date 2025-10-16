#Constants for impact definition
from src.ImpactRegistry import Impacts
#define each impact

Impacts.register(
    key="Affected People",
    main_type="Human",
    description="Total number of individuals impacted by the hazard event.",
    keyword=r"\bAffected People\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Injured People",
    main_type="Human",
    description="Number of people injured, including those hospitalised or admitted.",
    keyword=r"\bInjured People\b",
    expected_unit="injuries",
    default_unit="people"
)

Impacts.register(
    key="Displaced People",
    main_type="Human",
    description="Number of people forcefully displaced or evacuated before or following the event.",
    keyword=r"\b(Displaced People|Displacement)\b",
    expected_unit="displaced",
    default_unit="people"
)

Impacts.register(
    key="Homeless People",
    main_type="Human",
    description="Number of people losing housing following the event.",
    keyword=r"\bHomeless People\b",
    expected_unit="homelesses",
    default_unit="people"
)

Impacts.register(
    key="Missing People",
    main_type="Human",
    description="Number of people unaccounted for following the event.",
    keyword=r"\bMissing People\b",
    expected_unit="missings",
    default_unit="people"
)

Impacts.register(
    key="Human Deaths",
    main_type="Human",
    description="Number of fatalities caused by the hazard.",
    keyword=r"\bHuman Deaths\b",
    expected_unit="deaths",
    default_unit="people"
)

Impacts.register(
    key="Infected and Ill People",
    main_type="Human",
    description="Number of people contaminated (cases) by an infectious disease.",
    keyword=r"\bInfected and Ill People\b",
    expected_unit="cases",
    default_unit="people"
)

Impacts.register(
    key="Human Health and Wellbeing",
    main_type="Human",
    description="Generic impacts on human health (physical, mental) or wellbeing not directly associated with the spread of an infectious disease.",
    keyword=r"\bHuman Health and Wellbeing\b",
    expected_unit="unknown",
    default_unit="unknown"
)

Impacts.register(
    key="Road Infrastructure",
    main_type="Infrastructure",
    description="Roads and road infrastructure (e.g. bridges, highways..) impacted by a hazard.",
    keyword=r"\b(Road Infrastructure|road)s?\b",
    expected_unit="roads",
    default_unit="roads"
)

Impacts.register(
    key="Other Transportation Infrastructure",
    main_type="Infrastructure",
    description="Transportation infrastructure, other than roads, impacted by a hazard. For example: Railways, airport, ferries, cars…",
    keyword=r"\bOther Transportation Infrastructure\b",
    expected_unit="transportation structures",
    default_unit="undefined transportation structures"
)

Impacts.register(
    key="Water, Sanitation, and Hygiene Infrastructure",
    main_type="Infrastructure",
    description="Number of water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a hazard.",
    keyword=r"\bWater,?\s*Sanitation,?\s*and Hygiene Infrastructure\b",
    expected_unit="WASH structures",
    default_unit="undefined WASH structures"
)

Impacts.register(
    key="Healthcare Infrastructure",
    main_type="Infrastructure",
    description="Number of healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc. impacted by a hazard.",
    keyword=r"\bHealthcare Infrastructure\b",
    expected_unit="healthcare structures",
    default_unit="undefined healthcare structures"
)

Impacts.register(
    key="IT and Communication Infrastructure",
    main_type="Infrastructure",
    description="Number of IT and communication infrastructure such as data centers, communication towers, and cables impacted by a hazard.",
    keyword=r"\bIT and Communication Infrastructure\b",
    expected_unit="IT and communication structures",
    default_unit="undefined IT and communication structures"
)

Impacts.register(
    key="Residential Buildings",
    main_type="Infrastructure",
    description="Number of residential buildings impacted by a hazard. This category also encompasses the impact on houses.",
    keyword=r"\bResidential Buildings\b",
    expected_unit="homes",
    default_unit="homes"
)

Impacts.register(
    key="Informal Settlements",
    main_type="Infrastructure",
    description="Number of informal settlements such as refugee camps, slums, tents, etc. impacted by a hazard.",
    keyword=r"\bInformal settlements\b",
    expected_unit="informal settlements",
    default_unit="informal settlements"
)

Impacts.register(
    key="Education Infrastructure",
    main_type="Infrastructure",
    description="Number of education infrastructures such as schools, universities, etc. impacted by a hazard.",
    keyword=r"\bEducation Infrastructure\b",
    expected_unit="education structures",
    default_unit="schools"
)

Impacts.register(
    key="Power and Energy Production Infrastructure",
    main_type="Infrastructure",
    description="Number of energy production infrastructures such as power plants, turbines, grids, pipelines, etc., impacted by a hazard.",
    keyword=r"\bPower and Energy Production Infrastructure\b",
    expected_unit="power and energy production structures",
    default_unit="undefined power and energy production structures"
)

Impacts.register(
    key="Agricultural Infrastructure",
    main_type="Infrastructure",
    description="Number of agricultural infrastructures such as farms, warehouses, greenhouses, etc. impacted by a hazard. This category should also gather impacted infrastructure for fisheries such as vessels, boats, etc.",
    keyword=r"\bAgricultur(?:e|al)? Infras(?:tructure|tucture)\b",
    expected_unit="agricultural structures",
    default_unit="undefined agricultural structures"
)

Impacts.register(
    key="Crop Production and Forestry",
    main_type="Agriculture",
    description="Number of crops, agricultural production and forest impacted by a hazard.",
    keyword=r"\bCrop Production and Forestry\b",
    expected_unit="crop production and forestry",
    default_unit="crop production and forestry"
)

Impacts.register(
    key="Affected Livestock and Animals",
    main_type="Agriculture",
    description="Total number of animals, including terrestrial and aquatic species, impacted by the hazard (e.g. loss, death, perished animals or fishes).",
    keyword=r"\bAffected Livestock and Animals\b",
    expected_unit="affected animals",
    default_unit="affected animals"
)

Impacts.register(
    key="Recreation, Tourism, and Culture",
    main_type="Economic Activity & Livelihood Production",
    description="Tourist attractions and cultural sites impacted by a hazard.",
    keyword=r"\bRecreation, Tourism, and Culture\b",
    expected_unit="unknown",
    default_unit="unknown"
)

Impacts.register(
    key="Other Economic Activity & Livelihood Production",
    main_type="Economic Activity & Livelihood Production",
    description="Any identified impact on the economy which cannot be associated with the previous impactSubtypes.",
    keyword=r"\b(Other Economic(?: Activity)? (?:and|&) Livelihood (?:Production|Impact(?:s)?)|Economy and Market|Livelihood|employment|basic needs)\s*\b",
    expected_unit="businesses",
    default_unit="unknown"
)

Impacts.register(
    key="Access to Healthcare",
    main_type="Service access",
    description="People losing the ability to obtain needed medical services, including preventative care, emergency services…",
    keyword=r"\bAccess to Healthcare\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Access to Food",
    main_type="Service access",
    description="People losing access to a secure food supply.",
    keyword=r"\bfood\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Mobility and Access to Transport",
    main_type="Service access",
    description="People losing the capacity to move safely and efficiently between locations.",
    keyword=r"\b(Access to transport and Mobility|Access to transport|Mobility)\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Access to Water, Sanitation, and Hygiene",
    main_type="Service access",
    description="People losing access to water, sanitation, and hygiene services.",
    keyword=r"\bAccess to Water,?\s*Sanitation,?\s*and Hygiene\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Water Quality and Availability",
    main_type="Service access",
    description="People losing safe, clean, and consistent supply of water for drinking, sanitation, and other essential uses.",
    keyword=r"\bWater Quality and Availability\b",
    expected_unit="unknown",
    default_unit="unknown"
)

Impacts.register(
    key="Access to Education",
    main_type="Service access",
    description="People losing the ability to attend educational institutions and receive instruction.",
    keyword=r"\bAccess to Education\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Access to Power and Energy",
    main_type="Service access",
    description="People losing access to electricity, gas, or other energy sources necessary for households, businesses, and public services.",
    keyword=r"\bAccess to Power and Energy\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Other Human Impacts",
    main_type="Human",
    description="Any identified impact on humans which cannot be associated with the previous impactSubtypes.",
    keyword=r"\bOther Human.* Impacts?\b",
    expected_unit="unknown",
    default_unit="unknown"
)

Impacts.register(
    key="Other Infrastructural Impacts",
    main_type="Infrastructure",
    description="Any identified impact on infrastructure which cannot be associated with the previous impactSubtypes, e.g. dykes, embankment, shops, etc.",
    keyword=r"\b(Other Infrastructur(?:e|al)? Impacts?)\b",
    expected_unit="undefined structures",
    default_unit="unknown"
)

Impacts.register(
    key="Other Service Access Impacts",
    main_type="Service access",
    description="Any identified impact on service access which cannot be associated with the previous impactSubtypes.",
    keyword=r"\bOther Service Access(?: Impacts?)?\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Other Agricultural Impacts",
    main_type="Agriculture",
    description="Any identified impact on agriculture which cannot be associated with the previous impactSubtypes.",
    keyword=r"\bOther Agricultural.* Impacts?\b",
    expected_unit="unknown",
    default_unit="unknown"
)

IMPACT_TYPES = Impacts.get_main_types()
IMPACT_SUBTYPES = Impacts.get_subtypes()
IMPACT_DESCRIPTIONS = Impacts.get_descriptions()
IMPACT_KEYWORDS = Impacts.get_keywords()
IMPACT_EXPECTED_UNITS = Impacts.get_expected_units()
IMPACT_DEFAULT_UNITS = Impacts.get_default_units()

#impactType_list = ["Human",
#                   "Service Access",
#                   "Infrastructure",
#                   "Agriculture",
#                   "Economic Activity & Livelihood Production"]
#
#
#impactSubtype_list = ["Affected People", "Injured People", "Displaced People", "Homeless People", "Missing People", "Human Deaths", "Human Health and Wellbeing", "Infected and Ill People",#Affected Families and Households"
#                      "Road Infrastructure", "Other Transportation Infrastructure", "Water, Sanitation, and Hygiene Infrastructure", "Healthcare Infrastructure",
#                      "IT and Communication Infrastructure", "Residential Buildings", "Informal settlements", "Education Infrastructure", "Power and Energy Production Infrastructure",
#                      "Agricultural Infrastructure", "Crop Production and Forestry", "Affected Livestock and Animals", "Other Economic Activity & Livelihood Production", "Recreation, Tourism, and Culture",
#                      "Access to Healthcare", "Mobility and Access to Transport", "Water Quality and Availability", "Access to Education", "Access to Power and Energy", "Access to Food", "Access to Water, Sanitation, and Hygiene",
#                      "Other Human Impacts","Other Infrastructure Impacts","Other Agricultural Impacts", "Other Service Access Impacts"]
#                      #"Health Impacts"]
#
#impact_subtypes_desc_dict = {
#    #"Human":
#    #The impacts on the human population resulting from the hazards.
#    "Affected People": "Total number of individuals impacted by the hazard event.",
#    "Injured People": "Number of people injured, including those hospitalised or admitted.",
#    "Displaced People": "Number of people forcefully displaced or evacuated before or following the event.",
#    "Homeless People": "Number of people losing housing following the event.",
#    "Missing People": "Number of people unaccounted for following the event.",
#    "Human Deaths": "Number of fatalities caused by the hazard.",
#    "Infected and Ill People" : "Number of people contaminated (cases) by an infectious disease." ,
#    "Human Health and Wellbeing" : "Generic impacts on human health (physical, mental) or wellbeing not directly associated with the spread of an infectious disease.",
#    "Other Human Impacts" : "Any identified impact on humans which cannot be associated with the previous impactSubtypes.",
#
#    #"Infrastructure":
#    #The impacts on the built infrastructure resulting from the hazards.
#    "Road Infrastructure" : "Roads and road infrastructure (e.g. bridges, highways..) impacted by a hazard.",
#    "Other Transportation Infrastructure": "Transportation infrastructure, other than roads, impacted by a hazard. For example : Railways, airport, ferries, cars…",
#    "Water, Sanitation, and Hygiene Infrastructure": "Number of water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a hazard.",
#    "Healthcare Infrastructure": "Number of healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc.  impacted by a hazard.",
#    "IT and Communication Infrastructure": "Number of IT and communication infrastructure  such as data centers, communication towers, and cables impacted by a hazard.",
#    "Residential Buildings": "Number of residential buildings impacted by a hazard. This category also encompasses the impact on houses.",
#    "Informal Settlements": "Number of informal settlements such as refugee camps, slums, tents, etc. impacted by a hazard.",
#    "Education Infrastructure": "Number of education infrastructures such as schools, universities, etc. impacted by a hazard.",
#    "Power and Energy Production Infrastructure": "Number of energy production infrastructures such as power plants, turbines, grids, pipelines, etc., impacted by a hazard.",
#    "Agricultural Infrastructure": "Number of agricultural infrastructures such as farms, warehouses, greenhouses, etc. impacted by a hazard. This category should also gather impacted infrastructure for fisheries such as vessels, boats, etc.",
#    "Other Infrastructural Impacts" : "Any identified impact on infrastructure which cannot be associated with the previous impactSubtypes, e.g. dykes, embankment, shops, etc.",
#
#    #"Service access":
#    #The impacts on the provision of basic services to the population resulting from the hazards.
#    "Access to Healthcare" : "People losing the ability to obtain needed medical services, including preventative care, emergency services…",
#    "Access to Food" : "People losing access to a secure food supply.",
#    "Mobility and Access to Transport" : "People losing the capacity to move safely and efficiently between locations.",
#    "Access to Water, Sanitation, and Hygiene" : "People losing access to water, sanitation, and hygiene services.",
#    "Water Quality and Availability" : "People losing safe, clean, and consistent supply of water for drinking, sanitation, and other essential uses.",
#    "Access to Education" : "People losing the ability to attend educational institutions and receive instruction.",
#    "Access to Power and Energy" :  "People losing access to electricity, gas, or other energy sources necessary for households, businesses, and public services.",
#    "Other Service Access Impacts" : "Any identified impact on service access which cannot be associated with the previous impactSubtypes.",
#
#    #"Agriculture":
#    #The impacts on agriculture resulting from the hazards.
#    "Crop Production and Forestry" : "Number of crops, agricultural production and forest impacted by a hazard.",
#    "Affected Livestock and Animals" : "Total number of animals, including terrestrial and aquatic species, impacted by the hazard (e.g. loss, death, perished animals or fishes).",
#    "Other Agricultural Impacts" : "Any identified impact on agriculture which cannot be associated with the previous impactSubtypes.",
#
#    #"Economic Activity & Livelihood Production":
#    #The impacts on the economy and livelihood resulting from the hazards.
#    "Recreation, Tourism, and Culture" : "Tourist attractions and cultural sites impacted by a hazard.",
#    "Other Economic Activity & Livelihood Production" : "Any identified impact on the economy which cannot be associated with the previous impactSubtypes.",
#}
#
#impact_kw_reclass = {
#    'Affected People': r"\bAffected People\b",
#    'Injured People': r"\bInjured People\b",
#    'Displaced People': r"\b(Displaced People|Displacement)\b",
#    'Homeless People': r"\bHomeless People\b",
#    'Missing People': r"\bMissing People\b",
#    'Human Deaths': r"\bHuman Deaths\b",
#    'Human Health and Wellbeing': r"\bHuman Health and Wellbeing\b",
#    'Infected and Ill People': r"\bInfected and Ill People\b",
#
#
#    'Road Infrastructure': r"\b(Road Infrastructure|road)s?\b",
#    'Other Transportation Infrastructure': r"\bOther Transportation Infrastructure\b",
#    'Water, Sanitation, and Hygiene Infrastructure': r"\bWater,?\s*Sanitation,?\s*and Hygiene Infrastructure\b",
#    'Healthcare Infrastructure': r"\bHealthcare Infrastructure\b",
#    'IT and Communication Infrastructure': r"\bIT and Communication Infrastructure\b",
#
#    'Residential Buildings': r"\bResidential Buildings\b",
#    'Informal Settlements': r"\bInformal settlements\b",
#    'Education Infrastructure': r"\bEducation Infrastructure\b",
#    'Power and Energy Production Infrastructure': r"\bPower and Energy Production Infrastructure\b",
#    'Agricultural Infrastructure': r"\bAgricultur(?:e|al)? Infras(?:tructure|tucture)\b",
#
#    'Crop Production and Forestry': r"\bCrop Production and Forestry\b",
#    'Affected Livestock and Animals': r"\bAffected Livestock and Animals\b",
#
#    'Other Economic Activity & Livelihood Production': r"\b(Other Economic(?: Activity)? (?:and|&) Livelihood (?:Production|Impact(?:s)?)|Economy and Market|Livelihood|employment|basic needs)\s*\b",
#    'Recreation, Tourism, and Culture': r"\bRecreation, Tourism, and Culture\b",
#
#    'Access to Healthcare': r"\bAccess to Healthcare\b",
#    'Mobility and Access to Transport': r"\b(Access to transport and Mobility|Access to transport|Mobility)\b",
#    'Water Quality and Availability': r"\bWater Quality and Availability\b",
#    'Access to Education': r"\bAccess to Education\b",
#    'Access to Power and Energy': r"\bAccess to Power and Energy\b",
#    'Access to Food': r"\bfood\b",
#    'Access to Water, Sanitation, and Hygiene': r"\bAccess to Water,?\s*Sanitation,?\s*and Hygiene\b",
#
#    'Other Infrastructural Impacts': r"\b(Other Infrastructur(?:e|al)? Impacts?)\b",
#    'Other Human Impacts': r"\bOther Human.* Impacts?\b",
#    'Other Service Access Impacts': r"\bOther Service Access(?: Impacts?)?\b",
#    'Other Agricultural Impacts': r"\bOther Agricultural.* Impacts?\b",
#}


