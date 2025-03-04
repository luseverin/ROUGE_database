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
    If end year, end month, and end day are not mentioned in the text, repeat the values for start year, start month, and start day.
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
def find_impact_types(text, hazard_subtypes, hazard_location , hazard_date, impact_types):
    """Find associated impacts from identified hazard subtypes, location, and date"""
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

def find_impact_types2(text, hazard_subtypes, hazard_location , hazard_date):
    """Find associated impacts from identified hazard subtypes, location, and date"""
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
     "Population" : "[affected, displaced]"
     "Infrastructures" : "[roads, bridges]",
     "impactsAnnotation :""
     }
    ]
    }"""