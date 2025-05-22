#Prompts for impact extraction
def make_prompt_system(impact_types, hazard_types):
    prompt_system = f"""
    You are an assistant that analyzes impacts. You must output results strictly in the following JSON format:

    [
        {{
            "impactType": "<one of {impact_types}>",
            "impactValue": <integer or null>,
            "impactUnit": "<string or null>",
            "location": ["<list of strings>"],
            "startYear": <integer or null>,
            "startMonth": <integer or null>,
            "startDay": <integer or null>,
            "endYear": <integer or null>,
            "endMonth": <integer or null>,
            "endDay": <integer or null>,
            "hazards": ["<one or more of {hazard_types}>"],
            "impactsAnnotation": ["<list of strings>"]
        }}
    ]

    Rules:
    1. The `impactType` field must only contain one of the valid values: {impact_types}.
    2. The `hazards` field must only contain values from {hazard_types}.
    3. Adhere to the JSON format strictly; no extra fields are allowed.
    """
    return prompt_system

def find_impact_types_categories(text, impact_cat, impact_desc):
    """Try to identify impacts from different categories. Based on impact categories
    dict"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Based on the following description of the impact type {impact_cat}  "{impact_cat}": {impact_desc},
    identify if an impact of the type {impact_cat} occurred in the report area described in the text above.

    Answer with 1 or 0. If yes, answer 1. If not, answer 0.
    Answer with either 1 or 0 and do not add extra text or notes.
    """
    return prompt

def make_impact_cat_prompt(impact_subType_dict):

    try:
        prompt_impquant = """\n""".join([impact_subType_dict[imptype] for imptype in impact_types])
    except ValueError as e:
        print(e)
        prompt_impquant = None
    return prompt_impquant

def quantify_impacts_value_loc_date_haz(text, impact_type, impact_type_desc):
    """Find associated impacts from different impactTypes identified.
    Try to quantify numerically impacts from different categories."""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: For the type of impact {impact_type}, described as follow: {impact_type_desc}, extract from the above text
    all descriptions and mentions of this specific impact, including:
    "impactValue"       : The quantified value of the described impact. If no quantified value can be identified, write null,
    "impactUnit         : The unit of the quantified impact value. If no unit can be identified, write null.
    "location"          : The locations for which the impact value is described. If no location can be identified, write null.
                          If multiple locations are described, write them in a python list format [location1, location2],

    "startYear"    : The year during which the described impact is thought to have started.
                          If you cannot find this information write null.
    "startMonth"  : The month during which the described impact is thought to have started.
                          If you cannot find this information write null.
    "startDay"    : The day at which the described impact is thought to have started.
                          If you cannot find this information write null.
    "endYear"    : The year during which the described impact is thought to have ended.
                          If you cannot find this information write null.
    "endMonth"  : The month during which the described impact is thought to have ended.
                          If you cannot find this information write null.
    "endDay"    : The day at which the described impact is thought to have ended.
                          If you cannot find this information write null.
    "hazards"           : The natural hazards that are thought to have caused the described impacts.
                          If no hazard can be identified, write null, if more than one natural hazard can be identified,
                          write the hazards in a python list format [hazard1, hazard2]. Chose from the list {hazard_all_subtype_emdat}.
                          Do not include hazard types that are not from the list. Write the hazard exactly as they are written in the list.
    "impactsAnnotation" : Provide the text excerpt from where you extracted the impacts information.

    If information is missing, leave it empty.
    Do not reuse or count the same impactValue twice.
    For numerical values, use integers; do not use commas (e.g., 1000 instead of 1,000),
    sum ranges if multiple are provided for the same impact, convert million or mi to six zeros (10^6), billion or bi to nine zeros (10^9).
    If only the number of affected households or houses is given, assume each unit equals three people.
    Provide the answer as a list of JSON i.e. [JSON1, JSON2].
    Do not add notes or extra text, only output the list of JSONs, without saying "here is the list of JSONs".
    Here is an example of how the structure of the list of JSONs must be:""" + \
    """[{
       "impactValue": 10000,
       "impactUnit": "people",
        "location" : ["Abu Hamad", "Tokar"],
        "startYear" : "2024",
        "startMonth" : "08",
        "startDay" : "29",
        "endYear" : "null",
        "endMonth" : "null",
        "endDay" : "null",
        "hazards" : ["flash flood"],
        "impactAnnotation" : ["Flash floods impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024",]
      },
      {
       "impactValue": 100002,
       "impactUnit": "people",
        "location" : ["Red Sea State"],
        "startYear" : "2024",
        "startMonth" : "08",
        "startDay" : "null",
        "endYear" : "2024",
        "endMonth" : "10",
        "endDay" : "null",
        "hazards" : ["flash flood"],
        "impactAnnotation" : ["Flash floods impacted 100002 people in Red Sea State between August to October 2024",]
      },
      {
          "impactValue": 4,
          "impactUnit": "hospitals",
          "location": ["River Nile State"],
          "startYear": "null",
          "startMonth": "null",
          "startDay": "null",
          "endYear": "null",
          "endMonth": "null",
          "endDay": "null",
          "hazards" : "null",
          "impactAnnotation" : ["At least 4 hospitals have been impacted in River Nile State alone."]
          }]

    """
    #Here is an example of how the structure of the list of JSONs must be:{example_impacts_quant_value_loc_date_haz}
    return prompt


def make_impact_cat_prompt(impact_types):
    prompt_impact_dict = {
        "Human impacts":
        "'Affected People': Total number of individuals impacted by the hazard event (the term affected must be mentioned)."\
        "'Injured People': Number of people injured, including those hospitalized or admitted (the term injured must be used)."\
        "'Displaced People': Number of individuals temporarily relocated to safer areas due to the event."\
        "'Homeless People': Number of individuals who lost their homes."\
        "'Missing People': Number of people unaccounted for following the event."\
        "'Human Deaths': Number of fatalities caused by the hazard.",
        "Transportation Infrastructure": "'Transportation Infrastructure': Location of transportation infrastructure such as roads, bridges, railways, and highways impacted by a hazard. If you identify impacts but the location of the impacts is unknown, write “Location unknown”. Write the different locations in a python list format.",
        "Water, Sanitation, and Hygiene Infrastructure": "'Water Sanitation and Hygiene Infrastructure: Number of water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a hazard.",
        "Healthcare Infrastructure":"'Healthcare Infrastructure': Number of healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc.  impacted by a hazard.",
        "IT and Communication Infrastructure":"'IT and Communication Infrastructure': Number of IT and communication infrastructure  such as data centers, communication towers, and cables impacted by a hazard.",
        "Residential Buildings":"'Residential Buildings': Number of residential buildings impacted by a hazard.",
        "Informal Settlements":"'Informal Settlements': Number of informal settlements such as refugee camps, slums, tents, etc. impacted by a hazard.",
        "Education Infrastructure":"'Education Infrastructure': Number of education infrastructure such as schools, universities, etc. impacted by a hazard.",
    }
    try:
        prompt_impquant = """\n""".join([prompt_impact_dict[imptype] for imptype in impact_types])
    except ValueError as e:
        print(e)
        prompt_impquant = None
    return prompt_impquant

def quantify_impacts(text, hazard_subtypes, hazard_location , hazard_date, impact_types):
    """Find associated impacts from identified hazard subtypes, location, and date.
    Try to quantify numerically impacts from different categories."""
    impact_types_prompt = make_impact_cat_prompt(impact_types)
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: For the {hazard_subtypes} event that affected {hazard_location} between
    the {hazard_date} dates, extract, if possible information on the following type of  categories:
    {impact_types_prompt}
    impactsAnnotation": Provide the text excerpt from where you extracted the impacts information.
    If information is missing, leave it empty. Do not add notes or extra text.
    General Instructions for Numerical Values: use integers; do not use commas (e.g., 1000 instead of 1,000),
    sum ranges if multiple are provided for the same impact, convert million or mi to six zeros (10^6), billion or bi to nine zeros (10^9).
    If only the number of affected households or houses is given, assume each unit equals three people.
    If an impact for an impact category can be identified but not quantified with a numerical value, write "True".
    Provide the answer in JSON format.
    Here is an example of how the structure of the JSON must be:{example_impacts_quant}
    """
    return prompt


example_location =     """ {"hazardLocation": [
    {
      "country": "Brazil",
      "region": "",
      "state": "Ceará",
      "city": "Fortaleza, Bela Cruz",
      "locationAnnotation": ""
     },
    {
      "country": "United States",
      "region": "",
      "state": "California, Arizona",
      "city": "",
      "locationAnnotation": ""
     },
     {
      "country": "Colombia",
      "region": "",
      "state": "",
      "city": "",
      "locationAnnotation": ""
     }
     ]
     }
    """
example_date =     """{"hazardDate": [
    {
      "startYear": "2017",
      "startMonth": "8",
      "startDay": "30",
      "endYear": "2017",
      "endMonth": "9",
      "endDay": "13",
      "hazardName": "Hurricane Irma"
     },
     {
      "startYear": "2017",
      "startMonth": "9",
      "startDay": "16",
      "endYear": "2017",
      "endMonth": "9",
      "endDay": "30",
      "hazardName": "Hurricane Maria"
     }
     ]
     }
    """

example_subtypes = """["tornado", "lightning", "hail"]"""

example_impacts = """{"impactSubtypes": [
    {
     "Population" : "[affected, displaced]",
     "Infrastructures" : "[roads, bridges]",
     "impactsAnnotation :""
     }
    ]
    }"""

example_impact_types = """["Healthcare Infrastructure", "Education Infrastructure"]"""

example_impacts_quant =     """{"impactSubtypes": [
    {
      "Affected People": "10000",
      "Injured People": "2500",
      "Displaced People": "9000",
      "Homeless People": "True",
      "Missing People": True,
      "Human Deaths": "2",
      "Transportation Infrastructure": ["Abu Ahmad", "Port Sudan"]
      "Water Sanitation and Hygiene Infrastructure": "True",
      "Healthcare Infrastructure": 4,
      "IT and Communication Infrastructure": "True",
      "Residential Buildings": "1000",
      "Informal Settlements": "True",
      "Education Infrastructure": "1",
      "impactsAnnotation :""
     }
     ]
     }
    """
