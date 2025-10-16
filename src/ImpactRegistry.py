class ImpactRegistry:
    def __init__(self):
        # === Core Dictionaries ===
        self.descriptions = {
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

        self.keywords = {
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

        self.expected_units = {
            "Affected People": "people",
            "Injured People": "injuries",
            "Displaced People": "displaced",
            "Homeless People": "homelesses",
            "Missing People": "missings",
            "Human Deaths": "deaths",
            "Residential Buildings": "homes",
            "Informal Settlements": "informal settlements",
            "Education Infrastructure": "education facilities",
            "Human Health and Wellbeing" : "unknown",
            "Infected and Ill People": "cases",
            "Road Infrastructure" : "roads",
            "Other Transportation Infrastructure" : "transportation facilities",
            "Water, Sanitation, and Hygiene Infrastructure": "water, sanitation and hygiene facilities",
            "Healthcare Infrastructure": "healthcare facilities",
            "IT and Communication Infrastructure": "IT and communication facilities",
            "Power and Energy Production Infrastructure" : "power and energy production infrastructure facilities",
            "Agriculture Infrastructure": "agricultural facilities",
            "Affected Livestock and Animals": "affected animals",
            "Recreation, Tourism, and Culture": "unknown",
            "Access to Healthcare": "people",
            "Access to transport and Mobility": "people",
            "Access to Food": "people",
            "Access to Water, Sanitation, and Hygiene": "people",
            "Other Human Impacts": "unknown",
            "Other Infrastructure Impacts": "undefined facilities",
            "Other Agricultural Impacts": "unknown",
            "Other Service Access Impacts": "people",
            'Other Economic and Livelihood Impacts' : "businesses"
        }

        self.default_units = {
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

    # === Accessor Methods ===
    def get_descriptions(self):
        return self.descriptions

    def get_keywords(self):
        return self.keywords

    def get_expected_units(self):
        return self.expected_units

    def get_default_units(self):
        return self.default_units

    # === Utility: Validate all keys are consistent across dicts ===
    def validate_consistency(self, verbose=True):
        dicts = {
            "descriptions": self.descriptions,
            "keywords": self.keywords,
            "expected_units": self.expected_units,
            "default_units": self.default_units,
        }

        all_keys = {name: set(d.keys()) for name, d in dicts.items()}
        base = next(iter(all_keys.values()))
        ok = True

        for name, keys in all_keys.items():
            missing = base - keys
            extra = keys - base
            if missing:
                ok = False
                if verbose:
                    print(f"⚠ {name} is missing: {missing}")
            if extra:
                ok = False
                if verbose:
                    print(f"⚠ {name} has extra keys: {extra}")

        if ok and verbose:
            print("✅ All dictionaries are consistent.")
        return ok

    # === Export All Data in a Unified Structure (optional) ===
    def to_dataframe(self):
        import pandas as pd
        df = pd.DataFrame({
            "description": self.descriptions,
            "keywords": self.keywords,
            "expected_unit": self.expected_units,
            "default_unit": self.default_units,
        })
        return df
