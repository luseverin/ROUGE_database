#Constants for impact definition


impactType_list = ["Human",
                   "Service Access",
                   "Infrastructure",
                   "Agriculture",
                   "Economic Activity & Livelihood Production"]


impactSubtype_list = ["Affected People", "Injured People", "Displaced People", "Homeless People", "Missing People", "Human Deaths", "Human Health and Wellbeing", "Infected and Ill People",#Affected Families and Households"
                      "Road Infrastructure", "Other Transportation Infrastructure", "Water, Sanitation, and Hygiene Infrastructure", "Healthcare Infrastructure",
                      "IT and Communication Infrastructure", "Residential Buildings", "Informal settlements", "Education Infrastructure", "Power and Energy Production Infrastructure",
                      "Agricultural Infrastructure", "Crop Production and Forestry", "Affected Livestock and Animals", "Other Economic Activity & Livelihood Production", "Recreation, Tourism, and Culture",
                      "Access to Healthcare", "Mobility and Access to Transport", "Water Quality and Availability", "Access to Education", "Access to Power and Energy", "Access to Food", "Access to Water, Sanitation, and Hygiene",
                      "Other Human Impacts","Other Infrastructure Impacts","Other Agricultural Impacts", "Other Service Access Impacts"]
                      #"Health Impacts"]

impact_subtypes_desc_dict = {
    #"Human":
    #The impacts on the human population resulting from the hazards.
    "Affected People": "Total number of individuals impacted by the hazard event.",
    "Injured People": "Number of people injured, including those hospitalised or admitted.",
    "Displaced People": "Number of people forcefully displaced or evacuated before or following the event.",
    "Homeless People": "Number of people losing housing following the event.",
    "Missing People": "Number of people unaccounted for following the event.",
    "Human Deaths": "Number of fatalities caused by the hazard.",
    "Infected and Ill People" : "Number of people contaminated (cases) by an infectious disease." ,
    "Human Health and Wellbeing" : "Generic impacts on human health (physical, mental) or wellbeing not directly associated with the spread of an infectious disease.",
    "Other Human Impacts" : "Any identified impact on humans which cannot be associated with the previous impactSubtypes.",

    #"Infrastructure":
    #The impacts on the built infrastructure resulting from the hazards.
    "Road Infrastructure" : "Roads and road infrastructure (e.g. bridges, highways..) impacted by a hazard.",
    "Other Transportation Infrastructure": "Transportation infrastructure, other than roads, impacted by a hazard. For example : Railways, airport, ferries, cars…",
    "Water, Sanitation, and Hygiene Infrastructure": "Number of water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a hazard.",
    "Healthcare Infrastructure": "Number of healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc.  impacted by a hazard.",
    "IT and Communication Infrastructure": "Number of IT and communication infrastructure  such as data centers, communication towers, and cables impacted by a hazard.",
    "Residential Buildings": "Number of residential buildings impacted by a hazard. This category also encompasses the impact on houses.",
    "Informal Settlements": "Number of informal settlements such as refugee camps, slums, tents, etc. impacted by a hazard.",
    "Education Infrastructure": "Number of education infrastructures such as schools, universities, etc. impacted by a hazard.",
    "Power and Energy Production Infrastructure": "Number of energy production infrastructures such as power plants, turbines, grids, pipelines, etc., impacted by a hazard.",
    "Agricultural Infrastructure": "Number of agricultural infrastructures such as farms, warehouses, greenhouses, etc. impacted by a hazard. This category should also gather impacted infrastructure for fisheries such as vessels, boats, etc.",
    "Other Infrastructural Impacts" : "Any identified impact on infrastructure which cannot be associated with the previous impactSubtypes, e.g. dykes, embankment, shops, etc.",

    #"Service access":
    #The impacts on the provision of basic services to the population resulting from the hazards.
    "Access to Healthcare" : "People losing the ability to obtain needed medical services, including preventative care, emergency services…",
    "Access to Food" : "People losing access to a secure food supply.",
    "Mobility and Access to Transport" : "People losing the capacity to move safely and efficiently between locations.",
    "Access to Water, Sanitation, and Hygiene" : "People losing access to water, sanitation, and hygiene services.",
    "Water Quality and Availability" : "People losing safe, clean, and consistent supply of water for drinking, sanitation, and other essential uses.",
    "Access to Education" : "People losing the ability to attend educational institutions and receive instruction.",
    "Access to Power and Energy" :  "People losing access to electricity, gas, or other energy sources necessary for households, businesses, and public services.",
    "Other Service Access Impacts" : "Any identified impact on service access which cannot be associated with the previous impactSubtypes.",

    #"Agriculture":
    #The impacts on agriculture resulting from the hazards.
    "Crop Production and Forestry" : "Number of crops, agricultural production and forest impacted by a hazard.",
    "Affected Livestock and Animals" : "Total number of animals, including terrestrial and aquatic species, impacted by the hazard (e.g. loss, death, perished animals or fishes).",
    "Other Agricultural Impacts" : "Any identified impact on agriculture which cannot be associated with the previous impactSubtypes.",

    #"Economic Activity & Livelihood Production":
    #The impacts on the economy and livelihood resulting from the hazards.
    "Recreation, Tourism, and Culture" : "Tourist attractions and cultural sites impacted by a hazard.",
    "Other Economic Activity & Livelihood Production" : "Any identified impact on the economy which cannot be associated with the previous impactSubtypes.",
}

impact_kw_reclass = {
    'Affected People': r"\bAffected People\b",
    'Injured People': r"\bInjured People\b",
    'Displaced People': r"\b(Displaced People|Displacement)\b",
    'Homeless People': r"\bHomeless People\b",
    'Missing People': r"\bMissing People\b",
    'Human Deaths': r"\bHuman Deaths\b",
    'Human Health and Wellbeing': r"\bHuman Health and Wellbeing\b",
    'Infected and Ill People': r"\bInfected and Ill People\b",


    'Road Infrastructure': r"\b(Road Infrastructure|road)s?\b",
    'Other Transportation Infrastructure': r"\bOther Transportation Infrastructure\b",
    'Water, Sanitation, and Hygiene Infrastructure': r"\bWater,?\s*Sanitation,?\s*and Hygiene Infrastructure\b",
    'Healthcare Infrastructure': r"\bHealthcare Infrastructure\b",
    'IT and Communication Infrastructure': r"\bIT and Communication Infrastructure\b",

    'Residential Buildings': r"\bResidential Buildings\b",
    'Informal Settlements': r"\bInformal settlements\b",
    'Education Infrastructure': r"\bEducation Infrastructure\b",
    'Power and Energy Production Infrastructure': r"\bPower and Energy Production Infrastructure\b",
    'Agricultural Infrastructure': r"\bAgricultur(?:e|al)? Infras(?:tructure|tucture)\b",

    'Crop Production and Forestry': r"\bCrop Production and Forestry\b",
    'Affected Livestock and Animals': r"\bAffected Livestock and Animals\b",

    'Other Economic Activity & Livelihood Production': r"\b(Other Economic(?: Activity)? (?:and|&) Livelihood (?:Production|Impact(?:s)?)|Economy and Market|Livelihood|employment|basic needs)\s*\b",
    'Recreation, Tourism, and Culture': r"\bRecreation, Tourism, and Culture\b",

    'Access to Healthcare': r"\bAccess to Healthcare\b",
    'Mobility and Access to Transport': r"\b(Access to transport and Mobility|Access to transport|Mobility)\b",
    'Water Quality and Availability': r"\bWater Quality and Availability\b",
    'Access to Education': r"\bAccess to Education\b",
    'Access to Power and Energy': r"\bAccess to Power and Energy\b",
    'Access to Food': r"\bfood\b",
    'Access to Water, Sanitation, and Hygiene': r"\bAccess to Water,?\s*Sanitation,?\s*and Hygiene\b",

    'Other Infrastructural Impacts': r"\b(Other Infrastructur(?:e|al)? Impacts?)\b",
    'Other Human Impacts': r"\bOther Human.* Impacts?\b",
    'Other Service Access Impacts': r"\bOther Service Access(?: Impacts?)?\b",
    'Other Agricultural Impacts': r"\bOther Agricultural.* Impacts?\b",
}


