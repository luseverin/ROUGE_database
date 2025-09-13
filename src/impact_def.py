#Constants for impact definition


impactType_list = ["Human",
"Service Access",
"Infrastructure",
"Agriculture",
"Economic Activity & Livelihood Production"]


impactSubtype_list = ["Affected People", "Injured People", "Displaced People", "Homeless People", "Missing People", "Human Deaths", "Human Health and Wellbeing", "Infected and Ill People",#Affected Families and Households"
                      "Road Infrastructure", "Other Transportation Infrastructure", "Water, Sanitation, and Hygiene Infrastructure", "Healthcare Infrastructure",
                      "IT and Communication Infrastructure", "Residential Buildings", "Informal settlements", "Education Infrastructure", "Power and Energy Production Infrastructure",
                      "Agriculture Infrastructure", "Crop Production and Forestry", "Affected Livestock and Animals", "Other Economic and Livelihood Impacts", "Recreation, Tourism, and Culture",
                      "Access to Healthcare", "Access to transport and Mobility", "Water Quality and Availability", "Access to Education", "Access to Power and Energy", "Access to Food", "Access to Water, Sanitation, and Hygiene",
                      "Other Human Impacts","Other Infrastructure Impacts","Other Agricultural Impacts", "Other Service Access Impacts"]
                      #"Health Impacts"]

impact_subtypes_desc_dict = {
        "Affected People": "People impacted by a natural hazard event (the term affected must be mentioned). Reports the impacts in number of people.",
        "Injured People": "People injured, including those hospitalized or admitted (the term injured must be used), to a natural hazard event. Reports the impacts in number of people.",
        "Displaced People": "People forcefully displaced or evacuated before or following the event. Reports the impacts in number of people.",
        "Homeless People": "People who lost their homes, to a natural hazard event. Reports the impacts in number of people.",
        "Missing People": "People unaccounted for following a natural hazard event. Reports the impacts in number of people.",
        "Human Deaths": "Fatalities caused by a natural hazard event. Reports the impacts in number of deaths.",
        "Human Health and Wellbeing": "The impacts on human health and wellbeing such as infection, illness, etc. resulting from a natural hazard event. Reports the impacts in number of people.",
        "Roads" : "Roads (including bridges and highways) blocked or damaged or disrupted traffic due to a natural hazard event. Reports the impacts in number of , kilometers of, or damage cost of roads or bridges affected.",
        "Other Transportation Infrastructure": "The impacts on the transportation infrastructures other than roads such as airports, railways, etc. resulting from the natural hazard event. Reports the impacts in number of or kilometers of or damage cost of facilities affected.",
        "Water, Sanitation, and Hygiene Infrastructure": "Water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a natural hazard event.  Reports the impacts in number of or damage cost of facilities affected.",
        "Healthcare Infrastructure": "Healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc. impacted by a natural hazard event. Reports the impacts in number of or damage cost of facilities affected.",
        "IT and Communication Infrastructure": "IT and communication infrastructure such as data centers, communication towers, and cables impacted by a natural hazard event. Reports the impacts in number of or damage cost of facilities affected.",
        "Residential Buildings": "Residential buildings impacted by a natural hazard event. Reports the impacts in number of or damage cost of buildings affected.",
        "Informal Settlements":"Informal settlements such as refugee camps, slums, tents, etc. impacted by a natural hazard event. Reports the impacts in number of or damage cost of settlements affected.",
        "Education Infrastructure": "Education infrastructure such as schools, universities, etc. impacted by a natural hazard event. Reports the impacts in number of or damage cost of facilities affected.",
        "Agriculture Infrastructure": "Agriculture infrastructures such as farms, silos, irrigation systems, greenhouses, etc. impacted by a natural hazard event. Reports the impacts in number of or damage cost of facilities affected.",
        "Power and Energy Production Infrastructure": "Power and energy production infrastructures such as power plants, grids, wind farms, solar farms, etc. impacted by a natural hazard event. Reports the impacts in number of or damage cost of facilities affected.",
        "Crop Production and Forestry": "The impacts on crop production and forestry such as trees, crops, kg of crops, etc. resulting from a natural hazard event. Reports the impacts in number of, kilometer ** 2 of, kilograms of, or damage cost of crops or trees affected.",
        "Affected Livestock and Animals": "The impacts on livestock and animals such as cattles, pigs, sheeps, fishes, etc. impacted by a natural hazard event. Reports the impacts in number of or damage cost of livestock or animals affected.",
        "Economy and Market": "Changes in prices or market instability resulting from a natural hazard event. Reports the impacts in percentage of price changes.",
        "Recreation, Tourism, and Culture": "The impacts on recreation, tourism, and culture such as cultural heritage sites, tourist attractions, etc. resulting from a natural hazard event. Reports the impacts in number of or damage cost of facilities affected.",
        "Access to Healthcare": "People losing access to healthcare resulting from a natural hazard event. Reports the impacts in number of people losing access to healthcare.",
        "Access to transport and Mobility": "People losing access to transport or being stranded resulting from a natural hazard event. Reports the impacts in number of people losing access to transport or being stranded.",
        "Water Quality and Availability": "Changes in the quality and availability of water resulting from a natural hazard event. Reports the impacts in percentage of water quality changes.",
        "Access to Education": "People losing access to education resulting from a natural hazard event. Reports the impacts in number of people losing access to education.",
        "Access to Power and Energy": "People losing access to power or energy resulting from a natural hazard event. Reports the impacts in number of people losing access to power or energy.",
        }

impact_kw_reclass = {
    'Affected People': r"\bAffected People\b",
    'Injured People': r"\bInjured People\b",
    'Displaced People': r"\bDisplaced People\b",
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
    'Informal settlements': r"\bInformal settlements\b",
    'Education Infrastructure': r"\bEducation Infrastructure\b",
    'Power and Energy Production Infrastructure': r"\bPower and Energy Production Infrastructure\b",
    'Agriculture Infrastructure': r"\bAgricultur(?:e|al)? Infras(?:tructure|tucture)\b",

    'Crop Production and Forestry': r"\bCrop Production and Forestry\b",
    'Affected Livestock and Animals': r"\bAffected Livestock and Animals\b",

    'Other Economic and Livelihood Impacts': r"\b(Other Economic(?: Activity)? (?:and|&) Livelihood (?:Production|Impact(?:s)?)|Economy and Market|Livelihood|employment|basic needs)\s*\b",
    'Recreation, Tourism, and Culture': r"\bRecreation, Tourism, and Culture\b",

    'Access to Healthcare': r"\bAccess to Healthcare\b",
    'Access to transport and Mobility': r"\b(Access to transport and Mobility|Access to transport|Mobility)\b",
    'Water Quality and Availability': r"\bWater Quality and Availability\b",
    'Access to Education': r"\bAccess to Education\b",
    'Access to Power and Energy': r"\bAccess to Power and Energy\b",
    'Access to Food': r"\bfood\b",
    'Access to Water, Sanitation, and Hygiene': r"\bAccess to Water,?\s*Sanitation,?\s*and Hygiene\b",

    'Other Infrastructure Impacts': r"\b(Other Infrastructur(?:e|al)? Impacts?)\b",
    'Other Human Impacts': r"\bOther Human.* Impacts?\b",
    'Other Environmental Impacts': r"\bOther Environmental.* Impacts?\b",
    'Other Service Access Impacts': r"\bOther Service Access(?: Impacts?)?\b",
    'Other Agricultural Impacts': r"\bOther Agricultural.* Impacts?\b",
}


