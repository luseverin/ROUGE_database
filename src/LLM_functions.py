#Functions to process data using LLMs
import pandas as pd
import json as json
import re
from copy import deepcopy
from itertools import chain
from src.constants import *
from src.prompts import *
from src.client import CLIENT, MODEL_NAME

def extract_outer_json(text):
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        return None  # Return None for empty JSON or invalid format

    extracted_json = text[start_index:end_index + 1]
    return extracted_json

def get_model_response(CLIENT, MODEL, prompt):
  completion = CLIENT.chat.completions.create(
    model=MODEL,
    messages=[
      {"role": "user", "content": prompt}
    ],
    temperature=0
  )

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

def check_result_json(result_json, label):
    try:
        answer = json.loads(result_json.replace("\n", ""))[label]
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
    if hazard_date:
        del hazard_date[0]["hazardName"]
    prompt = get_hazard_subtype(text, hazard, location_complete, hazard_date, subtypes)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    #result_json = extract_outer_json(result)
    #answer_subtypes = check_result_json(result_json, "hazardSubtypes")
    return result

def identify_impacts(text, hazard_subtypes, location_complete , hazard_date):
    prompt = find_impact_types2(text, hazard_subtypes, location_complete , hazard_date)
    result = get_model_response(CLIENT, MODEL_NAME, prompt)
    result_json = extract_outer_json(result)
    answer_subtypes = check_result_json(result_json, "impactSubtypes")
    return answer_subtypes

def get_event_information(df_labelled, guess_hazard_types=True, guess_subtypes=True, guess_impacts=False):
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
            print(f"No hazard event identified in{row.index}")
            continue

        #identify hazards
        hazards_identified = identify_hazards(text, hazards_to_check)
        for hazard in hazards_identified:
            locations_identified = identify_locations(text, hazard)

            for location_complete, location in locations_identified.items():

                #add data entry
                data = add_key_value_pairs([{"hazardType": hazard}], location)

                #try to identify dates
                ##!assumes only one date per event-location
                answer_date = identify_dates(text, hazard, location_complete)
                if answer_date:
                    updated_data = deepcopy(add_key_value_pairs(data, answer_date))

                if guess_subtypes:
                    answer_subtypes = identify_subtypes(text, hazard, location_complete, answer_date)
                    if answer_subtypes:
                        updated_data = deepcopy(add_key_value_pairs(updated_data, {"hazardSubtypes":answer_subtypes}))

                if guess_impacts:
                    #for impact_cat, impact_types in impact_types_dict.items():
                    #    answer_impacts = identify_impacts(text, answer_subtypes, location_complete , answer_date, impact_types)
                    #    if answer_impacts:
                    #        updated_data = deepcopy(add_key_value_pairs(updated_data, {impact_cat:answer_impacts}))
                    answer_impacts = identify_impacts(text, answer_subtypes, location_complete , answer_date)
                    if answer_impacts:
                        updated_data = deepcopy(add_key_value_pairs(updated_data,answer_impacts))
                updated_data = deepcopy(add_key_value_pairs(updated_data, reference_info))
                response.append(deepcopy(updated_data))




    response_unnested = list(chain(*response))
    response_df = pd.DataFrame(response_unnested)
    return(response, response_df)