import pycountry
import pandas as pd
#import json
import numpy as np
import regex as re
import copy as cp
#import ast
import regex as re
import json_repair
from pint import UnitRegistry
#from collections import Counter
from price_parser import Price
from currency_converter import CurrencyConverter, RateNotFoundError
#from shapely import equals

from src import units
from src.text_processing_functions import *
from src.units import *
from src.impact_def import *
from src.hazard_def import *

def country_name_to_iso3(name):
    """
    Convert a country name to its ISO 3 letter code.

    Parameters
    ----------
    name : str
        The name of the country.

    Returns
    -------
    str
        The ISO 3 letter code of the country, or "Unknown" if not found.
    """
    try:
        country = pycountry.countries.lookup(name)
        return country.alpha_3
    except LookupError:
        return "Unknown"
def list_country_name_to_iso3(name):
    """
    Convert a list of country names to their ISO 3 letter codes.

    Parameters
    ----------
    name : list of str
        List of country names.

    Returns
    -------
    list of str
        List of ISO 3 letter codes of the countries, or "Unknown" if not found.
    """
    if isinstance(name, list):
        return [country_name_to_iso3(country) for country in name]
    else:
        return country_name_to_iso3(name)

def separate_locs(locations):
    """Separate locations separated by a comma"""
    if pd.isnull(locations):
        return None
    else:
        return locations.split(",")

def remove_startspace(loc_list):
    """Remove space at start of string"""
    if loc_list is None:
        return None
    else:
        return [loc.strip() for loc in loc_list]

def delistify_cols(df):
    """
    Convert list columns to string columns

    This function takes a DataFrame as argument and iterates over all columns.
    If a column contains any list elements, it converts the whole column to string
    by applying a lambda function to each element. If the element is a list,
    it converts it to string, otherwise it leaves it as is.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to be formatted

    Returns
    -------
    pd.DataFrame
        DataFrame with list columns converted to string columns
    """
    for col in df.columns:
        if np.any([isinstance(cell, list) for cell in df[col]]):
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)
    return df
def listify_strings(x):
    """
    Convert strings to lists if possible

    If a string can be parsed as a list, it is converted to a list. If not,
    the string is wrapped in a list. If the input is already a list, it is
    returned as is. If the input is None or NaN, an empty list is returned.

    Parameters
    ----------
    x : str or list or None or numpy.nan
        Element to be converted

    Returns
    -------
    list
        The converted element
    """
    if isinstance(x, str):
        try :
            #x = json.loads(x.replace("'", '"'))
            x = json_repair.loads(x)
        except :
            x = [x]
        return x
    elif isinstance(x, list):
        return x
    elif pd.isna(x) or x is None:
        return []
    else:
        return x
def format_output(df, num_cols=None, list_cols=None):
    """
    Format output of the final report

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to be formatted
    num_cols : list
        List of columns to be converted to float

    Returns
    -------
    pd.DataFrame
        Formatted DataFrame
    """
    if num_cols:
        #df = df.replace(["null", "None", None], np.nan)
        #df[num_cols] = df[num_cols].astype(float)
        df[num_cols] =df[num_cols].apply(pd.to_numeric, errors='coerce')

    if list_cols:
        df[list_cols] = df[list_cols].map(lambda x: listify_strings(x))
    return df

def parse_impact_value_precision(x):
    """Parse impact values given precision levels.
    Ensures that min are mins, max are maxs.
    """
    # Extract scalars if x is a DataFrame
    if isinstance(x, pd.DataFrame):
        vals = [
            x["impactValueMin"].iloc[0] if "impactValueMin" in x else None,
            x["impactValueMax"].iloc[0] if "impactValueMax" in x else None,
            x["impactValue"].iloc[0] if "impactValue" in x else None,
        ]
    else:  # assume dict or Series-like
        vals = [x.get("impactValueMin"), x.get("impactValueMax"), x.get("impactValue")]

    # Convert all to floats, None → NaN
    all_values = pd.to_numeric(pd.Series(vals), errors="coerce").to_numpy(dtype=float)

    min_value = np.nanmin(all_values)
    max_value = np.nanmax(all_values)

    x["impactValueMin"] = min_value if not pd.isna(vals[0]) else vals[0]
    x["impactValueMax"] = max_value if not pd.isna(vals[1]) else vals[1]
    x["impactValue"]= x["impactValueMax"] if not pd.isna(x["impactValueMax"]) else max_value

    return x
def reclassify_impact_subtype(x, impact_kw_reclass=IMPACT_KEYWORDS):
    """
    Reclassify an impact subtype using a dictionary of regular expressions.

    Parameters
    ----------
    x : pandas.Series
        Row of data to be processed
    impact_kw_reclass : dict
        Dictionary of regular expressions to match against the impact subtype
        Values of the dictionary should be regular expressions to match against the impact subtype
        Keys of the dictionary should be the reclassified impact subtype

    Returns
    -------
    str
        Reclassified impact subtype
    flag : bool
        Flag indicating whether the impact subtype was reclassified
    """
    if x["impactSubtype"] in list(impact_kw_reclass.keys()):
        x["flag_impactSubtype_reclass"] = False
        return x
    candidates = []
    for key, value in impact_kw_reclass.items():
        if re.search(value, x["impactSubtype"], re.IGNORECASE):
            candidates.append(key)
    if len(candidates) == 1:
        new_subtype = candidates[0]
    else:
        new_subtype = "Unknown"
    x["impactSubtype"] = new_subtype
    x["flag_impactSubtype_reclass"] = True
    return x

def reclassify_hazard(x, hazard_kw_reclass):
    """
    Reclassify a hazard type using a dictionary of regular expressions.

    Parameters
    ----------
    x : pandas.Series
        Row of data to be processed
    hazard_kw_reclass : dict
        Dictionary of regular expressions to match against the hazard type
        Values of the dictionary should be regular expressions to match against the hazard type
        Keys of the dictionary should be the reclassified hazard type

    Returns
    -------
    list
        Reclassified hazard type
    """
    corr_haz = cp.deepcopy(x["hazards"])
    flag = False
    if any([haz for haz in x["hazards"] if haz not in hazard_kw_reclass.keys()]):
        flag = True
        for i, haz in enumerate(x["hazards"]):
            if haz not in hazard_kw_reclass.keys():
                candidates = [haz_corr for haz_corr in hazard_kw_reclass.keys() if re.search(hazard_kw_reclass[haz_corr], haz, re.IGNORECASE)]
                if len(candidates) == 1:
                    corr_haz[i] = candidates[0]
                else:
                    corr_haz[i] = "Unknown"
    x["hazards"] = corr_haz
    x["flag_hazards_reclass"] = flag
    return x

def reverse_mapping(hazard_mapping_emdat) :
    """
    Reclassify a hazard type using a dictionary of hazard mapping

    Parameters
    ----------
    hazard_kw_reclass : dict
        Dictionary of with list of hazard types to match against the emdat hazard type
        Values of the dictionary should be list of hazard type
        Keys of the dictionary should be the emdat reclassified hazard type

    Returns
    -------
    dict
        hazard_mapping_emdat Reverse dictionnary to map each hazard type to the corresponding emdat hazard type
    """
    reverse_mapping = {}
    for main, subs in hazard_mapping_emdat.items():
        for s in subs:
            reverse_mapping[s.lower()] = main
    return reverse_mapping

def reclassify_hazard_emdat(x, reverse_hazard_mapping_emdat):
    """
    Reclassify a hazard type using a dictionary of hazard mapping

    Parameters
    ----------
    x : pandas.Series
        Row of data to be processed, it should be a list
    hazard_kw_reclass : dict
        Dictionary of with list of hazard types to match against the emdat hazard type
        Values of the dictionary should be list of hazard type
        Keys of the dictionary should be the emdat reclassified hazard type

    Returns
    -------
    list
        Reclassified hazard type
    """
    # Map the row
    hazard_emdat_mapped = []
    for h in x :
        h_low = h.lower()
        if h_low in reverse_hazard_mapping_emdat:
            hazard_emdat_mapped.append(reverse_hazard_mapping_emdat[h_low])

    # Remove duplicates
    hazard_emdat_mapped = list(set(hazard_emdat_mapped))
    return hazard_emdat_mapped
def harmonize_units(x, harmonize_units_kw=HARMONIZE_UNITS_KW):
    """
    Harmonize units by replacing equivalent units.

    Parameters
    ----------
    x : str
        String containing the unit to be harmonized

    Returns
    -------
    str
        Harmonized unit string

    Notes
    -----
    This function uses a predefined dictionary of unit mappings to replace
    equivalent units. For example, "individuals" is replaced with "people".
    """
    unit = x['impactUnit']
    x["flag_unit_harmonization"] = False
    if not isinstance(unit, str):
        return x  # skip if unit is None or not a string
    unit = unit.strip()
    unit_original = unit
    for target_unit, regex_unit in harmonize_units_kw.items():
        unit = re.sub(regex_unit, target_unit, unit)
        x['impactUnit'] = unit
    if unit != unit_original:
        x["flag_unit_harmonization"] = True
    return x

def convert_unit(x, unit_converter=UNIT_CONVERTER):
    """Convert units that can be converted e.g. families => people"""

    unit = x['impactUnit']
    x["flag_unit_conversion"] = False
    if not isinstance(unit, str):
        return x  # skip if unit is None or not a string
    unit = unit.strip()
    if unit == "":
        return x
    for old_unit_pattern, (conv_fact, new_unit) in unit_converter.items():
        if re.search(old_unit_pattern, unit, re.IGNORECASE) and not re.search(r"\b(people)\b", unit, re.IGNORECASE): #avoid conversion when people already in unit e.g. people per household
            x["flag_unit_conversion"] = True
            for key in ["impactValueMin", "impactValueMax", "impactValue"]:
                try:
                    x[key] = float(x[key]) #force conversion to float
                    x[key] = conv_fact*x[key]
                    x["impactUnit"] = re.sub(old_unit_pattern, new_unit, unit) #replace unit with new_unit
                except Exception as e:
                    print(f"Skipping unit conversion for row due to error: {e}")
    return x

## assign_unit_type is redundant with standardize_metric_units, could simplified and removed
def assign_unit_type(x, unit_type_kw_reclass=UNIT_TYPE_KW_RECLASS):
    """Detect if dimension of unit can be identified e.g. length, mass,...
       Default to "other"
    """
    unit = str(x["impactUnit"]).lower() #ensure unit is string
    flag = False
    candidates = [unit_type for unit_type in unit_type_kw_reclass.keys() if re.search(unit_type_kw_reclass[unit_type], unit, re.IGNORECASE)]
    if len(candidates) == 1:
        unit_type = candidates[0]
    elif len(candidates) == 0:
        unit_type = "other"
    else:
        unit_type = "multiple"
        flag = True
    x["unit_type"] = unit_type
    x["flag_unit_type"] = flag
    return x

def reclassify_units(x, unit_kw_reclass=UNIT_KW_RECLASS, expected_unit_subtype=IMPACT_EXPECTED_UNITS, default_subtype_unit=IMPACT_DEFAULT_UNITS, force_unit_to_subtype=True, reclass_subtype=True):
    """
    Reclassify units based on keywords

    Parameters
    ----------
    x : pd.Series
        row of pandas dataframe
    unit_kw_reclass : dict
        dictionary of unit keywords and corresponding unit strings
    default_subtype_unit : dict
        dictionary of default subtype units
    force_unit_to_subtype : bool
        whether or not to force unit to default unit of subtype when unknown unit

    Returns
    -------
    str
        reclassified unit
    """
    unit = str(x["impactUnit"]).lower() #ensure unit is string
    unit_type = x['unit_type']
    flag_unit_nonstd = False
    flag_reclass_subtype_from_unit = False
    unit_prefix = f"{unit_type} of " if unit_type != "other" else ""
    candidates = [unit_corr for unit_corr in unit_kw_reclass.keys() if re.search(unit_kw_reclass[unit_corr], unit, re.IGNORECASE)]
    if len(candidates) == 1:
        reclass_unit = unit_prefix+candidates[0]
    else:
        if len(candidates) > 1:
            print(f"Multiple candidates found for {unit}: {candidates}")
        flag_unit_nonstd = True
        #no unit identified, infer unit from category
        if force_unit_to_subtype and x["impactSubtype"] != "Unknown":
            reclass_unit = unit_prefix+default_subtype_unit[x["impactSubtype"]]
        else:
            reclass_unit = unit
    if reclass_subtype:
        possible_subtypes = [subtype for subtype in expected_unit_subtype.keys() if reclass_unit == expected_unit_subtype[subtype]] #re.search(expected_unit_subtype[subtype], x["impactSubtype"], re.IGNORECASE)]
        if len(possible_subtypes) == 1 and (possible_subtypes[0] != x["impactSubtype"]):
            flag_reclass_subtype_from_unit = True
            print(f"Reclassified subtype from {x['impactSubtype']} to {possible_subtypes[0]} with unit reclass {reclass_unit} and orig unit {unit}")
            #print(x["valueAnnotation"])
            x["impactSubtype"] = possible_subtypes[0]
    x["impactUnit"] = reclass_unit
    x["flag_unit_nonstd"] = flag_unit_nonstd
    x["flag_reclass_subtype_from_unit"] = flag_reclass_subtype_from_unit
    return x

def standardize_metric_units(x, std_unit_kw_reclass=METRIC_UNIT_KW_RECLASS, unit_mapping=METRIC_UNIT_MAPPING):
    """Standardize units to a common baseline in text"""
    values = x[["impactValueMin", "impactValue", "impactValueMax"]].values.tolist()
    unit = x["impactUnit"]
    if (pd.isna(x["impactUnit"]) or x["impactUnit"] is None):
        x["flag_unit_standardization"] = False
        return x
    ureg = UnitRegistry()
    #print(f"{value} {unit}")
    identified_units = []
    identified_patterns = []
    for target_unit, unit_patterns in std_unit_kw_reclass.items():
        for pattern in unit_patterns:
            if re.search(pattern, unit, re.IGNORECASE):
                identified_units.append(target_unit)
                identified_patterns.append(pattern)
    #matched = [(target_unit, unit_patterns) for target_unit, unit_patterns in std_unit_kw_reclass.items() if np.any([re.search(pattern, unit, re.IGNORECASE) for pattern in unit_patterns])]
    if len(identified_units) == 0:
        x["flag_unit_standardization"] = False
        return x
    elif len(identified_units) > 1:
        raise ValueError(f"Multiple potential units found for token: {unit}")
    identified_unit = identified_units[0]
    identified_pattern = identified_patterns[0]
    si_unit = unit_mapping[identified_unit]

    # Perform conversion
    converted_unit = re.sub(identified_pattern, si_unit, unit)
    converted_values = []
    for value in values:
        quantity = float(value) * ureg(identified_unit)
        converted_quantity = quantity.to(si_unit)
        converted_values.append(converted_quantity.magnitude)

    x["impactValueMin"] = converted_values[0]
    x["impactValue"] = converted_values[1]
    x["impactValueMax"] = converted_values[2]
    x["impactUnit"] = converted_unit
    x["flag_unit_standardization"] = True
    return x

def normalize_people_unit(x):
    """
    Normalize people unit (e.g.) deaths to people.

    Parameters
    ----------
    x : pandas.Series
        The series containing the extracted data

    Returns
    -------
    pandas.Series
        The series with the normalized unit
    """
    unit = x["impactUnit"]
    if not isinstance(unit, str):
        return x  # skip if unit is None or not a string
    if re.search(PEOPLE_NORMALIZER, unit, re.IGNORECASE):
        x["impactUnit"] = "people"
    return x

def join_value_units(x):
        return str(x["impactValue"]) +  "," + str(x["impactUnit"])

def split_value_units(x):
    return x["value_unit"].split(",")

def money_converter(value_parsed, unit_parsed, report_date, flag, DEF_CUR="EUR"):
    try:
        value_parsed = CurrencyConverter().convert(value_parsed, unit_parsed, DEF_CUR, date=report_date)
        unit_parsed = DEF_CUR
    except RateNotFoundError as e:
        print(str(e) + "; using default conversion rate")
        try:
            value_parsed = CurrencyConverter().convert(value_parsed, unit_parsed, DEF_CUR)
            unit_parsed = DEF_CUR
        except Exception as e:
            print(f"Fallback failed: {e}")
            flag = True
    except Exception as e:
        print(f"General conversion error: {e}")
        flag = True
    return value_parsed, unit_parsed, flag

def convert_monetary_units(x):
    """
    Convert units that are currencies to a common baseline (EUR) by parsing the string
    and using a currency converter.

    Parameters
    ----------
    x : pd.Series
        row of dataframe with columns "impactValue", "impactUnit", and "reportDate"

    Returns
    -------
    pd.Series
        modified row with converted value and unit
    """
    DEF_CUR = "EUR"
    value_labels = ["impactValueMin", "impactValue", "impactValueMax"]
    unit_raw = x["impactUnit"]
    report_date = pd.to_datetime(x["reportDate"])
    values_parsed = {}
    units_parsed = []
    flag_failed_conversion = False
    for value_label in value_labels:
        value_raw = x[value_label]
        parsed_price = Price.fromstring(f'{value_raw} {unit_raw}')
        unit_parsed = parsed_price.currency
        value_parsed = parsed_price.amount_float
        if unit_parsed and value_parsed:#if monetary unit is identified, try to convert it to default currency
            values_parsed[value_label], unit_parsed, flag_failed_conversion = money_converter(value_parsed, unit_parsed, report_date, flag_failed_conversion, DEF_CUR)
            units_parsed.append(unit_parsed)
        else:
            values_parsed[value_label] = value_raw

    if len(pd.unique(units_parsed)) > 1:#only do assignment if all units are the same
        print(f"Multiple units parsed: {units_parsed}")
        flag_failed_conversion = True
    elif len(pd.unique(units_parsed)) == 1:
        for value_label in value_labels:
            x[value_label] = values_parsed[value_label]
        x["impactUnit"] = units_parsed[0]

    x["flag_currency_conversion"] = flag_failed_conversion
    return x

def replace_numbers_unit(x):
    """
    Move numbers from impactUnit to impactValue

    Args:
        text_in (str): The text to replace numbers in.

    Returns:
        str: The text with numbers replaced.
    """
    nlp = spacy.load("en_core_web_sm")
    unit = x["impactUnit"]
    if (pd.isna(unit) or unit is None):
        x["flag_reformat_unit"] = False
        return x

    # Process the text
    doc = nlp(unit)

    # Reconstruct text by replacing numbers
    modified_tokens = []
    id_number = None
    last_token_modified = False
    for token in doc:
        #first replace written-out numbers
        if written_num(token.text) and token.pos_ != "PROPN": #must not be part of a proper noun
            id_number = float(text2num(token.text, "en"))
            #if the previous token is a number replace by the multiple of the two numbers
            prev_token = take_n_neighb_tokens(token, -1) #nlp.tokenizer(modified_tokens[-1])[0] if len(modified_tokens) > 0 else None
            prev_token = prev_token[0] if prev_token else None
            if last_token_modified or (prev_token and is_float_digit(prev_token.text)):#and could_be_unit(next_tokens) do not necessarily ask to be a unit?
                if modified_tokens[-1] == " ": #remove whitespace
                    modified_tokens.pop()
                prev_number = float(modified_tokens.pop())
                id_number *= prev_number
            last_token_modified = True #mark that the last token was modified

        else: #if no number identified, keep as is
            modified_tokens.append(token.text)
            last_token_modified = False

        if token.whitespace_:#keep whitespace
            modified_tokens.append(token.whitespace_)

    #join tokens back to unit
    cleaned_unit = "".join(modified_tokens)

    # try to parse new value
    #keep id_number first if there was no impactValue at first else keep impactValue if no id_number
    impact_values = x[["impactValueMin", "impactValue", "impactValueMax"]].values.tolist()
    if id_number:
        new_imp_values = [id_number*impact_value if not pd.isna(impact_value) else id_number for impact_value in impact_values]
        flag_reformat_unit = True
    else: #keep impactValue if no id_number
        new_imp_values = impact_values
        flag_reformat_unit = False
    x["impactValueMin"] = new_imp_values[0]
    x["impactValue"] = new_imp_values[1]
    x["impactValueMax"] = new_imp_values[2]
    x["impactUnit"] = cleaned_unit
    x["flag_reformat_unit"] = flag_reformat_unit
    return x

def make_date(report_df):
    """
    Make start and end dates from the separate columns in the report DataFrame.

    Parameters
    ----------
    report_df : DataFrame
        The DataFrame containing the report data.

    Returns
    -------
    DataFrame
        The DataFrame with the new columns "startDate" and "endDate".
    """
    def get_date(df, prefix):
        year = df[f'{prefix}Year']
        month = df[f'{prefix}Month']
        day = df[f'{prefix}Day']

        if pd.isna(year) or year is None:
            return ""
        elif pd.isna(month) or month is None:
            return f"{int(df[f'{prefix}Year'])}"
        elif pd.isna(day) or day is None:
            return f"{int(df[f'{prefix}Year'])}-{int(df[f'{prefix}Month'])}"
        return f"{int(df[f'{prefix}Year'])}-{int(df[f'{prefix}Month'])}-{int(df[f'{prefix}Day'])}"

    report_df["startDate"] = report_df.apply(lambda x: get_date(x, prefix='start'), axis=1)
    report_df["endDate"] = report_df.apply(lambda x: get_date(x, prefix='end'), axis=1)
    return report_df
