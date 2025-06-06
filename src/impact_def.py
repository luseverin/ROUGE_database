#Constants for impact definition


impactType_list = ["Human", "Infrastructure", "Agriculture", "Economy"]

impactSubtype_list = ["Affected People", "Injured People", "Displaced People", "Homeless People", "Missing People", "Human Deaths", #"Affected Families and Households"
                      "Transportation Infrastructure", "Water, Sanitation, and Hygiene Infrastructure", "Healthcare Infrastructure",
                      "IT and Communication Infrastructure", "Residential Buildings", "Informal settlements", "Education Infrastructure",
                      "Crop Production", "Affected Livestock", "Economic Losses", "Agriculture Infrastructure", "Water Quality and Availability",
                      "Health Impacts"]

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
        "Human Deaths": "Fatalities caused by a natural hazard event.",
        "Transportation Infrastructure": "The impacts on the transportation infrastructures resulting from the natural hazard event.",
        #"Blocked roads" : "Roads blocked or disrupted traffic due to a  natural hazard. event.",
        #"Airports": "Airports or aerodromes impacted by a natural hazard event.",
        "Water, Sanitation, and Hygiene Infrastructure": "Water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a natural hazard event.",
        "Healthcare Infrastructure": "Healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc. impacted by a natural hazard event.",
        "IT and Communication Infrastructure": "IT and communication infrastructure such as data centers, communication towers, and cables impacted by a natural hazard event.",
        "Residential Buildings": "Residential buildings impacted by a natural hazard event.",
        "Informal Settlements":"Informal settlements such as refugee camps, slums, tents, etc. impacted by a natural hazard event.",
        "Education Infrastructure": "Education infrastructure such as schools, universities, etc. impacted by a natural hazard event.",
        "Agriculture": "The impacts on the agriculture such as land, crops, livestock resulting from a natural hazard event.",
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
                                   "livestock heads",
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
        "Blocked roads" : ["km", "nb."],
        "Airports": ["nb."],
        "WASH infrastructure": ["nb."],
        "Healthcare Infrastructure": ["nb."],
        "IT and Communication Infrastructure": ["nb."],
        "Residential Buildings": ["nb."],
        "Informal Settlements": ["nb."],
        "Education Infrastructure": ["nb."],
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


