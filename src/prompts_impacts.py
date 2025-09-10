import pandas as pd
from src.prompt_examples import *
from src.impact_def import *
#Prompts for impact extraction
def identify_impacts_prompt(text, impact_desc):
    """Try to identify impacts from different categories. Based on impact categories
    dict"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Identify subtypes of impacts that occurred in the report area described in the text above, only
    accounting for subtypes described below:
    {format_desc(impact_desc)}
    Answer as a JSON in the following format and respecting the rules described after:
    JSON format:
    {{
    "impactSubtypes": ["<one or more of {list(impact_desc.keys())}>" or null],  # Description: The list of subtypes of impact (e.g., Affected People, Road Infrastructure, Crop Production and Forestry).
    }}

    Rules
    - Only include impact subtypes that are in the following list: {list(impact_desc.keys())}.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the JSON.

    Example output:
    {examples_subtypes}
    """
    return prompt

def identify_value_unit_prompt(text, answer):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Based on the list of types of impacts that you previously identified:
    {answer}
    identify the values and units of these impacts from the text above.
    Answer by providing a list of JSONs, in the following format and respecting the rules described after:
    List of JSON format:
    [
    {{
    "impactSubtype": "<one of {answer}>",  # Description: Subtype of impact (e.g., Affected People, Road Infrastructure, Crop Production and Forestry).
    "impactValue": <float or null>  # Description: The quantified value of the impact. Provide the exact number if mentioned. If a range is provided give the upper estimate. Use null if unknown.
    "impactValuePrecision": "one of ["exact", "approx"], # Description: The flag describing whether the quantified impact value is exact or approximate. Use null if unknown.
    "impactValueMin": <float or null>,  # Description: The lower bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
    "impactValueMax": <float or null>,  # Description: The upper bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
    "impactUnit": "<string>" or null,  # Description: The unit of the impact value (e.g., people, meters, houses). Use null if unknown.
    "valueAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the impacts information. Write the text exactly as found in the original text.
    }}
    ]

    Rules:
    - The `impactSubtype` field must only contain one of the valid values: {answer}.
    - Do not reuse a specific impactValue for different entries.
    - Provide the exact text excerpt from where you extracted the impacts information in the `valueAnnotation` field. Write the text exactly as found in the original text. Provide the entire sentences.
    - Extract each mention of an impact only once. Do not repeat yourself.
    - Provide the unit of the impact in the `impactUnit` field exactly as found in the original text, keeping all information on the measured quantity (e.g. write 'km of roads' instead of just 'km')
    - When multiple numbers are provided favour the `impactValue` associated with `impactUnit` in terms of "people" over "households", and "CHF" over other currencies
    - When the `impactValue` field is an exact number, `impactValuePrecision` must be set to `exact`.
    - When the `impactValue` field is an approximation, `impactValuePrecision` must be set to `approx`.
    - When the `impactValue` field is a range, `impactValuePrecision` must be set to `approx` and the `impactValueMin` and `impactValueMax` fields must be filled.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the list of JSONs.

    Example output:
    {examples_value_unit}
    """
    return prompt

def make_impact_description(impact_type, impact_value, impact_unit):
    if ((impact_value is not None) or
        (not pd.isna(impact_value) or
        (impact_unit is not None) or
        (not pd.isna(impact_unit)))):
        return f"the impact of type '{impact_type}' with a value of {impact_value} {impact_unit}"
    else:
        return f"impacts of type '{impact_type}'"

def identify_impact_loc_prompt(text, impact_description):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Identify the locations where {impact_description} occurred in the report area described in the text above.
    Answer as a JSON in the following format and respecting the rules described after:
    JSON format:
    {{
    "country": ["<list of strings>"],  # Description: The list of affected countries where the described impact occurred.
    "location" : ["<list of strings>"] or null,  # Description: The list of affected locations at the subnational level (e.g. cities, regions) where the described impact occurred.
    "locationAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the location information. Write the text exactly as found in the original text.
    }}

    Rules:
    - Provide the the most precise level of location found for the described impact in the `city field`.
    - Give the location names exactly as written in the text. Do not aggregate different locations in words such as "varions locations" but provide the list of names.
    - Follow the JSON format strictly; do not add or remove fields.
    - Provide the exact text excerpt from where you extracted the location information in the `locationAnnotation` field. Write the text exactly as found in the original text. Provide the entire sentences.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the JSON.

    Example output:
    {examples_location}
    """
    return prompt

def identify_impact_dates_prompt(text, impact_description, locations):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Identify the dates when {impact_description} occurred at {locations} in the report area described in the text above.
    Answer as a JSON in the following format and respecting the rules described after:
    JSON format:
    {{
    "startYear": <integer or null>,  # Description: The year when the impact started. Use null if unknown.
    "startMonth": <integer or null>,  # Description: The month when the impact started. Use null if unknown.
    "startDay": <integer or null>,  # Description: The day when the impact started. Use null if unknown.
    "endYear": <integer or null>,  # Description: The year when the impact ended. Use null if ongoing or unknown.
    "endMonth": <integer or null>,  # Description: The month when the impact ended. Use null if ongoing or unknown.
    "endDay": <integer or null>,  # Description: The day when the impact ended. Use null if ongoing or unknown.
    "dateAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the date information. Write the text exactly as found in the original text.
    }}

    Rules:
    - Follow the JSON format strictly; do not add or remove fields.
    - Provide the exact text excerpt from where you extracted the date information in the `dateAnnotation` field. Write the text exactly as found in the original text. Provide the entire sentences.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the JSON.

    Example output:
    {examples_date}
    """
    return prompt

def identify_impact_hazards_prompt(text, impact_description, locations, dates, hazards_list):
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Identify the hazards that caused {impact_description} at {locations} at {dates} in the report area described in the text above.
    Answer as a JSON in the following format and respecting the rules described after:
    JSON format:
    {{
    "hazards": ["<one or more of {hazards_list}>" or null],  # Description: List of hazards causing the impact (e.g., Tropical storm, Drought, Flood).
    "hazardsAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the hazard information. Write the text exactly as found in the original text. Provide the entire sentences.
    }}
    Rules:
    - The `hazards` field must only contain values from {hazards_list}.
    - Provide the exact text excerpt from where you extracted the hazard information in the `hazardsAnnotation` field. Write the text exactly as found in the original text.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the JSON.

    Example output:
    {example_hazards}
    """
    return prompt

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

#try new formulation with formatting
def quantify_impacts_type_value_loc_date_haz_const_unit(imp_main, imp_sub, imp_unit, hazard_cat):
    """Find impact type, values, locs, etc. altogether"""
    prompt = f"""
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Extract from the above text all descriptions and mentions of impacts resulting from extreme
    natural hazard events. Answer by providing a list of JSONs, following strictly the instructructions
    on the fields to extract and the structure of the output below:
    [
    {{
        "impactType": "<one of {imp_main}>",  # Description: Main type of impact (e.g., Human, Agriculture, Infrastructure).
        "impactSubtype": "<one of {imp_sub}>",  # Description: Subtype of impact (e.g., Affected People, Crop Production, WASH Infrastructure).
        "impactValue": <integer or null>,  # Description: The quantified value of the impact. Use null if unknown.
        "impactUnit": "<one of {imp_unit}>",  # Description: The unit of the impact value (e.g., people, kilometers, houses).
        "impactValueFlag": "one of ["exact", "approx"], # Description: The quality flag for the quantified impact value informing on the confidence in the quantified value.
        "country": "<string>",  # Description: The country where the impact occurred.
        "location": ["<list of strings>" or null],  # Description: A list of affected locations (e.g., cities, regions).
        "startYear": <integer or null>,  # Description: The year when the impact started. Use null if unknown.
        "startMonth": <integer or null>,  # Description: The month when the impact started. Use null if unknown.
        "startDay": <integer or null>,  # Description: The day when the impact started. Use null if unknown.
        "endYear": <integer or null>,  # Description: The year when the impact ended. Use null if ongoing or unknown.
        "endMonth": <integer or null>,  # Description: The month when the impact ended. Use null if ongoing or unknown.
        "endDay": <integer or null>,  # Description: The day when the impact ended. Use null if ongoing or unknown.
        "hazards": ["<one or more of {hazard_cat}>" or null],  # Description: List of hazards causing the impact (e.g., Tropical storm, Drought, Flood).
        "impactsAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the impacts information. Write the text exactly as found in the original text.
    }}
    ]

    Rules:
    1. The `impactType` field must only contain one of the valid values: {imp_main}.
    2. The `impactSubtype` field must only contain one of the valid values: {imp_sub}.
    2. The `impactUnit` field must only contain one of the valid values: {imp_unit}.
    3. The `hazards` field must only contain values from {hazard_cat}.
    4. Follow the JSON format strictly; do not add or remove fields.
    5. Ensure all field constraints are respected. If any values are unknown, use null.
    6. Do not add notes or extra text, only output the list of JSONs.
    7. Do not reuse a specific impactValue for different entries.

    """
    return prompt

def quantify_impacts_type_value_loc_date_haz_free_unit_ranges(imp_sub, hazard_cat):
    """Find impact type, values, locs, etc. altogether"""
    prompt = f"""
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Extract from the above text all descriptions and mentions of impacts resulting from extreme
    natural hazard events.
    Answer by providing a list of JSONs, following strictly the JSON structure provided below and the strictly
    following the set of rules described after.

    ### Structure of the list of JSONs
    [
    {{
        "impactSubtype": "<one of {imp_sub}>",  # Description: Subtype of impact (e.g., Affected People, Road Infrastructure, Crop Production and Forestry).
        "impactValue": <float or null>  # Description: The quantified value of the impact. Provide the exact number if mentioned. If a range is provided give the upper estimate. Use null if unknown.
        "impactValuePrecision": "one of ["exact", "approx"], # Description: The flag describing whether the quantified impact value is exact or approximate. Use null if unknown.
        "impactValueMin": <float or null>,  # Description: The lower bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
        "impactValueMax": <float or null>,  # Description: The upper bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
        "impactUnit": "<string>" or null,  # Description: The unit of the impact value (e.g., people, meters, houses). Use null if unknown.
        "country": ["<list of strings>"],  # Description: The list of affected countries where the described impact occurred.
        "location": ["<list of strings>"],  # Description: The list of affected locations (e.g., cities, regions) where the described impact occurred.
        "startYear": <integer or null>,  # Description: The year when the impact started. Use null if unknown.
        "startMonth": <integer or null>,  # Description: The month when the impact started. Use null if unknown.
        "startDay": <integer or null>,  # Description: The day when the impact started. Use null if unknown.
        "endYear": <integer or null>,  # Description: The year when the impact ended. Use null if ongoing or unknown.
        "endMonth": <integer or null>,  # Description: The month when the impact ended. Use null if ongoing or unknown.
        "endDay": <integer or null>,  # Description: The day when the impact ended. Use null if ongoing or unknown.
        "hazards": ["<one or more of {hazard_cat}>" or null],  # Description: List of hazards causing the impact (e.g., Tropical storm, Drought, Flood).
        "impactsAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the impacts information. Write the text exactly as found in the original text.
    }}
    ]

    ### Rules:
    - The `impactSubtype` field must only contain one of the valid values: {imp_sub}.
    - The `hazards` field must only contain values from {hazard_cat}.
    - Do not reuse a specific impactValue for different entries.
    - Extract each mention of an impact only once. Do not repeat yourself.
    - Provide the exact text excerpt from where you extracted the impacts information in the `impactsAnnotation` field. Write the text exactly as found in the original text.
    - Provide the unit of the impact in the `impactUnit` field exactly as found in the original text, keeping all information on the measured quantity (e.g. write 'km of roads' instead of just 'km')
    - When multiple numbers are provided favour the `impactValue` associated with `impactUnit` in terms of "people" over "households", and "CHF" over other currencies
    - When the `impactValue` field is an exact number, `impactValuePrecision` must be set to `exact`.
    - When the `impactValue` field is an approximation, `impactValuePrecision` must be set to `approx`.
    - When the `impactValue` field is a range, `impactValuePrecision` must be set to `approx` and the `impactValueMin` and `impactValueMax` fields must be filled.
    - Provide the location names in the `location` field as the most precise level that is mentionned. Give the names exactly as written in the text. Do not aggregate different locations in words such as "varions locations" but provide the list of names.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the list of JSONs.

    """
    return prompt

def quantify_impacts_all_system_prompt(imp_sub, hazard_cat):
    """Find impact type, values, locs, etc. altogether"""
    prompt = f"""
    You are provided a text (### Input text) containing information about impacts from natural hazards. Extract from the
    provided text all descriptions and mentions of impacts resulting from the natural hazard events.
    You must provide your answer as a list of JSONs with the structure ###JSON structure described below,
    and strictly follow the rules described below in the ###Rules section. Further information on the fields to extract
    are provided in the ###impactSubtype description section, ###hazards description section and ###Examples provided
    at the end. See ###Example output for an example of how the output list of JSON must look like.
    ###JSON structure:
    [
    {{
        "impactSubtype": "<one of {imp_sub}>",  # Description: Subtype of impact (e.g., Affected People, Road Infrastructure, Crop Production and Forestry).
        "impactValue": <float or null>  # Description: The quantified value of the impact. Provide the exact number if mentioned. If a range is provided give the upper estimate. Use null if unknown.
        "impactValuePrecision": "one of ["exact", "approx"], # Description: The flag describing whether the quantified impact value is exact or approximate. Use null if unknown.
        "impactValueMin": <float or null>,  # Description: The lower bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
        "impactValueMax": <float or null>,  # Description: The upper bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
        "impactUnit": "<string>" or null,  # Description: The unit of the impact value (e.g., people, meters, houses). Use null if unknown.
        "country": ["<list of strings>"],  # Description: The list of affected countries where the described impact occurred.
        "location": ["<list of strings>"],  # Description: The list of affected locations (e.g., cities, regions) where the described impact occurred.
        "startYear": <integer or null>,  # Description: The year when the impact started. Use null if unknown.
        "startMonth": <integer or null>,  # Description: The month when the impact started. Use null if unknown.
        "startDay": <integer or null>,  # Description: The day when the impact started. Use null if unknown.
        "endYear": <integer or null>,  # Description: The year when the impact ended. Use null if ongoing or unknown.
        "endMonth": <integer or null>,  # Description: The month when the impact ended. Use null if ongoing or unknown.
        "endDay": <integer or null>,  # Description: The day when the impact ended. Use null if ongoing or unknown.
        "hazards": ["<one or more of {hazard_cat}>" or null],  # Description: List of hazards causing the impact (e.g., Tropical storm, Drought, Flood).
        "impactsAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the impacts information. Write the text exactly as found in the original text.
    }}
    ]

    ###Rules:
    - The `impactSubtype` field must only contain one of the valid values: {imp_sub}.
    - The `hazards` field must only contain values from {hazard_cat}.
    - Do not reuse a specific impactValue for different entries.
    - Extract each mention of an impact only once. Do not repeat yourself.
    - Provide the exact text excerpt from where you extracted the impacts information in the `impactsAnnotation` field. Write the text exactly as found in the original text.
    - Provide the unit of the impact in the `impactUnit` field exactly as found in the original text, keeping all information on the measured quantity (e.g. write 'km of roads' instead of just 'km')
    - When multiple numbers are provided favour the `impactValue` associated with `impactUnit` in terms of "people" over "households", and "CHF" over other currencies
    - When the `impactValue` field is an exact number, `impactValuePrecision` must be set to `exact`.
    - When the `impactValue` field is an approximation, `impactValuePrecision` must be set to `approx`.
    - When the `impactValue` field is a range, `impactValuePrecision` must be set to `approx` and the `impactValueMin` and `impactValueMax` fields must be filled.
    - Provide the location names in the `location` field as the most precise level that is mentionned. Give the names exactly as written in the text. Do not aggregate different locations in words such as "varions locations" but provide the list of names.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the list of JSONs.

    """
    return prompt
#- impactSubtype (string)
#- impactValue (float or null)
#- impactValuePrecision (string)
#- impactValueMin (float or null)
#- impactValueMax (float or null)
#- impactUnit (string or null)
#- country (list of strings or null)
#- location (list of strings or null)
#- startYear (integer or null)
#- startMonth (integer or null)
#- startDay (integer or null)
#- endYear (integer or null)
#- endMonth (integer or null)
#- endDay (integer or null)
#- hazards (list of strings or null)
#- impactsAnnotation (list of strings)

def impact_scehem_json_schema(impsub_list, haz_list):
    impact_scheme_json = {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "impactSubtype": {
            "type": "string",
            "enum": impsub_list
          },
          "impactValue": { "type": ["number", "null"] },
          "impactUnit": { "type": ["string", "null"] },
          "impactValuePrecision": {
              "type": ["string", "null"],
              "enum": ["exact", "approx"]
          },
          "country": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 1
          },
          "location": {
            "type": ["array", "null"],
            "items": { "type": "string" }
          },
          "startYear": { "type": ["integer", "null"] },
          "startMonth": { "type": ["integer", "null"] },
          "startDay": { "type": ["integer", "null"] },
          "endYear": { "type": ["integer", "null"] },
          "endMonth": { "type": ["integer", "null"] },
          "endDay": { "type": ["integer", "null"] },
          "hazards": {
            "type": ["array", "null"],
            "items": {
              "type": "string",
              "enum": haz_list
            },
            "minItems": 1
          },
          "impactsAnnotation": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 1
          }
        },
        "required": ["impactSubtype",
                     "impactValue",
                     "hazards",
                     "location",
                     "startYear",
                     "startMonth",
                     "startDay",
                     "endYear",
                     "endMonth",
                     "endDay",
                     "impactValueMin",
                     "impactValueMax",
                     "impactUnit",
                     "impactValuePrecision",
                     "country",
                     "impactsAnnotation"]
      }
    }
    return impact_scheme_json

def groq_system_prompt(imp_sub, hazard_cat):
    prompt = f"""

    ### System
    You are a data-extraction bot. Return **ONLY** a python list of valid JSONs.

    ### Instructions
    Return only a python list of JSONs. Each JSON must have the following fields, with the correct data type and correspoding to the description:
    - "impactSubtype": "<one of {imp_sub}>",  # Description: Subtype of impact (e.g., Affected People, Road Infrastructure, Crop Production and Forestry).
    - "impactValue": <float or null>  # Description: The quantified value of the impact. Provide the exact number if mentioned. If a range is provided give the upper estimate. Use null if unknown.
    - "impactValuePrecision": "one of ["exact", "approx"], # Description: The flag describing whether the quantified impact value is exact or approximate. Use null if unknown.
    - "impactValueMin": <float or null>,  # Description: The lower bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
    - "impactValueMax": <float or null>,  # Description: The upper bound estimate of the quantified value of the impact if the impact is approximate or a range. Use null if unknown.
    - "impactUnit": "<string>" or null,  # Description: The unit of the impact value (e.g., people, meters, houses). Use null if unknown.
    - "country": ["<list of strings>"],  # Description: The list of affected countries where the described impact occurred.
    - "location": ["<list of strings>"],  # Description: The list of affected locations (e.g., cities, regions) where the described impact occurred.
    - "startYear": <integer or null>,  # Description: The year when the impact started. Use null if unknown.
    - "startMonth": <integer or null>,  # Description: The month when the impact started. Use null if unknown.
    - "startDay": <integer or null>,  # Description: The day when the impact started. Use null if unknown.
    - "endYear": <integer or null>,  # Description: The year when the impact ended. Use null if ongoing or unknown.
    - "endMonth": <integer or null>,  # Description: The month when the impact ended. Use null if ongoing or unknown.
    - "endDay": <integer or null>,  # Description: The day when the impact ended. Use null if ongoing or unknown.
    - "hazards": ["<one or more of {hazard_cat}>" or null],  # Description: List of hazards causing the impact (e.g., Tropical storm, Drought, Flood).
    - "impactsAnnotation": ["<list of strings>"]  # Description: the exact text excerpt from where you extracted the impacts information. Write the text exactly as found in the original text. Provide the entire sentences.

    Respect the following rules:
    - The `impactSubtype` field must only contain one of the valid values: {imp_sub}.
    - The `hazards` field must only contain values from {hazard_cat}.
    - Do not reuse a specific impactValue for different entries.
    - Provide the exact text excerpt from where you extracted the impacts information in the `impactsAnnotation` field. Write the text exactly as found in the original text. Provide the entire sentences.
    - Extract each mention of an impact only once. Do not repeat yourself.
    - Provide the unit of the impact in the `impactUnit` field exactly as found in the original text, keeping all information on the measured quantity (e.g. write 'km of roads' instead of just 'km')
    - When multiple numbers are provided favour the `impactValue` associated with `impactUnit` in terms of "people" over "households", and "CHF" over other currencies
    - When the `impactValue` field is an exact number, `impactValuePrecision` must be set to `exact`.
    - When the `impactValue` field is an approximation, `impactValuePrecision` must be set to `approx`.
    - When the `impactValue` field is a range, `impactValuePrecision` must be set to `approx` and the `impactValueMin` and `impactValueMax` fields must be filled.
    - Follow the JSON format strictly; do not add or remove fields.
    - Ensure all field constraints on allowed values and their data types are respected.
    - Do not add notes or extra text, only output the list of JSONs.
    """
    return prompt


def quantify_impacts_all_user_prompt(text):
    prompt = f"""
    Please extract from the text TEXT below all the information about impacts from natural hazards
    as described in the instructions, providing your answer in the correct format as described in
    the instructions.

    TEXT:
    {text}
    """
    return prompt

def groq_user_prompt(text):
    prompt = f"""
    Please extract from the input text below all the information about impacts from natural hazards.

    ### Input text:
    {text}
    """
    return prompt

def add_text_prompt(prompt, text, text_pos="below"):
    if text_pos == "above":
        prompt = "### Input text:\n" + text + "\n" + prompt
    elif text_pos == "below":
        prompt = prompt + "\n### Input text:\n" + text
    else:
        raise ValueError("Position must be 'above' or 'below'")
    return prompt

def add_context(prompt, context):
    return prompt + "\n### Context\nUse the following descriptions to help you complete the task:\n" + context

def add_subtype_descriptions_prompt(prompt, category, descriptions):
    return prompt + f"\n###{category} description:\n " + descriptions

def add_examples_prompt(prompt, examples):
    return prompt + f"\n### Example output:\n {examples}"

def add_examples_prompt_v2(prompt, examples):
    new_prompt = ""
    for i, example in enumerate(examples):
        new_prompt += f"\n### Example {i+1}:\n {example}\n"
    return prompt + new_prompt

def format_desc(desc_dict):
    return "\n".join([f"{k}: {v}" for k, v in desc_dict.items()])


def quantify_impacts_type_value_loc_date_haz(text, impact_cat_desc_dict, hazard_all_subtype_emdat):
    """Find impact type, values, locs, etc. altogether"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Eextract from the above text all descriptions and mentions of impacts resulting from extreme
    natural hazard events. Focus on the categories of impacts described as follow: {impact_cat_desc_dict}.
    For each mention of impact that you identify, extract the following information:
    "impactType"        : The type of impact. If no type of impact can be identified, write null.
                          Choose from the list {impact_cat_desc_dict.keys()}.
                          Do not include impact types that are not from the list.
                          Write the impact exactly as they are written in the list.
    "impactValue"       : The quantified value of the described impact.
                          Make sure that the value is consistent with the impactUnit field.
                          If no quantified value can be identified, write null.
    "impactUnit         : The unit of the quantified impact value.
                          Make sure that the value is consistent with the impactValue field.
                          If no unit can be identified, write null.
    "impactValueFlag"   : The quality flag for the quantified impact value informing on the confidence
                          in the quantified value. If the extracted impactValue is exact (e.g. "1001 people have been affected"), write "exact".
                          If the extracted impactValue is an approximation (e.g. "several hundred people have been affected"), write "approx".
    "location"          : The locations for which the impact value is described.
                          Write the locations exactly as they are written in the text.
                          If no location can be identified, write null.
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
                          write the hazards in a python list format [hazard1, hazard2].
                          Choose from the list {hazard_all_subtype_emdat}.
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
       "impactType" : "Affected People",
       "impactValue": 10000,
       "impactUnit": "people",
       "impactValueFlag" : "exact",
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
       "impactType" : "Affected People",
       "impactValue": 100,
       "impactUnit": "hospitals",
       "impactValueFlag" : "exact",
        "location" : ["Red Sea State"],
        "startYear" : "2024",
        "startMonth" : "08",
        "startDay" : "null",
        "endYear" : "2024",
        "endMonth" : "10",
        "endDay" : "null",
        "hazards" : ["flash flood"],
        "impactAnnotation" : ["Flash floods impacted 100 hospitals in Red Sea State between August to October 2024",]
      },
      {
          "impactType" : "Healthcare Infrastructure",
          "impactValue": 4,
          "impactUnit": "hospitals",
          "impactValueFlag" : "approx",
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

#without constraint in user prompt
def quantify_impacts_type_value_loc_date_haz_v2(text, impact_cat_desc_dict, hazard_all_subtype_emdat):
    """Find impact type, values, locs, etc. altogether"""
    prompt = f"""
    Context information is below.
    ---
    {text}
    ---
    Using information from the text above and no previous knowledge, please answer the query.
    Query: Extract from the above text all descriptions and mentions of impacts resulting from extreme
    natural hazard events. Focus on the categories of impacts described as follow: {impact_cat_desc_dict}.
    For each mention of impact that you identify, extract the following information:
    "impactType"        : The type of impact. If no type of impact can be identified, write null.
                          Write the impact exactly as they are written in the list.
    "impactValue"       : The quantified value of the described impact.
                          Make sure that the value is consistent with the impactUnit field.
                          If no quantified value can be identified, write null.
    "impactUnit         : The unit of the quantified impact value.
                          Make sure that the value is consistent with the impactValue field.
                          If no unit can be identified, write null.
    "impactValueFlag"   : The quality flag for the quantified impact value informing on the confidence
                          in the quantified value. If the extracted impactValue is exact (e.g. "1001 people have been affected"), write "exact".
                          If the extracted impactValue is an approximation (e.g. "several hundred people have been affected"), write "approx".
    "location"          : The locations for which the impact value is described.
                          Write the locations exactly as they are written in the text.
                          If no location can be identified, write null.
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
                          write the hazards in a python list format [hazard1, hazard2].
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
       "impactType" : "Affected People",
       "impactValue": 10000,
       "impactUnit": "people",
       "impactValueFlag" : "exact",
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
       "impactType" : "Affected People",
       "impactValue": 100,
       "impactUnit": "hospitals",
       "impactValueFlag" : "exact",
        "location" : ["Red Sea State"],
        "startYear" : "2024",
        "startMonth" : "08",
        "startDay" : "null",
        "endYear" : "2024",
        "endMonth" : "10",
        "endDay" : "null",
        "hazards" : ["flash flood"],
        "impactAnnotation" : ["Flash floods impacted 100 hospitals in Red Sea State between August to October 2024",]
      },
      {
          "impactType" : "Healthcare Infrastructure",
          "impactValue": 4,
          "impactUnit": "hospitals",
          "impactValueFlag" : "approx",
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

#functions to be parsed to chat.completions (do not seem to work)
functions = [
    {
        "name": "ImpactList",
        "description": "Analyze impacts and structure results.",
        "parameters": {
            "type": "object",
            "properties": {
                "impacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "impactType": {"type": "string", "enum": ["Affected People", "Jeej"]},
                            "impactValue": {"type": ["integer", "null"]},
                            "impactUnit": {"type": ["string", "null"]},
                            "location": {"type": "array", "items": {"type": "string"}},
                            "startYear": {"type": ["integer", "null"]},
                            "startMonth": {"type": ["integer", "null"]},
                            "startDay": {"type": ["integer", "null"]},
                            "endYear": {"type": ["integer", "null"]},
                            "endMonth": {"type": ["integer", "null"]},
                            "endDay": {"type": ["integer", "null"]},
                            "hazards": {"type": "array", "items": {"type": "string", "enum": ["Flood", "Storm", "Drought"]}},
                            "impactsAnnotation": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["impactType", "location", "hazards", "impactsAnnotation"]
                    }
                }
            },
            "required": ["impacts"]
        }
    }
]

