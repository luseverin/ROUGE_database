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

impact_cat_desc_dict = {
    "Human impacts": "The impacts on the human population resulting from the natural hazard event. Look for words such as 'Affected People', 'Injured People', 'Displaced People','Homeless People', 'Missing People', 'Human Deaths'.",
    "Transportation Infrastructure": "The impacts on the transportation infrastructures resulting from the natural hazard event. Look for words such as 'roads', 'bridges', 'railways', and 'highways'.",
    "Water, Sanitation, and Hygiene Infrastructure": "The impacts on the water, sanitation, and hygiene infrastructure resulting from the natural hazard event. Look for words such as 'sewage networks', 'drainage systems', 'wastewater treatment plants', etc.",
    "Healthcare Infrastructure": "The impacts on the healthcare infrastructure resulting from the natural hazard event. Look for words such as 'hospitals', 'healthcare centers', 'pharmacies', 'clinics', etc.",
    "IT and Communication Infrastructure": "The impacts on the IT and communication infrastructure resulting from the natural hazard event. Look for words such as 'data centers', 'communication towers', 'cables', etc.",
    "Residential Buildings": "The impacts on the residential buildings resulting from the natural hazard event.",
    "Informal Settlements": "The impacts on informal settlements resulting from the natural hazard event. Look for words such as 'refugee camps', 'slums', 'tents', etc.",
    "Education Infrastructure": "The impacts on education infrastructure resulting from the natural hazard event. Look for words such as 'schools', 'universities', etc."
}
impact_subtypes_desc_dict = {
        "Affected People": "Individuals impacted by a natural hazard event (the term affected must be mentioned).",
        "Injured People": "People injured, including those hospitalized or admitted (the term injured must be used), to a natural hazard event.",
        "Displaced People": "Individuals temporarily relocated to safer areas due to a natural hazard event.",
        "Homeless People": "Individuals who lost their homes, to a natural hazard event",
        "Missing People": "People unaccounted for following a natural hazard event.",
        "Human Deaths": "Fatalities caused by a natural hazard event."
        }

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
#to use to constraint the units in the user prompt
impactUnit_list_prompting = ["people", "families", "households",
                             "m", "km", "km**2", "kg", "tons",
                             "roads", "km of roads",
                             "railways", "km of railways",
                             "transportation facilities",
                             "Water, sanitation and hygiene facilities",
                             "healthcare facilities",
                             "IT and communication facilities",
                             "residential facilities",
                             "education facilities",
                             "agricultural facilities",
                             "kg of crops",
                             "tons of crops",
                             "km**2 of crops",
                             "livestock heads",
                             "trees"
                             ]
#target units for post proc
impactUnit_list_final = ["people",
                         "km",
                         "km**2",
                         "kg",
                         "roads",
                         "km of roads",
                         "railways",
                         "km of railways",
                         "transportation facilities",
                         "water, sanitation and hygiene facilities",
                         "healthcare facilities",
                         "IT and communication facilities",
                         "residential facilities",
                         "education facilities",
                         "agricultural facilities",
                         "kg of crops",
                         "km**2 of crops",
                         "affected animals",
                         "trees"
                        ]

impactUnitType_list = ["count", "distance", "area", "weight", "volume"]

impact_subtypes_unit_dict = {
        "Affected People": ["people"],
        "Injured People": ["people"],
        "Displaced People": ["people"],
        "Homeless People": ["people"],
        "Missing People": ["people"],
        "Human Deaths": ["people"],
        "Human Health and Wellbeing": ["people", "cases"],
        "Roads" : ["roads", "km of roads", "CHF"],
        "Other transportation infrastructure" : ["transportation facilities", "km of transportation facilities", "CHF"],
        "Water, Sanitation, and Hygiene Infrastructure": ["WASH facilities","CHF"],
        "Healthcare Infrastructure": ["healthcare facilities","CHF"],
        "IT and Communication Infrastructure": ["IT and communication facilities","CHF"],
        "Residential Buildings": ["houses","CHF"],
        "Informal Settlements": ["informal settlements","CHF"],
        "Education Infrastructure": ["education facilities","CHF"],
        "Agricultural Infrastructure": ["agricultural facilities","CHF"],
        "Power and Energy Production Infrastructure": ["power and energy production facilities","CHF"],
        "Crop Production and Forestry": ["kg of crops", "km**2 of crops", "trees", "CHF"],
        "Affected Livestock and Animals": ["affected animals","CHF"],
        "Recreation, Tourism, and Culture": ["recreation, tourisme and culture facilities", "CHF"],
        "Economy and Market": ["CHF"],
        "Access to Healthcare": ["people"],
        "Access to transport and Mobility": ["people"],
        "Water Quality and Availability": ["people", "m**3"],
        "Access to Education": ["people"],
        "Access to Power and Energy": ["people"],
        }

impact_subtypes_desc_quant_dict = {
        "Human impacts": {
            'Affected People': "Total number of individuals impacted by a natural hazard event (the term affected must be mentioned).",
            'Injured People': "Number of people injured, including those hospitalized or admitted (the term injured must be used), to a natural hazard event.",
            'Displaced People': "Number of individuals temporarily relocated to safer areas due to a natural hazard event.",
            'Homeless People': "Number of individuals who lost their homes, to a natural hazard event",
            'Missing People': "Number of people unaccounted for following a natural hazard event.",
            'Human Deaths': "Number of fatalities caused by a natural hazard event."
        },
        "Transportation Infrastructure": {
            "Blocked roads locations" : "The locations where roads have been blocked or traffic is disrupted due to the natural hazard. Write the locations as a tuple (location1, location2).",
            "Blocked roads kilometers" : "The number of kilometers of roads impacted by a natural hazard event.",
            "Airports": "Number of airports or aerodromes impacted by a natural hazard event."
        },
        "Water, Sanitation, and Hygiene Infrastructure": {
            "Impacted WASH infrastructure": "Number of water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a natural hazard event.",
        },
        "Healthcare Infrastructure":{
            "Impacted Healthcare Infrastructure": "Number of healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc. impacted by a natural hazard event.",
        },
        "IT and Communication Infrastructure": {
            "Impacted IT and Communication Infrastructure": "Number of IT and communication infrastructure such as data centers, communication towers, and cables impacted by a natural hazard event.",
        },
        "Residential Buildings":{
            "Impacted Residential Buildings": "Number of residential buildings impacted by a natural hazard event.",
            "Impacted Informal Settlements":"Number of informal settlements such as refugee camps, slums, tents, etc. impacted by a natural hazard event.",
        },
        "Education Infrastructure":{
            "Impacted Education Infrastructure": "Number of education infrastructure such as schools, universities, etc. impacted by a natural hazard event.",
        }
    }


