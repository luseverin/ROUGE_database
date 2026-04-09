# Functions to extract data with LLMs
import time
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
                full_response_formatted, structured_response
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


def deduplicate_structured_responses(prev_responses, new_responses):
    """Function to check for duplicate responses. Returns a list of unique responses."""
    new_unique_responses = []
    seen = set(
        [
            (
                entry["impactSubtype"],
                entry["impactValue"],
                entry["impactUnit"],
                # tuple(entry.get("location") or []),
                # tuple(entry.get("country") or []),
                # tuple(entry.get("hazards") or [])
            )
            for entry in prev_responses
        ]
    )

    for new_entry in new_responses:
        entry_key = (
            new_entry["impactSubtype"],
            new_entry["impactValue"],
            new_entry["impactUnit"],
            # tuple(new_entry.get("location") or []),
            # tuple(new_entry.get("country") or []),
            # tuple(new_entry.get("hazards") or []),
        )
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
    Extracts the impact value from the impact dictionary.
    """
    impact_cols = [
        col
        for col in impact
        if col in ["impactValue", "impactValueMin", "impactValueMax"]
    ]
    return impact[impact_cols].max().max()


def impact_extraction_chain(
    text,
    impact_types_dict,
    validate_impSubtypes=True,
    max_rounds=5,
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
    if not answer_impact_types or not len(answer_impact_types):
        LOGGER.info("No impact types identified. Stopping extraction.")
        return None, 0
    impact_types = answer_impact_types["impactSubtypes"]

    ## Identify impact values
    prompt_value_unit = identify_value_unit_prompt(text, impact_types)
    ImpactValue.set_allowed_subtypes(impact_types)
    if not validate_impSubtypes:
        ImpactValue.turn_off_impactSubtypes_validation()

    answer_impact_values, valid_errors_impVal = get_model_response_retry_continue(
        prompt_value_unit, ImpactValueList, max_rounds=max_rounds, **groq_kwargs
    )
    return answer_impact_values, valid_errors_impVal


def extraction_chain(
    text,
    impact_types_dict,
    hazards_list,
    validate_impSubtypes=True,
    validate_hazards=True,
    max_rounds=5,
    chunk_size=None,
    **groq_kwargs,
):
    """
    Multiprompt extraction chain with following sequence
        1. Type
        2. Value unit
        3. Loc
        4. Dates
        5. Hazards
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
            validate_impSubtypes=validate_impSubtypes,
            max_rounds=max_rounds,
            **groq_kwargs,
        )
    identified_impacts = []

    # deduplicate impact values
    answer_impact_values = deduplicate_structured_responses([], answer_impact_values)

    ## Localize, date and find hazards of each impact value
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

        # track errors in impact extraction
        impact.update({"valid_errors_impactValue": valid_errors_impVal[i]})

        # extract impact value
        try:
            impact_value = extract_impact_value(pd.DataFrame([impact]))
        except TypeError as e:
            LOGGER.info("Error occurred while extracting impact value: %s", e)
            continue

        impact_unit = impact["impactUnit"]
        impact_desc = make_impact_description(impact, impact_value, impact_unit)

        ## Find locs
        prompt_impact_loc = build_messages(
            identify_impact_loc_prompt(text, impact_desc)
        )
        _, answer_loc, valid_errors_loc = get_model_response_retry(
            prompt_impact_loc, ImpactLocation, **groq_kwargs
        )
        if isinstance(answer_loc, list) and len(answer_loc) == 1:
            answer_loc = answer_loc[0]
        if not isinstance(answer_loc, dict):
            answer_loc = {"country": None, "location": None, "locationAnnotation": None}
        answer_loc["valid_errors_loc"] = valid_errors_loc
        impact.update(answer_loc)

        ## Find dates
        prompt_impact_dates = build_messages(
            identify_impact_dates_prompt(text, impact, answer_loc)
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

        ## Find hazards
        prompt_impact_hazards = build_messages(
            identify_impact_hazards_prompt(
                text, impact_desc, answer_loc, answer_dates, hazards_list
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
        impact.update(answer_hazards)

        identified_impacts.append(impact)

    return identified_impacts


def get_event_impacts_multiprompt(
    df_labelled,
    impact_types_dict,
    hazards_list,
    text_col="nathaz_text",
    validate_impSubtypes=True,
    validate_hazards=True,
    chunk_size=None,
    max_rounds=5,
    res_savename=None,
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

        answer_impacts = extraction_chain(
            row[text_col],
            impact_types_dict,
            hazards_list,
            max_rounds=max_rounds,
            validate_impSubtypes=validate_impSubtypes,
            validate_hazards=validate_hazards,
            chunk_size=chunk_size,
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
