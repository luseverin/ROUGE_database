#multi-level prompting from Tais
def investigates_specific_events(text):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using only information from the text above, answer the query.
    Query: Does the text refer to a report that addresses one or more climate hazard events (i.e. it investigates the consequences of one or more events that happened in specific dates and locations)?
    Answer with 1 or 0. If yes, answer 1. If not, answer 0. Answer with either 1 or 0 and do not add extra text or notes.
    """
    return prompt

#Make sure the event detected with the keyword search actually is there in the text
def check_event_occurrence(text, hazard_type):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using only information from the text above and no previous knowledge, please answer the query.
    Query: Did a {hazard_type} event happened in the area investigated in the report?
    Answer with 1 or 0. If yes, answer 1. If not, answer 0. Answer with either 1 or 0 and do not add extra text or notes.
    """
    return prompt

#Get location
def get_event_location(text, hazard_type):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using only information from the text above and no previous knowledge, please answer the query.
    Query: Where happened the {hazard_type} event investigated in the report?
    For each unique country where the event occurred, extract, if possible:
    "country": Country affected by the {hazard_type} event, mandatory field
    "region": Regions within the country affected by the {hazard_type} event
    "state": States within the country affected by the {hazard_type} event
    "city": Cities within the country affected by the {hazard_type} event
    "locationAnnotation": Provide the text excerpt from where you extracted the location information.
    If any of these information is missing from the text, leave the item empty. Do not add notes or extra text.
    Provide the answer in JSON format.
    Here is an example of how the structure of the JSON must be:
    {str(example_location)}
    """
    return prompt

def get_event_date(text, hazard_type, hazard_location):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using only information from the text above and no previous knowledge, please answer the query.
    Query: When did the {hazard_type} event that affected {hazard_location} investigated in the study happened?
    The date in which the hazard happened should be described by:
    "startYear": starting year, four numeric values "YYYY",
    "startMonth": starting month, one or two numeric values "MM",
    "startDay": starting day, one or two numeric values "DD",
    "endYear": ending year, four numeric values "YYYY",
    "endMonth": ending month, one or two numeric values "MM",
    "endDay": ending day, one or two numeric values "DD",
    "hazardName": If the hazard received a special name, such as "Hurricane Harvey" or "Storm Sandy", add it here, enclosed by double quotes
    Provide the answer in JSON format.
    If information is missing, leave it empty. Do not add notes or extra text.
    Here is an example of how the structure of the JSON must be:
    {str(example_date)}
    """
    return prompt

def get_hazard_subtype(text, hazard_type, hazard_location , hazard_date, subtypes):
    """Find associated hazard subtype from identified main hazard type"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Find the associated hazard subtypes associated with the {hazard_type}
    event that affected {hazard_location} between the {hazard_date} dates.
    Select one or more subtypes from the list {subtypes}.
    Provide the answer in python list format.
    If information is missing, leave it empty. Do not add notes or extra text.
    Here is an example of how the structure of the python list must be:{example_subtypes}
    """
    #If information is missing, leave it empty. Do not add notes or extra text.
    #Here is an example of how the structure of the python list must be: {example_types}
    return prompt

def find_hazard_types(text, hazard_types):
    """Find if hazard events from hazard_types list occured in the report"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using only information from the text above and no previous knowledge, please answer the query.
    Query: Did any hazard event involving one or more hazard types from the list {hazard_types} happened in the area investigated in the report?
    Answer with the list of the hazard types
    Provide the answer in python list format.
    If information is missing, leave it empty. Do not add notes or extra text.
    Here is an example of how the structure of the python list must be: {example_types}
    """
    return prompt

#only one query per hazard location currently; should we do one query per each found subhazard?
def find_impact_types_list(text, hazard_subtypes, hazard_location , hazard_date, impact_types):
    """Find associated impacts from identified hazard subtypes, location, and date.
    Chosing from a list of impact_types"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Find the associated impacts resulting from the {hazard_subtypes}
    event that affected {hazard_location} between the {hazard_date} dates.
    Select one or more subtypes from the list {impact_types}.
    Provide the answer in JSON format.
    If information is missing, leave it empty. Do not add notes or extra text.
    Here is an example of how the structure of the JSON must be:{example_impacts}
    """
    return prompt

def find_impact_types_unconstrained(text, hazard_subtypes, hazard_location , hazard_date):
    """Find associated impacts from identified hazard subtypes, location, and date.
    No constraints on the format."""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: For the {hazard_subtypes} event that affected {hazard_location} between
    the {hazard_date} dates, extract, if possible:
    "Population": The impacts on the population resulting from the event,
    "Infrastructures": The impacts on the infrastructures resulting from the event,
    "impactsAnnotation": Provide the text excerpt from where you extracted the impacts information.
    Provide the answer in JSON format.
    If information is missing, leave it empty. Do not add notes or extra text.
    Here is an example of how the structure of the JSON must be:{example_impacts}
    """
    return prompt

def find_impact_types_categories(text, hazard_subtypes, hazard_location , hazard_date, impact_cat):
    """Find associated impacts from identified hazard subtypes, location, and date.
    Try to identify impacts from different categories."""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: For the {hazard_subtypes} event that affected {hazard_location} between
    the {hazard_date} dates, extract, identify if the following type of impact occured:
    {impact_cat}
    Answer with 1 or 0. If yes, answer 1. If not, answer 0.
    Answer with either 1 or 0 and do not add extra text or notes.
    """
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
