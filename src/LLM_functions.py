# Functions to extract data with LLMs
import time
from attr import validate
import pandas as pd
import numpy as np
import json as json
import regex as re
import json_repair
import random
import json
import re
import logging

# import instructor
from pydantic import ValidationError
from typing import get_type_hints, get_origin, get_args
from copy import deepcopy

# from itertools import chain
# from langchain_groq import ChatGroq
from src.data_format import listify_strings
from src.hazard_def import *
from src.impact_def import *
from src.data import *

# from src.prompts_hazards import *
from src.prompts_impacts import *
from src.client import CLIENT, CONTEXT_WINDOW, MODEL_NAME, MAX_COMPLETION_TOKENS
from src.classOutput import *

# set up logger
LOGGER = logging.getLogger("impact_extraction")


def extract_outer_json(text):
    start_index = text.find("{")
    end_index = text.rfind("}")

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        return None  # Return None for empty JSON or invalid format

    extracted_json = text[start_index : end_index + 1]
    return extracted_json


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


# def check_result_json(result_json, label=None):
#    try:
#        answer = json.loads(result_json.replace("\n", ""))
#        if label:
#            answer = answer[label]
#    except Exception as e:
#        LOGGER.error("An unexpected error occurred: %s", e)
#        return None
#    if not answer:
#        LOGGER.info("JSON is empty: %s", result_json)
#    return answer


def build_messages(prompt, prompt_system=None, prompt_assistant=None):
    """Build messages for OpenAI API based on (user) prompt, system prompt and assistant prompt"""

    messages = [{"role": "user", "content": prompt}]
    if prompt_system:
        messages.append({"role": "system", "content": prompt_system})
    if prompt_assistant:
        messages.append({"role": "assistant", "content": prompt_assistant})
    return messages


def extract_json_block(text):
    """
    Attempts to extract the first JSON-like block from text.
    Supports arrays and objects.
    """
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return match.group(1)
    return text  # fallback to raw


def get_model_response(messages, max_retries=5, initial_wait=2, **kwargs):
    """Query Groq API with retry and exponential backoff when hitting 429 errors."""

    for attempt in range(max_retries):
        try:
            completion = CLIENT.chat.completions.create(
                model=MODEL_NAME, messages=messages, **kwargs
            )
            used_tokens = completion.usage.total_tokens
            completion_tokens = completion.usage.completion_tokens
            if used_tokens > CONTEXT_WINDOW:
                LOGGER.warning(
                    "Request exceeded max context window width: %i > %i",
                    used_tokens,
                    CONTEXT_WINDOW,
                )
            if completion_tokens > MAX_COMPLETION_TOKENS:
                LOGGER.warning(
                    "Request exceeded max completion tokens: %i > %i",
                    completion_tokens,
                    MAX_COMPLETION_TOKENS,
                )
            return completion  # ✅ Success, return response immediately

        except Exception as e:
            error_message = str(e)

            # Handle rate limit or token errors
            if "429" in error_message or "rate" in error_message.lower():
                wait_time = initial_wait * (2**attempt) + random.uniform(
                    0.1, 0.5
                )  # jitter to avoid thundering herd
                LOGGER.info(
                    "[Rate Limit] 429 received. Retry %i/%i in %.1f seconds...",
                    attempt + 1,
                    max_retries,
                    wait_time,
                )
                time.sleep(wait_time)
                continue

            # Other errors → stop immediately
            LOGGER.error("[API Error - Not Retrying] %s", error_message)
            return None  # {"error": "API call failed.", "details": error_message}
    LOGGER.error(
        "[API Error - Max Retries Exceeded] Max retries exceeded due to rate limits."
    )
    return None  # {"error": "Max retries exceeded due to rate limits."}


def get_model_response_retry(
    messages, output_model, nb_valid_error=0, trials=0, trials_limit=2, **kwargs
):
    """Get model response structured using OpenAI API allowing for one retry prompting the model with its error
    from pydantic ValidationError"""
    # get model response
    response = get_model_response(messages, **kwargs)
    if response is None:
        return None, None, 1

    # Parse the response content into a list of ImpactDetail objects
    raw_text = response.choices[0].message.content

    try:
        response_content = json_repair.loads(raw_text)
    except Exception as e:
        LOGGER.error("[JSON_REPAIR ERROR] Falling back to raw content. Error: %s", e)
        # Try a simpler parse: extract JSON substring or force minimal cleanup
        try:
            json_str = extract_json_block(
                raw_text
            )  # custom helper to extract {...} or [...]
            response_content = json.loads(json_str)
        except Exception as e2:
            LOGGER.error("[SECONDARY JSON LOAD FAILURE] %s", e2)
            return None, None, 1

    # response_content = json_repair.loads(response.choices[0].message.content)
    try:
        # Normalize string nulls to actual None before validation
        # This prevents float_parsing errors when LLM returns 'None' instead of null
        response_content = normalize_null_values(response_content)
        structured_response = output_model.model_validate(response_content)
        return (
            response,
            structured_response.model_dump(),
            nb_valid_error,
        )  # Return as Python object
    except ValidationError as e:
        nb_valid_error += 1
        LOGGER.info("Validation Error: %s", e)
        # allow one retry prompting the model with its error
        # Add context messages and build retry messages
        retry_prompt = f"""
        The previous response was not valid due to the error:\n {e}.\n
        Please answer again the query respecting the output format specified and the instructions to avoid the error.\n
        """
        # Query:\n
        # {prompt}
        # """
        messages.append({"role": "assistant", "content": str(response_content)})
        messages.append({"role": "user", "content": retry_prompt})

        trials += 1
        if trials < trials_limit:
            return get_model_response_retry(
                messages, output_model, nb_valid_error, trials, trials_limit, **kwargs
            )
        else:
            return response, response_content, nb_valid_error


def get_model_response_retry_continue(
    prompt_user,
    output_model,
    validate_fields,
    prompt_system=None,
    prompt_assistant=None,
    max_rounds=5,
    **groq_kwargs,
):
    """Get continued model response reprompting the model with the previous response. Stops when max_rounds is reached or now new (not duplicate)
    impacts are extracted."""
    full_response_raw = ""  # need to feed raw response to llm otherwise causes issues with output format
    full_response_formatted = []
    valid_error_count = {i: 0 for i in range(max_rounds)}
    nb_extracted_impacts = {}

    init_messages = build_messages(
        prompt_user, prompt_system=prompt_system, prompt_assistant=prompt_assistant
    )
    messages = init_messages
    # get model response
    for i in range(max_rounds):
        # get model response
        raw_response, structured_response, nb_valid_error = get_model_response_retry(
            messages, output_model, valid_error_count[i], **groq_kwargs
        )
        valid_error_count[i] += nb_valid_error
        if structured_response is None or not isinstance(structured_response, list):
            nb_extracted_impacts[i] = 0
            continue
        # deduplicate output
        try:
            structured_response_non_dedup = structured_response
            structured_response = deduplicate_structured_responses(
                full_response_formatted,
                structured_response,
                validate_fields=validate_fields,
            )
            LOGGER.info(
                "Deduplicated %i impacts",
                len(structured_response_non_dedup) - len(structured_response),
            )
        except Exception as e:
            LOGGER.error("deduplicate_structured_responses error: %s", e)

        valid_error_count[i] = valid_error_count.get(i, 0)
        if len(structured_response):
            nb_extracted_impacts[i] = len(structured_response)
        else:
            nb_extracted_impacts[i] = 0
            break
        full_response_raw += raw_response.choices[
            0
        ].message.content  # keep raw output so it does not mess with formating instructions
        full_response_formatted.extend(structured_response)

        # Add assistant message and user prompt for continuation
        messages = deepcopy(init_messages)
        messages.append(
            {"role": "assistant", "content": str(json.dumps(full_response_formatted))}
        )
        messages.append(
            {
                "role": "user",
                "content": "Check for NEW impacts not already extracted above. "
                "Only return the NEW impacts, do not return the ones already extracted. "
                "Answer in the same format as before. "
                "Do NOT return repeated impacts under any circumstances.",
            }
        )

    LOGGER.info("Nb. of iterations: %i", i + 1)
    # extend and flatten list
    valid_error_ext = []
    for it in nb_extracted_impacts.keys():
        count = nb_extracted_impacts[it]
        errs = valid_error_count.get(it, 0)
        valid_error_ext.extend([errs] * count)
    return full_response_formatted, valid_error_ext


def is_extraction_finished(response_content):
    """check if extraction is finished"""
    return "__end__" in response_content.lower()


def normalize_null_values(obj):
    """
    Recursively convert string representations of null/None/nan to actual None values.
    This prevents Pydantic validation errors when LLM returns string 'None' instead of JSON null.

    Args:
        obj: A dictionary, list, or primitive value to normalize

    Returns:
        The normalized object with string nulls converted to None
    """
    null_strings = {"None", "none", "null", "Null", "NULL", "nan", "NaN", "NAN", ""}

    if isinstance(obj, dict):
        return {k: normalize_null_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_null_values(item) for item in obj]
    elif isinstance(obj, str):
        # Convert string nulls to actual None
        if obj.strip() in null_strings:
            return None
        return obj
    else:
        return obj


def parse_none_str(output):
    """
    Parse "None" strings in a list or dictionary and replace them with None value.

    Args:
        output (list or dict): List or dictionary to parse.

    Returns:
        list or dict: List or dictionary with "None" strings replaced by None value.
    """
    if isinstance(output, list):
        new_output = []
        for el in output:
            if isinstance(el, dict):
                new_output.append(
                    {
                        k: None if v in ["None", "none", "Null", "null"] else v
                        for k, v in el.items()
                    }
                )
        output = new_output
    elif isinstance(output, dict):
        output = {
            k: None if v in ["None", "none", "Null", "null"] else v
            for k, v in el.items()
        }

    return output


def get_target_type(output_model):
    """Infer target type from output_model"""
    model_types = get_type_hints(output_model)
    if "root" in model_types:  # pydantic v1 style RootModel
        field_type = model_types["root"]
    elif "__root__" in model_types:  # pydantic v2 style RootModel
        field_type = model_types["__root__"]
    else:
        return None  # no special root type

    # If it's something like List[ImpactValue], get_origin returns <class 'list'>
    return get_origin(field_type) or field_type


def force_target_type(output_model, response):
    """Function to force target type based on output_model"""
    target_type = get_target_type(output_model)

    if target_type is None:
        return response

    # Handle lists
    if target_type is list:
        if not isinstance(response, list):
            return [response]
        elif all(isinstance(x, list) for x in response):
            return [item for sublist in response for item in sublist]  # flatten
        else:
            return response
    # Handle dicts
    if target_type is dict and isinstance(response, list) and len(response) == 1:
        return response[0]  # unwrap singleton list

    return response


def deduplicate_structured_responses(
    prev_responses,
    new_responses,
    validate_fields,
):
    """Function to check for duplicate responses. Returns a list of unique responses."""
    if validate_fields is None:
        validate_fields = (
            [col for col in prev_responses[0].keys()]
            if len(prev_responses) > 0
            else [col for col in new_responses[0].keys()]
        )
    new_unique_responses = []
    seen = set(
        tuple(str(entry[field]) for field in validate_fields)
        for entry in prev_responses
    )

    for new_entry in new_responses:
        entry_key = tuple(str(new_entry[field]) for field in validate_fields)
        if entry_key not in seen:
            seen.add(entry_key)
            new_unique_responses.append(new_entry)
    return new_unique_responses


def break_down_sent(sentences, max_tokens):
    """break down single sentences if too long"""
    for i, sent in enumerate(sentences):
        if len(sent) > max_tokens:
            # break sentence into chunks
            sent1 = sent[:max_tokens]
            sent2 = sent[max_tokens:]
            sentences[i] = sent1
            sentences.insert(i + 1, sent2)
    return sentences


def break_down_text(sentences, max_tokens=5000):
    """break down entire text of sentences"""
    cum_len = 0
    break_id = []
    sentences = break_down_sent(sentences, max_tokens)
    for i, sent in enumerate(sentences):
        cum_len += len(sent)
        if cum_len > max_tokens:
            cum_len = 0
            break_id.append(i)
    if len(break_id) > 0:
        chunks = []
        for i in range(len(break_id)):
            if i == 0:
                chunks.append(sentences[: break_id[i]])
            else:
                chunks.append(sentences[break_id[i - 1] : break_id[i]])
        chunks.append(sentences[break_id[-1] :])
        return chunks
    else:
        return sentences


def extract_impact_value(impact):
    """
    Extracts the impact value from the impact dictionary/DataFrame.
    Correctly handles None, np.nan, and their string equivalents ("null", "none", "nan", etc.)

    Args:
        impact: A pandas DataFrame with one row containing impact value columns

    Returns:
        The maximum numeric value, or None if no valid values found
    """

    impact_cols = [
        col
        for col in impact
        if col in ["impactValue", "impactValueMin", "impactValueMax"]
    ]

    if not impact_cols:
        return None

    # Get the data
    data = impact[impact_cols]

    # Define null string values to filter
    null_strings = {"None", "none", "Null", "null", "NULL", "NaN", "nan", "NAN", ""}

    # Function to check if a value is null-like
    def is_null_like(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return True
        if isinstance(val, str) and val.strip() in null_strings:
            return True
        return False

    # Collect valid numeric values
    valid_values = []
    for col in impact_cols:
        for val in data[col]:
            if not is_null_like(val):
                try:
                    valid_values.append(float(val))
                except (ValueError, TypeError):
                    pass

    # Return the maximum value or None if no valid values
    return max(valid_values) if valid_values else None


def impact_extraction_chain(
    text,
    impact_types_dict,
    validate_fields,
    validate_impSubtypes=True,
    max_rounds=None,
    **groq_kwargs,
):
    ## Identify impact subtypes
    prompt_impact_type = build_messages(
        identify_impacts_prompt(text, impact_types_dict)
    )
    impact_types_list = list(impact_types_dict.keys())
    ImpactSubtypes.set_allowed_subtypes(impact_types_list)
    _, answer_impact_types, valid_errors_impSubT = get_model_response_retry(
        prompt_impact_type, ImpactSubtypes, **groq_kwargs
    )
    if not answer_impact_types or len(answer_impact_types) == 0:
        LOGGER.info("No impact types identified. Stopping extraction.")
        return None, 0
    elif len(answer_impact_types["impactSubtypes"]) == 0:
        LOGGER.info("No impact types identified. Stopping extraction.")
        return None, 0

    impact_types = answer_impact_types["impactSubtypes"]

    ## Identify impact values
    prompt_value_unit = identify_value_unit_prompt_quanti(text, impact_types)
    ImpactValue.set_allowed_subtypes(impact_types)
    if not validate_impSubtypes:
        ImpactValue.turn_off_impactSubtypes_validation()
    if max_rounds is not None:
        answer_impact_values, valid_errors_impVal = get_model_response_retry_continue(
            prompt_value_unit,
            ImpactValueList,
            validate_fields=validate_fields,
            max_rounds=max_rounds,
            **groq_kwargs,
        )
    else:
        _, answer_impact_values, valid_errors_impVal = get_model_response_retry(
            build_messages(prompt_value_unit), ImpactValueList, **groq_kwargs
        )
        valid_errors_impVal = (
            [valid_errors_impVal] * len(answer_impact_values)
            if answer_impact_values
            else []
        )
    return answer_impact_values, valid_errors_impVal


def clean_value_unit(answer_impact_values, valid_errors_impVal):
    """Clean and validate the impact values and units extracted by the model, ensuring they are in the correct format and contain the required fields.
    This function performs the following steps:
    1. Normalizes the list structure of the impact values, unwrapping singleton lists
    2. Validates that each impact value is a dictionary containing the required 'impactValue' key
    3. Extracts the numeric impact value using the extract_impact_value function, handling any errors that may arise during extraction
    4. Checks for the presence of value annotations, logging a message if none are found
    5. Tracks the number of validation errors for each impact value and adds this information to the impact dictionary
    6. Returns a cleaned list of impact values that are properly formatted and contain the necessary information for further processing in the extraction chain.
    """
    answer_impact_values_cleaned = []
    for i, impact in enumerate(answer_impact_values):
        # normalize list structure
        if isinstance(impact, list):
            if len(impact) == 1:
                impact = impact[0]
            else:
                LOGGER.info("discarding impact (list with >1 items): %s", impact)
                continue

        # validate that impact is a dict with the required key
        if not isinstance(impact, dict):
            LOGGER.info("discarding impact (not a dict): %s", impact)
            continue

        if "impactValue" not in impact:
            LOGGER.info("discarding impact (missing 'impactValue'): %s", impact)
            continue

        # extract impact value
        try:
            impact_value = extract_impact_value(pd.DataFrame([impact]))
            impact["impactValue"] = impact_value
        except TypeError as e:
            print("TypeError in extract_impact_value for impact:", impact)
            LOGGER.info("Error occurred while extracting impact value: %s", e)
            continue

        if not impact.get("valueAnnotation", None):
            LOGGER.info("No impact sentences found for impact: %s", impact)
            continue

        # track errors in impact extraction
        impact.update({"valid_errors_impactValue": valid_errors_impVal[i]})
        answer_impact_values_cleaned.append(impact)
    return answer_impact_values_cleaned


def impact_extraction_chain_quanti(
    text,
    impact_types_dict,
    validate_fields,
    validate_impSubtypes=True,
    max_rounds=None,
    **groq_kwargs,
):
    ## Identify impact subtypes
    prompt_impact_type = build_messages(
        identify_impacts_prompt(text, impact_types_dict)
    )
    impact_types_list = list(impact_types_dict.keys())
    ImpactSubtypes.set_allowed_subtypes(impact_types_list)
    _, answer_impact_types, valid_errors_impSubT = get_model_response_retry(
        prompt_impact_type, ImpactSubtypes, **groq_kwargs
    )
    if not answer_impact_types or len(answer_impact_types) == 0:
        LOGGER.info("No impact types identified. Stopping extraction.")
        return None, 0
    elif len(answer_impact_types["impactSubtypes"]) == 0:
        LOGGER.info("No impact types identified. Stopping extraction.")
        return None, 0

    impact_types = answer_impact_types["impactSubtypes"]

    ## Identify impact values
    prompt_value_unit = identify_value_unit_prompt_quanti(text, impact_types)
    ImpactValueQuanti.set_allowed_subtypes(impact_types)
    if not validate_impSubtypes:
        ImpactValueQuanti.turn_off_impactSubtypes_validation()
    if max_rounds is not None:
        answer_impact_values, valid_errors_impVal = get_model_response_retry_continue(
            prompt_value_unit,
            ImpactValueQuantiList,
            validate_fields=validate_fields,
            max_rounds=max_rounds,
            **groq_kwargs,
        )
    else:
        _, answer_impact_values, valid_errors_impVal = get_model_response_retry(
            build_messages(prompt_value_unit), ImpactValueQuantiList, **groq_kwargs
        )
        valid_errors_impVal = (
            [valid_errors_impVal] * len(answer_impact_values)
            if answer_impact_values
            else []
        )

    return impact_types, answer_impact_values, valid_errors_impVal


def duplicate_impact_by_date_pairs(impact_dict, date_pairs, valid_error_dates):
    """
    Duplicate an impact record for each date pair.

    Args:
        impact_dict: The impact dictionary (without date fields)
        date_pairs: List of DatePair objects with individual dateAnnotation
        valid_error_dates: Count of validation errors for the date fields

    Returns:
        List of impact dictionaries, one per date pair
    """
    duplicated_impacts = []

    for date_pair in date_pairs:
        # Create a copy of the impact
        impact_copy = deepcopy(impact_dict)

        # Convert DatePair to dict if needed
        if hasattr(date_pair, "model_dump"):
            pair_dict = date_pair.model_dump()
        else:
            pair_dict = date_pair

        # Add the individual date pair fields, including its annotation
        impact_copy.update(
            {
                "startYear": pair_dict.get("startYear"),
                "startMonth": pair_dict.get("startMonth"),
                "startDay": pair_dict.get("startDay"),
                "endYear": pair_dict.get("endYear"),
                "endMonth": pair_dict.get("endMonth"),
                "endDay": pair_dict.get("endDay"),
                "dateAnnotation": pair_dict.get("dateAnnotation", []),
                "valid_errors_dates": valid_error_dates,
            }
        )

        duplicated_impacts.append(impact_copy)

    return duplicated_impacts


def extract_localization_hazards_for_impact(
    text, impact_desc, answer_loc, hazards_list, validate_hazards=True, **groq_kwargs
):
    """
    Helper function to extract hazards for a given impact description.
    Compartmentalized to reduce code duplication.

    Args:
        text: Full text for context
        impact_desc: Description of the impact
        answer_loc: Location dict with country/location/annotation
        hazards_list: List of allowed hazards
        validate_hazards: Whether to validate hazard values
        **groq_kwargs: Additional kwargs for API calls

    Returns:
        Tuple of (answer_loc, answer_hazards, valid_errors_haz)
    """
    # Extract hazards
    prompt_impact_hazards = build_messages(
        identify_impact_hazards_prompt(
            text, impact_desc, answer_loc, hazards_list, dates=None
        )
    )
    ImpactHazards.set_allowed_classes(hazards_list)
    if not validate_hazards:
        ImpactHazards.turn_off_hazard_validation()
    _, answer_hazards, valid_errors_haz = get_model_response_retry(
        prompt_impact_hazards, ImpactHazards, **groq_kwargs
    )
    if isinstance(answer_hazards, list) and len(answer_hazards) == 1:
        answer_hazards = answer_hazards[0]
    if not isinstance(answer_hazards, dict):
        answer_hazards = {"hazards": None, "hazardsAnnotation": None}
    answer_hazards["valid_errors_haz"] = valid_errors_haz

    return answer_hazards


def extract_locations_for_impact(text, impact_desc, **groq_kwargs):
    """
    Helper function to extract locations for a given impact description.
    Compartmentalized to reduce code duplication.

    Args:
        text: Full text for context
        impact_desc: Description of the impact
        **groq_kwargs: Additional kwargs for API calls

    Returns:
        Tuple of (answer_loc_dict, valid_errors_loc)
    """
    prompt_impact_loc = build_messages(identify_impact_loc_prompt(text, impact_desc))
    _, answer_loc, valid_errors_loc = get_model_response_retry(
        prompt_impact_loc, ImpactLocation, **groq_kwargs
    )
    if isinstance(answer_loc, list) and len(answer_loc) == 1:
        answer_loc = answer_loc[0]
    if not isinstance(answer_loc, dict):
        answer_loc = {"country": None, "location": None, "locationAnnotation": None}
    answer_loc["valid_errors_loc"] = valid_errors_loc

    return answer_loc


def extract_dates_for_impact(
    text,
    impact_desc,
    answer_loc,
    multi_dates=False,
    is_qualitative=False,
    **groq_kwargs,
):
    """
    Helper function to extract dates for a given impact description.
    Handles both quantitative (single date range) and qualitative (multiple date pairs).

    Args:
        text: Full text for context
        impact_desc: Description of the impact
        answer_loc: Location dict with country/location/annotation
        is_qualitative: If True, extract multiple date pairs; else single date range
        **groq_kwargs: Additional kwargs for API calls

    Returns:
        Tuple of (answer_dates_dict, valid_errors_dates, impacts_list)
            - impacts_list will contain duplicated impacts for multi-date extraction
    """
    if is_qualitative and multi_dates:
        # For qualitative, extract multiple date pairs
        prompt_impact_dates = build_messages(
            identify_impact_dates_prompt_qualitative(text, impact_desc, answer_loc)
        )
        _, answer_dates, valid_errors_dates = get_model_response_retry(
            prompt_impact_dates, ImpactDatesMultiple, **groq_kwargs
        )

        if isinstance(answer_dates, dict) and "datePairs" in answer_dates:
            date_pairs = answer_dates["datePairs"]
            return answer_dates, date_pairs
        else:
            # Fall back to single date if extraction fails
            LOGGER.info(
                "Failed to extract multiple date pairs, falling back to single date"
            )
            if isinstance(answer_dates, list) and len(answer_dates) == 1:
                answer_dates = answer_dates[0]
            if not isinstance(answer_dates, dict):
                answer_dates = {
                    "startYear": None,
                    "startMonth": None,
                    "startDay": None,
                    "endYear": None,
                    "endMonth": None,
                    "endDay": None,
                    "dateAnnotation": None,
                }
            answer_dates["valid_errors_dates"] = valid_errors_dates
            return answer_dates, None
    else:
        # Use single date extraction
        prompt_impact_dates = build_messages(
            identify_impact_dates_prompt(text, impact_desc, answer_loc)
        )
        _, answer_dates, valid_errors_dates = get_model_response_retry(
            prompt_impact_dates, ImpactDates, **groq_kwargs
        )
        if isinstance(answer_dates, list) and len(answer_dates) == 1:
            answer_dates = answer_dates[0]
        if not isinstance(answer_dates, dict):
            answer_dates = {
                "startYear": None,
                "startMonth": None,
                "startDay": None,
                "endYear": None,
                "endMonth": None,
                "endDay": None,
                "dateAnnotation": None,
            }
        answer_dates["valid_errors_dates"] = valid_errors_dates
        return answer_dates, None


def extraction_chain_multiprompt(
    text,
    impact_types_dict,
    hazards_list,
    dedup_impacts,
    dedup_fields,
    validate_impSubtypes=True,
    validate_hazards=True,
    max_rounds=5,
    chunk_size=None,
    multi_dates=False,
    **groq_kwargs,
):
    """
    Multiprompt extraction chain with following sequence
        1. Type
        2. Value unit
        3. Loc
        4. Hazards
        5. Dates
    """
    error_counts = {}
    text = str(text)
    sentences = listify_strings(text)
    if chunk_size:
        chunks = break_down_text(sentences, chunk_size)
        answer_impact_values = []
        valid_errors_impVal = []

        for chunk in chunks:
            answer_impact_values_chunk, valid_errors_impVal_chunk = (
                impact_extraction_chain(
                    str(chunk),
                    impact_types_dict,
                    validate_fields=dedup_fields,
                    validate_impSubtypes=validate_impSubtypes,
                    max_rounds=max_rounds,
                    **groq_kwargs,
                )
            )
            if answer_impact_values_chunk:
                answer_impact_values.extend(answer_impact_values_chunk)
                valid_errors_impVal.extend(valid_errors_impVal_chunk)

    else:
        answer_impact_values, valid_errors_impVal = impact_extraction_chain(
            text,
            impact_types_dict,
            validate_fields=dedup_fields,
            validate_impSubtypes=validate_impSubtypes,
            max_rounds=max_rounds,
            **groq_kwargs,
        )

    answer_impact_values_cleaned = clean_value_unit(
        answer_impact_values, valid_errors_impVal
    )

    # deduplicate impact values
    if dedup_impacts == "all":
        answer_impact_values_cleaned = deduplicate_structured_responses(
            [],
            answer_impact_values_cleaned,
            validate_fields=dedup_fields,
        )
    elif dedup_impacts == "quali":
        quanti_imp = [
            imp
            for imp in answer_impact_values_cleaned
            if imp.get("impactValue") is not None
        ]
        quali_imp = [
            imp
            for imp in answer_impact_values_cleaned
            if imp.get("impactValue") is None
        ]
        quali_imp_dedup = deduplicate_structured_responses(
            [],
            quali_imp,
            validate_fields=dedup_fields,
        )
        answer_impact_values_cleaned = quanti_imp + quali_imp_dedup

    identified_impacts = []
    ## Localize, date and find hazards of each impact value
    for i, impact in enumerate(answer_impact_values_cleaned):

        impact_desc = make_impact_description(
            impact["impactSubtype"],
            impact["impactValue"],
            impact["impactUnit"],
            impact["valueAnnotation"],
        )

        # Extract locations
        answer_loc = extract_locations_for_impact(text, impact_desc, **groq_kwargs)
        impact.update(answer_loc)

        # Extract hazards
        answer_hazards = extract_localization_hazards_for_impact(
            text, impact_desc, answer_loc, hazards_list, validate_hazards, **groq_kwargs
        )
        impact.update(answer_hazards)

        ## Find dates
        if multi_dates:
            # Check if this is qualitative (no impactValue)
            multi_dates_extract = impact.get("impactValue") is None or pd.isna(
                impact.get("impactValue")
            )
        else:
            multi_dates_extract = False

        if multi_dates_extract:
            # For qualitative, extract multiple date pairs
            prompt_impact_dates = build_messages(
                identify_impact_dates_prompt_qualitative(
                    text, impact_desc, answer_loc, hazards=impact.get("hazards")
                )
            )
            _, answer_dates, valid_errors_dates = get_model_response_retry(
                prompt_impact_dates, ImpactDatesMultiple, **groq_kwargs
            )

            if isinstance(answer_dates, dict) and "datePairs" in answer_dates:
                date_pairs = answer_dates["datePairs"]
                # Duplicate impact for each date pair (each carries its own annotation)
                impact_list = duplicate_impact_by_date_pairs(
                    impact, date_pairs, valid_errors_dates
                )
            else:
                LOGGER.info(
                    "Failed to extract multiple date pairs for impact: %s", impact
                )
                if isinstance(answer_dates, list) and len(answer_dates) == 1:
                    answer_dates = answer_dates[0]
                if not isinstance(answer_dates, dict):
                    answer_dates = {
                        "startYear": None,
                        "startMonth": None,
                        "startDay": None,
                        "endYear": None,
                        "endMonth": None,
                        "endDay": None,
                        "dateAnnotation": None,
                    }
                answer_dates["valid_errors_dates"] = valid_errors_dates
                impact.update(answer_dates)
                impact_list = [impact]  # process as single impact without duplication
        else:
            # For quantitative, use single date extraction (existing logic)
            prompt_impact_dates = build_messages(
                identify_impact_dates_prompt(
                    text, impact_desc, answer_loc, hazards=impact.get("hazards")
                )
            )
            _, answer_dates, valid_errors_dates = get_model_response_retry(
                prompt_impact_dates, ImpactDates, **groq_kwargs
            )
            if isinstance(answer_dates, list) and len(answer_dates) == 1:
                answer_dates = answer_dates[0]
            if not isinstance(answer_dates, dict):
                answer_dates = {
                    "startYear": None,
                    "startMonth": None,
                    "startDay": None,
                    "endYear": None,
                    "endMonth": None,
                    "endDay": None,
                    "dateAnnotation": None,
                }
            answer_dates["valid_errors_dates"] = valid_errors_dates
            impact.update(answer_dates)
            impact_list = [impact]  # process as single impact without duplication
        identified_impacts.extend(impact_list)

    return identified_impacts


def extraction_chain_multiprompt_sep(
    text,
    impact_types_dict,
    hazards_list,
    dedup_impacts,
    dedup_fields,
    validate_impSubtypes=True,
    validate_hazards=True,
    max_rounds=5,
    chunk_size=None,
    multi_dates=False,
    **groq_kwargs,
):
    """
    Multiprompt extraction chain with SEPARATE quantitative and qualitative extraction:
        1. Identify impact subtypes from entire text
        2. Extract quantitative impacts (with values and units)
        3. Extract qualitative impacts for each identified subtype

    Args:
        text: The text to extract impacts from
        impact_types_dict: Dictionary of impact types and their descriptions
        hazards_list: List of allowed hazard types
        dedup_fields: Fields to use for deduplication
        validate_impSubtypes: Whether to validate impact subtypes
        validate_hazards: Whether to validate hazard values
        max_rounds: Maximum rounds for continued extraction
        chunk_size: Size of text chunks for processing
        multi_dates: If True, extract multiple date pairs for qualitative impacts;
                    if False, extract single date range for qualitative impacts
        **groq_kwargs: Additional kwargs for API calls

    Returns:
        List of identified impacts (both quantitative and qualitative)
    """
    text = str(text)
    sentences = listify_strings(text)

    LOGGER.info("Step 2: Extracting quantitative impacts...")
    if chunk_size:
        chunks = break_down_text(sentences, chunk_size)
        impact_types = []
        answer_impact_values = []
        valid_errors_impVal = []

        for chunk in chunks:
            (
                impact_types_chunk,
                answer_impact_values_chunk,
                valid_errors_impVal_chunk,
            ) = impact_extraction_chain_quanti(
                str(chunk),
                impact_types,
                validate_fields=dedup_fields,
                validate_impSubtypes=validate_impSubtypes,
                max_rounds=max_rounds,
                **groq_kwargs,
            )
            if impact_types_chunk:
                impact_types.extend(impact_types_chunk)
            if answer_impact_values_chunk:
                answer_impact_values.extend(answer_impact_values_chunk)
                valid_errors_impVal.extend(valid_errors_impVal_chunk)
    else:
        impact_types, answer_impact_values, valid_errors_impVal = (
            impact_extraction_chain_quanti(
                text,
                impact_types,
                validate_fields=dedup_fields,
                validate_impSubtypes=validate_impSubtypes,
                max_rounds=max_rounds,
                **groq_kwargs,
            )
        )
    impact_types = list(set(impact_types))
    answer_impact_values_cleaned = clean_value_unit(
        answer_impact_values, valid_errors_impVal
    )

    # deduplicate impact values
    if dedup_impacts == "all":
        answer_impact_values_cleaned = deduplicate_structured_responses(
            [],
            answer_impact_values_cleaned,
            validate_fields=dedup_fields,
        )
    elif dedup_impacts == "quali":
        quanti_imp = [
            imp
            for imp in answer_impact_values_cleaned
            if imp.get("impactValue") is not None
        ]
        quali_imp = [
            imp
            for imp in answer_impact_values_cleaned
            if imp.get("impactValue") is None
        ]
        quali_imp_dedup = deduplicate_structured_responses(
            [],
            quali_imp,
            validate_fields=dedup_fields,
        )
        answer_impact_values_cleaned = quanti_imp + quali_imp_dedup

    identified_impacts = []
    # Process each quantitative impact
    for i, impact in enumerate(answer_impact_values_cleaned):

        impact_desc = make_impact_description(
            impact["impactSubtype"],
            impact["impactValue"],
            impact["impactUnit"],
            impact["valueAnnotation"],
        )

        # Extract locations
        answer_loc = extract_locations_for_impact(text, impact_desc, **groq_kwargs)
        impact.update(answer_loc)

        # Extract hazards
        answer_hazards = extract_localization_hazards_for_impact(
            text, impact_desc, answer_loc, hazards_list, validate_hazards, **groq_kwargs
        )
        impact.update(answer_hazards)

        # Extract dates (single date range for quantitative)
        answer_dates, _ = extract_dates_for_impact(
            text,
            impact_desc,
            answer_loc,
            is_qualitative=False,
            multi_dates=multi_dates,
            **groq_kwargs,
        )
        impact.update(answer_dates)
        unique_subtype.add(impact["impactSubtype"])
        identified_impacts.append(impact)

    LOGGER.info("Extracted %i quantitative impacts", len(identified_impacts))

    # ===== STEP 3: Extract QUALITATIVE impacts for each identified subtype =====
    LOGGER.info("Step 3: Extracting qualitative impacts for each subtype...")
    for subtype in impact_types:
        LOGGER.info("Extracting qualitative impacts for subtype: %s", subtype)

        # Generic qualitative description for this subtype
        qualitative_impact_desc = f"impacts of type '{subtype}'"

        # Extract locations for this subtype (should capture ALL affected locations)
        answer_loc = extract_locations_for_impact(
            text, qualitative_impact_desc, **groq_kwargs
        )

        if not answer_loc.get("country") or (
            isinstance(answer_loc.get("country"), float)
            and pd.isna(answer_loc.get("country"))
        ):
            LOGGER.info("No locations found for subtype %s, skipping", subtype)
            continue

        # Extract hazards that caused this subtype of impact
        answer_hazards = extract_localization_hazards_for_impact(
            text,
            qualitative_impact_desc,
            answer_loc,
            hazards_list,
            validate_hazards,
            **groq_kwargs,
        )

        # Extract dates for qualitative (single or multiple date pairs depending on multi_dates parameter)
        answer_dates, date_pairs = extract_dates_for_impact(
            text,
            qualitative_impact_desc,
            answer_loc,
            is_qualitative=True,
            multi_dates=multi_dates,  # Use multi_dates to control whether to extract multiple date pairs
            **groq_kwargs,
        )

        # Create qualitative impact record(s)
        qualitative_impact = {
            "impactSubtype": subtype,
            "impactValue": None,
            "impactUnit": None,
            "valueAnnotation": None,
        }
        qualitative_impact.update(answer_loc)
        qualitative_impact.update(answer_hazards)

        # Handle multiple date pairs for qualitative (only if multi_dates=True and date_pairs extracted)
        if multi_dates and date_pairs and isinstance(date_pairs, list):
            impacts_to_add = duplicate_impact_by_date_pairs(
                qualitative_impact, date_pairs, valid_errors_dates
            )
            identified_impacts.extend(impacts_to_add)
            LOGGER.info(
                "Added %i qualitative impacts for subtype %s (multi-date)",
                len(impacts_to_add),
                subtype,
            )
        else:
            # Single date range
            qualitative_impact.update(answer_dates)
            identified_impacts.append(qualitative_impact)
            LOGGER.info(
                "Added 1 qualitative impact for subtype %s (single date)", subtype
            )

    return identified_impacts


def get_event_impacts(
    df_labelled,
    impact_types_dict,
    hazards_list,
    dedup_impacts,
    dedup_fields,
    text_col="nathaz_text",
    validate_impSubtypes=True,
    validate_hazards=True,
    chunk_size=None,
    max_rounds=5,
    res_savename=None,
    multi_dates=False,
    **groq_kwargs,
):
    """Wrapper function to do all level promptings for impact extraction
    Version 3 retrying multilevel prompting

    """
    response = []
    response_df_list = []
    count = 0
    start_time = time.time()
    last_extract_time = start_time
    for rowid, row in df_labelled.iterrows():

        reference_info = {
            "appealCode": row["appealCode"],
            "country_kw": row["location"],
            "reportDate": row["reportDate"],
            "reportLink": row["reportLink"],
            "disasterType": row["disasterType"],
            "nathaz_text": row["nathaz_text"],
        }

        columns = [
            "appealCode",
            "country_kw",
            "reportDate",
            "disasterType",
            "impactValue",
            "impactValuePrecision",
            "impactValueMin",
            "impactValueMax",
            "impactUnit",
            "country",
            "location",
            "startYear",
            "startMonth",
            "startDay",
            "endYear",
            "endMonth",
            "endDay",
            "hazards",
            "impactsAnnotation",
        ]
        data = reference_info
        # query impact, value, loc, date haz altogether

        answer_impacts = extraction_chain_multiprompt(
            row[text_col],
            impact_types_dict,
            hazards_list,
            dedup_impacts=dedup_impacts,
            dedup_fields=dedup_fields,
            max_rounds=max_rounds,
            validate_impSubtypes=validate_impSubtypes,
            validate_hazards=validate_hazards,
            chunk_size=chunk_size,
            multi_dates=multi_dates,
            **groq_kwargs,
        )

        if answer_impacts:
            # further clean-up
            answer_impacts = [
                el for el in answer_impacts if isinstance(el, dict)
            ]  # filter out anything that is not dict or list
            LOGGER.info(
                "Extracted %s impacts identified in %s, %s",
                len(answer_impacts),
                reference_info["appealCode"],
                reference_info["reportDate"],
            )
            now_extract_time = time.time()
            LOGGER.info(
                "Extraction time: %.2f seconds", now_extract_time - last_extract_time
            )
            last_extract_time = now_extract_time
            data = deepcopy(add_key_value_pairs(answer_impacts, data))
            response.append(data)
            # construct df
            new_dfs = pd.concat(
                [pd.DataFrame.from_dict(impdict, orient="index").T for impdict in data],
                axis=0,
            )
        else:
            # if extraction fail, write empty row with reference info
            LOGGER.info(
                "No impacts identified in %s, %s",
                reference_info["appealCode"],
                reference_info["reportDate"],
            )
            new_dfs = pd.DataFrame(columns=columns, data=[reference_info])

        response_df_list.append(new_dfs)
        all_response_df = pd.concat(response_df_list, ignore_index=True, axis=0)
        if res_savename:
            all_response_df.to_csv(DATA_OUT_LLMS / (res_savename + ".csv"), index=False)

    end_time = time.time()
    nreports = len(df_labelled)
    dtime = end_time - start_time
    n_extracted_fields = len(all_response_df) if answer_impacts else 0
    LOGGER.info(
        "%s; time taken: %.2f seconds, , %i fields extracted in %.2f seconds per report",
        MODEL_NAME,
        dtime,
        n_extracted_fields,
        dtime / nreports,
    )

    return (response, all_response_df)
