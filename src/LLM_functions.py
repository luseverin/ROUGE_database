#Functions to extract data with LLMs
import pandas as pd
import json as json
import re
from copy import deepcopy
from itertools import chain
from langchain_groq import ChatGroq
import instructor
from src.hazard_def import *
from src.impact_def import *
from src.data import *
from src.prompts_hazards import *
from src.prompts_impacts import *
from src.client import CLIENT, MODEL_NAME
from src.classOutput import ImpactList

def extract_outer_json(text):
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        return None  # Return None for empty JSON or invalid format

    extracted_json = text[start_index:end_index + 1]
    return extracted_json

def get_model_response(CLIENT, MODEL, prompt, kwargs={}):

  completion = CLIENT.chat.completions.create(
    model=MODEL,
    messages=[
      {"role": "user", "content": prompt}
    ],
    temperature=0,
    **kwargs
  )

  return completion.choices[0].message.content

def get_model_response_v2(CLIENT, MODEL, prompt):

  """Get model response structured using Groq API"""

  chat = ChatGroq(
    temperature=0,
    model=MODEL,
    api_key="os.getenv("GROQ_API_KEY")" # Optional if not set as an environment variable
    )
  structured_llm = chat.with_structured_output(ImpactList, include_raw=True)
  response = structured_llm.invoke(prompt)
  return response

def get_model_response_v3(CLIENT, MODEL, prompt, kwargs={}):
   """Get model response structured using OpenAI API"""
   prompt_system = """
    You are an assistant that analyzes impacts. Use the following function to structure your response:

    Function: ImpactList
    Parameters: {"impacts": [{impactValue: int, impactUnit: str, location : list, startYear : int, startMonth : int, startDay : int, endYear : int, endMonth : int, endDay : int, hazards : list, impactAnnotation : list}]}

    Analyze the impacts and return results in the above format.
    """
   try:
      completion = CLIENT.chat.completions.create(
           model=MODEL,
           messages=[
                     {"role": "system", "content": prompt_system},
                     {"role": "user", "content": prompt}
                     ],
            temperature=0,
            response_model = ImpactList
            )
   except instructor.exceptions.InstructorRetryException as e:
       print(e)
   return completion.choices[0].message.content

def add_key_value_pairs(data, new_pairs):
    """
    Adds new key-value pairs to each dictionary in a list of dictionaries.

    Parameters:
    data (list): A list of dictionaries.
    new_pairs (list or dict): A dictionary or list of dictionaries containing key-value pairs to be added.

    Returns:
    list: A list of dictionaries with the new key-value pairs added.
    """
    if isinstance(new_pairs, dict):
        # If new_pairs is a dictionary, add its key-value pairs to each dictionary in data
        for entry in data:
            for key, value in new_pairs.items():
                entry[key] = value
    elif isinstance(new_pairs, list):
        # If new_pairs is a list, add the corresponding dictionary's key-value pairs to the corresponding dictionary in data
        for entry, new_pair in zip(data, new_pairs):
            if isinstance(new_pair, dict):
                for key, value in new_pair.items():
                    entry[key] = value
    else:
        raise TypeError("new_pairs must be a dictionary or a list of dictionaries")

    return data

def check_result_json(result_json, label=None):
    try:
        answer = json.loads(result_json.replace("\n", ""))
        if label:
            answer = answer[label]
    except Exception as e:
        print("An unexpected error occurred:", e)
        return None
    if not answer:
        print("JSON is empty:", result_json)
    return answer

def identify_hazards(text, hazards_to_check):
    hazards_identified = []
    for hazard in hazards_to_check:
        #test for event occurence
        prompt = check_event_occurrence(text, hazard)
        result = get_model_response(CLIENT, MODEL_NAME, prompt)
        hazard_occurrence = int(''.join(re.findall("[01]", result)))
        if hazard_occurrence == 1:
            hazards_identified.append(hazard)
            print(f"{hazard} occurred in the report area.")
    return hazards_identified

def check_location(location_text):
    # Check if 'country' key exists and has a value
    if ("country" in location_text and location_text["country"]):
        location_country = location_text["country"]
        print("Location: ", location_country)
    else:
        print("Country not specified or missing:", location_text)
        return None
    # Check if 'city' key exists and has a value
    if ("city" in location_text and location_text["city"]) or ("state" in location_text and location_text["state"]):
        if location_text["city"] and location_text["state"]:
            location_complete = f"{location_country}, {location_text['state']}, {location_text['city']}"
        elif location_text["state"]:
            location_complete = f"{location_country}, {location_text['state']}"
        elif location_text["city"]:
            location_complete = f"{location_country}, {location_text['city']}"
        print("Location found: ", location_complete)
    else:
        print("City/State not specified or missing:", location_text)
        location_complete = f"{location_country}"
    return location_complete

def identify_locations(text, hazard):
    identified_locations = {}
    prompt = get_event_location(text, hazard)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    result_json = extract_outer_json(result)
    answer_location = check_result_json(result_json, "hazardLocation")
    if len(answer_location) == 1:
        location_complete = check_location(answer_location[0])
        if location_complete:
            identified_locations[location_complete] = answer_location[0]
    if len(answer_location) >= 1:
        for location in answer_location:
            location_complete = check_location(location)
            if location_complete:
                identified_locations[location_complete] = location
    return identified_locations

def identify_dates(text, hazard, location_complete):
    prompt = get_event_date(text, hazard, location_complete)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    result_json = extract_outer_json(result)
    answer_date = check_result_json(result_json, "hazardDate")
    return answer_date

def identify_subtypes(text, hazard, location_complete, answer_date):
    subtypes = maintype_to_subytpe_emdat[hazard]
    hazard_date = deepcopy(answer_date)
    if hazard_date and "hazardName" in hazard_date[0]:
        del hazard_date[0]["hazardName"]
    prompt = get_hazard_subtype(text, hazard, location_complete, hazard_date, subtypes)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    #result_json = extract_outer_json(result)
    #answer_subtypes = check_result_json(result_json, "hazardSubtypes")
    return result

def identify_impacts_simple(text, hazard_subtypes, location_complete , hazard_date):
    """simple first version of impact data extraction"""
    prompt = find_impact_types_unconstrained(text, hazard_subtypes, location_complete , hazard_date)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    result_json = extract_outer_json(result)
    answer_subtypes = check_result_json(result_json, "impactSubtypes")
    return answer_subtypes

def identify_impacts_cat(text, impcat_to_check):
    """Identify categories of impacts"""
    impcat_identified = []
    for impcat, imp_description in impcat_to_check.items():
        #test for event occurence
        prompt = find_impact_types_categories(text, impcat, imp_description)
        result = get_model_response(CLIENT, MODEL_NAME, prompt)
        impcat_occurrence = int("".join(re.findall("[01]", result)))
        if impcat_occurrence == 1:
            impcat_identified.append(impcat)
            print(f"{impcat} identified in the report area.")
    return impcat_identified

def identify_impacts_quant(text, impact_types):
    """Quantify impacts from identified impact categories"""
    prompt = quantify_impacts(text, impact_types)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    result_json = extract_outer_json(result)
    answer_subtypes = check_result_json(result_json, "impactSubtypes")
    return answer_subtypes

def get_event_information(df_labelled, guess_hazard_types=True, guess_subtypes=True, guess_impacts_simple=False,
                          guess_impacts_quant=False):
    """Wrapper function to do all level promptings. Calls seaprate subfunctions per
    each level:
        Check if any hazard -> investigates_specific_events
        Check specific hazard -> identify_hazards
        Check event location -> get_event_location
        Check event date -> get_event_date
        Check event subtypes -> get_hazard_subtype
        Check event impacts -> find_impact_types

    """
    response = []
    count = 0
    for rowid, row in df_labelled.iterrows():

        reference_info = {
            "appealCode": row["appealCode"],
            "location": row["location"],
            "reportDate" : row["reportDate"],
            "disasterType": row["disasterType"]
        }

        text = row["nathaz_text"]

        #ask LLM to identify main haz types from list
        if guess_hazard_types:
            hazards_to_check = list(maintype_to_subytpe_emdat.keys())

        #just check that LLM can identify hazard identified with keyword search
        else:
            hazards_to_check = row['hazards_found']

        #test if a hazard occured, maybe unnecessary step?
        prompt = investigates_specific_events(text)
        result = get_model_response(CLIENT, MODEL_NAME, prompt)
        specific_event = int(''.join(re.findall("[01]", result)))

        if not specific_event:
            print(f"No hazard event identified in {reference_info['appealCode']}, {reference_info['reportDate']}")
            continue

        #identify hazards
        hazards_identified = identify_hazards(text, hazards_to_check)
        for hazard in hazards_identified:
            #add data entry with hazard and reference info
            data = add_key_value_pairs([reference_info], {"hazardType": hazard})

            #identify locations
            locations_identified = identify_locations(text, hazard)
            #loop over identified locations
            for location_complete, location in locations_identified.items():

                #add location to data
                updated_data = deepcopy(add_key_value_pairs(data, location))

                #try to identify dates
                ##!assumes only one date per event-location
                answer_date = identify_dates(text, hazard, location_complete)
                if answer_date:
                    updated_data = deepcopy(add_key_value_pairs(updated_data, answer_date))

                if guess_subtypes:
                    answer_subtypes = identify_subtypes(text, hazard, location_complete, answer_date)
                    if answer_subtypes:
                        updated_data = deepcopy(add_key_value_pairs(updated_data, {"hazardSubtypes":answer_subtypes}))

                if guess_impacts_simple:
                    #for impact_cat, impact_types in impact_types_dict.items():
                    #    answer_impacts = identify_impacts(text, answer_subtypes, location_complete , answer_date, impact_types)
                    #    if answer_impacts:
                    #        updated_data = deepcopy(add_key_value_pairs(updated_data, {impact_cat:answer_impacts}))
                    answer_impacts = identify_impacts_simple(text, answer_subtypes, location_complete , answer_date)
                    if answer_impacts:
                        updated_data = deepcopy(add_key_value_pairs(updated_data,answer_impacts))
                elif guess_impacts_quant:
                    answer_impacts_cat = identify_impacts_cat(text, answer_subtypes, location_complete , answer_date, impact_cat_desc_dict)
                    if answer_impacts_cat:
                        updated_data = deepcopy(add_key_value_pairs(updated_data, {"impactTypes":answer_impacts_cat}))
                        #answer_impacts_cat = json.loads(answer_impacts_cat) #convert to list
                        answer_impacts_quant = identify_impacts_quant(text, answer_subtypes, location_complete , answer_date, answer_impacts_cat)
                        if answer_impacts_quant:
                            updated_data = deepcopy(add_key_value_pairs(updated_data, answer_impacts_quant))


                #updated_data = deepcopy(add_key_value_pairs(updated_data, reference_info))
                response.append(deepcopy(updated_data))




    response_unnested = list(chain(*response))
    response_df = pd.DataFrame(response_unnested)
    return(response, response_df)

def get_event_impacts_v1(df_labelled, res_savename):
    """Wrapper function to do all level promptings for impact extraction
    Version 1 doing a separate identification of impact

    """
    response = []
    response_df_list = []
    count = 0
    for rowid, row in df_labelled.iterrows():

        reference_info = {
            "appealCode": row["appealCode"],
            "location": row["location"],
            "reportDate" : row["reportDate"],
            "disasterType": row["disasterType"]
        }

        text = row["nathaz_text"]

        #first identify impact main types or subtypes directly
        answer_impacts_cat = identify_impacts_cat(text, impact_subtypes_desc_dict)#impact_cat_desc_dict, impact_subtypes_desc_dict

        if len(answer_impacts_cat):
            print(f"Impacts {answer_impacts_cat} identified in {reference_info['appealCode']}, {reference_info['reportDate']}")
        else:
            print(f"No impacts identified in {reference_info['appealCode']}, {reference_info['reportDate']}")
            pass

        for impcat in answer_impacts_cat:

            #query impact, value, loc, date haz altogether
            impdesc = impact_subtypes_desc_dict[impcat]
            prompt = quantify_impacts_value_loc_date_haz(text, impcat, impdesc)
            #prompt = "List impacts with their location, value, and date in JSON format from the text below:\n" \
            #"Flood damage occured in Abu Hamad and Tokar on 29 August 2024. 10000 people were impacted. Other impacts occured"
            result = get_model_response(CLIENT, MODEL_NAME, prompt)
            answer_impacts = check_result_json(result)

            if answer_impacts:
                data = add_key_value_pairs([reference_info], {"impactType": impcat})
                updated_data = deepcopy(add_key_value_pairs(data, answer_impacts))
                response.append(updated_data)

        response_unnested = list(chain(*response))
        response_df_list.append(pd.DataFrame(response_unnested))
        all_response_df = pd.concat(response_df_list, ignore_index=True, axis=0)
        all_response_df.to_csv(DATA_OUT_LLMS + res_savename, index=False)

    return (response, all_response_df)