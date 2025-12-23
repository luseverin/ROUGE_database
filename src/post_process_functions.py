import pycountry
import pandas as pd
import numpy as np
import regex as re
import copy as cp
import regex as re
from pint import UnitRegistry
from currency_converter import CurrencyConverter, RateNotFoundError
import logging

from src import units
from src.text_processing_functions import *
from src.units import *
from src.impact_def import *
from src.hazard_def import *

#load spacy nlp
nlp = spacy.load("en_core_web_sm")
# set up logger
LOGGER = logging.getLogger("postprocessing")

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
        x["flag_unknown_subtype"] = False
        return x
    candidates = []
    for key, value in impact_kw_reclass.items():
        if re.search(value, x["impactSubtype"], re.IGNORECASE):
            candidates.append(key)
    if len(candidates) == 1:
        unknown_subtype = False
        new_subtype = candidates[0]
    else:
        unknown_subtype = True
        new_subtype = "Unknown"
    x["impactSubtype"] = new_subtype
    x["flag_impactSubtype_reclass"] = True
    x["flag_unknown_subtype"] = unknown_subtype
    return x


def reclassify_hazard(x, hazard_kw_reclass=hazard_kw_reclass):
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
def merge_impact_subtypes(x, impact_kw_reclass=IMPACT_SUBTYPE_MERGER):
    candidates = []
    for key, value in impact_kw_reclass.items():
        if re.search(value, x["impactSubtype"], re.IGNORECASE):
            candidates.append(key)
    if len(candidates) == 1:
        x["impactSubtype"] = candidates[0]
        x["flag_impactSubtype_merged"] = True
    else:
        x["flag_impactSubtype_merged"] = False
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

def convert_unit(x, unit_converter=UNIT_CONVERTER, default_unit_dict=IMPACT_DEFAULT_UNITS):
    """Convert units that can be converted e.g. families => people"""

    unit = x['impactUnit']
    x["flag_unit_conversion"] = False
    x["flag_unit_conversion_error"] = False
    if not isinstance(unit, str):
        return x  # skip if unit is None or not a string
    elif pd.isnull(unit) or unit in ["", "null"]:
        return x  # skip if unit is null or empty
    default_unit_subtype = default_unit_dict.get(x["impactSubtype"], None)

    if default_unit_subtype != "people":
        return x  # skip conversion if default unit for subtype is not people
    conv_val = {}
    for old_unit_pattern, (conv_fact, new_unit) in unit_converter.items():
        if re.search(old_unit_pattern, unit, re.IGNORECASE) and not re.search(r"\b(people)\b", unit, re.IGNORECASE): #avoid conversion when people already in unit e.g. people per household
            x["flag_unit_conversion"] = True
            try:
                for key in ["impactValueMin", "impactValueMax", "impactValue"]:
                    conv_val[key] = float(x[key]) #force conversion to float
                    conv_val[key] = conv_fact*conv_val[key]
                x["impactUnit"] = re.sub(old_unit_pattern, new_unit, unit) #replace unit with new_unit
                for key in ["impactValueMin", "impactValueMax", "impactValue"]:#do assignement after all conversions to avoid partial conversion
                    x[key] = conv_val[key]
                x["flag_unit_conversion_error"] = False
            except Exception as e:
                LOGGER.error("Skipping unit conversion for row due to error: %s", e)
                x["flag_unit_conversion_error"] = True
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

def re_match_overlaps(m1, m2):
    a_start, a_end = m1.span()
    b_start, b_end = m2.span()
    return max(a_start, b_start) < min(a_end, b_end)  # strict overlap
def reclassify_units(x, unit_kw_reclass=UNIT_KW_RECLASS):
    """
    Reclassify units based on keywords

    Parameters
    ----------
    x : pd.Series
        row of pandas dataframe
    unit_kw_reclass : dict
        dictionary of unit keywords and corresponding unit strings

    Returns
    -------
    str
        reclassified unit
    """
    unit = str(x["impactUnit"]).lower() #ensure unit is string
    unit_type = x['unit_type']
    x["flag_non-SI_unit_standardization_error"] = False
    unit_prefix = f"{unit_type} of " if unit_type != "other" else ""
    candidates = [unit_corr for unit_corr in unit_kw_reclass.keys() if re.search(unit_kw_reclass[unit_corr], unit, re.IGNORECASE)]
    if len(candidates) == 1:
        reclass_unit = unit_prefix+candidates[0]
    else:
        if len(candidates) > 1:
            LOGGER.warning("Multiple candidates found for %s: %s", unit, candidates)
            x["flag_non-SI_unit_standardization_error"] = True
        reclass_unit = unit
    x["flag_non-SI_unit_standardization"] = (reclass_unit != unit)
    x["impactUnit"] = reclass_unit
    return x
def force_unit_to_subtype(x, default_subtype_unit=IMPACT_DEFAULT_UNITS):
    """
    Force unit to default unit of subtype when unknown unit

    Parameters
    ----------
    x : pd.Series
        row of pandas dataframe
    expected_unit_subtype : dict
        dictionary of expected unit for each subtype

    Returns
    -------
    str
        reclassified unit
    """
    unit = str(x["impactUnit"]).lower() #ensure unit is string
    x["flag_force_unit_to_subtype"] = False
    unit_type = x['unit_type']
    no_reclass = ["null", "", "people"]
    if pd.isnull(unit) or unit in no_reclass:
        return x

    unit_prefix = f"{unit_type} of " if unit_type != "other" else ""
    if x["impactSubtype"] != "Unknown":
        reclass_unit = unit_prefix+default_subtype_unit[x["impactSubtype"]]
        LOGGER.info("Forcing unit from %s to %s for subtype %s", unit, reclass_unit, x['impactSubtype'])
        x["flag_force_unit_to_subtype"] = True
    else:
        reclass_unit = unit
    x["impactUnit"] = reclass_unit
    return x
def reclass_subtype_from_unit(x, expected_unit_subtype=IMPACT_EXPECTED_UNITS):
    """
    Reclassify subtype based on unit

    Parameters
    ----------
    x : pd.Series
        row of pandas dataframe
    expected_unit_subtype : dict
        dictionary of expected unit for each subtype

    Returns
    -------
    str
        reclassified subtype
    """
    unit = str(x["impactUnit"]).lower() #ensure unit is string
    no_reclass = ["null", "", "people"]
    x["flag_reclass_subtype_from_unit"] = False
    if pd.isnull(unit) or unit in no_reclass:
        return x
    possible_subtypes = [subtype for subtype in expected_unit_subtype.keys() if unit == expected_unit_subtype[subtype]]
    if len(possible_subtypes) == 1 and (possible_subtypes[0] != x["impactSubtype"]):
        x["flag_reclass_subtype_from_unit"] = True
        LOGGER.info("Reclassified subtype from %s to %s with unit %s", x['impactSubtype'], possible_subtypes[0], unit)
        x["impactSubtype"] = possible_subtypes[0]
    return x

def standardize_metric_units(x, std_unit_kw_reclass=METRIC_UNIT_KW_RECLASS, unit_mapping=METRIC_UNIT_MAPPING):
    """Standardize units to a common baseline in text"""
    value_labels = ["impactValueMin", "impactValue", "impactValueMax"]
    unit = x["impactUnit"]
    x["flag_SI_unit_standardization"] = False
    x["flag_SI_unit_standardization_error"] = False
    if (pd.isna(x["impactUnit"]) or x["impactUnit"] is None):
        return x
    ureg = UnitRegistry()
    
    identified_units = []
    identified_patterns = []
    for target_unit, unit_patterns in std_unit_kw_reclass.items():
        for pattern in unit_patterns:
            if re.search(pattern, unit, re.IGNORECASE):
                identified_units.append(target_unit)
                identified_patterns.append(pattern)
    #matched = [(target_unit, unit_patterns) for target_unit, unit_patterns in std_unit_kw_reclass.items() if np.any([re.search(pattern, unit, re.IGNORECASE) for pattern in unit_patterns])]
    if len(identified_units) == 0:
        x["unit_type"] = "other"
        return x
    elif len(identified_units) > 1:
        LOGGER.warning("Multiple potential units found for token %s, identified units %s. Not standardizing", unit, identified_units)
        x["flag_SI_unit_standardization"] = True
        x["flag_SI_unit_standardization_error"] = True
        x["unit_type"] = "multiple"
        return x

    x["flag_SI_unit_standardization"] = True
    identified_unit = identified_units[0]
    identified_pattern = identified_patterns[0]
    si_unit = unit_mapping[identified_unit]

    # Perform conversion
    converted_unit = re.sub(identified_pattern, si_unit, unit)
    converted_values = {}
    for value_label in value_labels:
        try:
            quantity = float(x[value_label]) * ureg(identified_unit)
            converted_quantity = quantity.to(si_unit)
            converted_values[value_label] = converted_quantity.magnitude
        except Exception as e:
            LOGGER.error("Unit conversion error: %s", e)
            x["flag_SI_unit_standardization"] = True
            converted_values[value_label] = x[value_label]
    #assign values only if no error occured
    if not x["flag_SI_unit_standardization_error"]:
        for value_label in value_labels:
            x[value_label] = converted_values[value_label]
    x["unit_type"] = si_unit
    x["impactUnit"] = converted_unit
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
    x["flag_people_unit_normalization"] = False
    if not isinstance(unit, str):
        return x  # skip if unit is None or not a string
    if re.search(PEOPLE_NORMALIZER, unit, re.IGNORECASE):
        x["impactUnit"] = "people"
        x["flag_people_unit_normalization"] = True
    return x

def join_value_units(x):
        return str(x["impactValue"]) +  "," + str(x["impactUnit"])

def split_value_units(x):
    return x["value_unit"].split(",")

def money_converter(value_parsed, unit_parsed, report_date, DEF_CUR="EUR"):
    """
    Convert a monetary value to a standard currency (DEF_CUR) at a given report date.

    Parameters
    ----------
    value_parsed : float
        The monetary value to convert
    unit_parsed : str
        The unit of the monetary value to convert
    report_date : datetime
        The report date at which to perform the conversion
    DEF_CUR : str, optional
        The default currency to convert to. Defaults to "EUR".

    Returns
    -------
    tuple
        A tuple containing the converted monetary value, the converted unit, and a flag indicating whether any errors occurred during the conversion.
    """
    flag = False
    try:
        value_parsed = CurrencyConverter().convert(value_parsed, unit_parsed, DEF_CUR, date=report_date)
        unit_parsed = DEF_CUR
    except RateNotFoundError as e:
        LOGGER.warning("%s; using default conversion rate", e)
        try:
            value_parsed = CurrencyConverter().convert(value_parsed, unit_parsed, DEF_CUR)
            unit_parsed = DEF_CUR
        except Exception as e:
            LOGGER.error("Fallback default rate money_converter failed: %s", e)
            flag = True
    except Exception as e:
        LOGGER.error(f"General money_converter error: %s", e)
        flag = True
    return value_parsed, unit_parsed, flag

def convert_monetary_units(x, currency_dict=CURRENCY_CONVERTER, DEF_CUR="EUR"):
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
    value_labels = ["impactValueMin", "impactValue", "impactValueMax"]
    unit_raw = x["impactUnit"]
    report_date = pd.to_datetime(x["reportDate"])
    x["flag_currency_conversion"] = False
    x["flag_failed_currency_conversion"] = False
    values_converted = {}
    units_converted = []
    #try to identify currency from impactUnit
    id_currencies = [curr for curr, pattern in currency_dict.items() if re.search(pattern, unit_raw, re.IGNORECASE)]
    if len(id_currencies) == 0:
        return x
    elif len(id_currencies) > 1:
        LOGGER.warning("Multiple potential currencies found for token %s, identified currencies %s. Not converting", unit_raw, id_currencies)
        x["flag_failed_currency_conversion"] = True
        return x
    else:
        unit_parsed = id_currencies[0]
    flag_failed_conversion = False
    for value_label in value_labels:
        value_raw = x[value_label]
        if not pd.isnull(value_raw) and not pd.isna(value_raw):#if monetary unit is identified, try to convert it to default currency
            values_converted[value_label], unit_converted, flag_failed_conversion = money_converter(value_raw, unit_parsed, report_date, DEF_CUR=DEF_CUR)
            units_converted.append(unit_converted)
        else:
            values_converted[value_label] = value_raw

    if len(pd.unique(units_converted)) > 1:#only do assignment if all units are the same
        LOGGER.warning("Multiple units parsed: %s", units_converted)
        flag_failed_conversion = True
    elif len(pd.unique(units_converted)) == 1:
        for value_label in value_labels:
            x[value_label] = values_converted[value_label]
        x["impactUnit"] = units_converted[0]

    x["flag_currency_conversion"] = True
    x["flag_failed_currency_conversion"] = flag_failed_conversion
    return x

def replace_numbers_unit(x):
    """
    Move numbers from impactUnit to impactValue

    Args:
        text_in (str): The text to replace numbers in.

    Returns:
        str: The text with numbers replaced.
    """
    unit = x["impactUnit"]
    x["flag_remove_number_unit"] = False
    x["flag_remove_number_unit_error"] = False
    if (pd.isna(unit) or unit is None):
        return x

    # Process the text
    doc = nlp(unit)

    # Reconstruct text by replacing numbers
    modified_tokens = []
    id_number = None
    last_token_modified = False
    for token in doc:
        #first replace written-out numbers
        if (written_num(token.text) or token.is_digit) and not looks_like_proper_name(token): #must not be part of a proper noun
            x["flag_remove_number_unit"] = True
            try:
                id_number = float(text2num(token.text, "en"))
            except ValueError:
                try:
                    id_number = float(token.text)
                except ValueError:
                    LOGGER.warning("Failed to convert %s to number.", token.text)
                    x["flag_remove_number_unit_error"] = True
                    modified_tokens.append(token.text)
                    last_token_modified = False
                    if token.whitespace_:#keep whitespace
                        modified_tokens.append(token.whitespace_)
                    continue
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
    cleaned_unit = cleaned_unit.strip()

    # try to parse new value
    #keep id_number first if there was no impactValue at first else keep impactValue if no id_number
    value_labels = ["impactValueMin", "impactValue", "impactValueMax"]
    if id_number:
        for value_label in value_labels:
            new_value = id_number * x[value_label] if not pd.isna(x[value_label]) else x[value_label]
            x[value_label] = new_value

    x["impactUnit"] = cleaned_unit
    return x

def label_quanti_quali(x):
    """
    Label a column "quanti" in a DataFrame x based on the existence of values in the "impactValue" column.

    Parameters
    ----------
    x : DataFrame
        The DataFrame to be labeled.

    Returns
    -------
    DataFrame
        The DataFrame with the added "quanti" column.

    Notes
    -----
    The "quanti" column is labeled as "quanti" if the "impactValue" column has a value, and "quali" otherwise.
    """
    quanti = pd.notnull(x["impactValue"])
    if quanti:
        x["quanti"] = "quanti"
    else:
        x["quanti"] = "quali"
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

def merge_annotations(x, annotation_cols):
    """
    Merge multiple annotation columns into a single column.

    Parameters
    ----------
    x : pd.Series
        Row of the DataFrame containing the annotation columns.
    annotation_cols : list
        List of annotation column names to be merged.

    Returns
    -------
    str
        Merged annotations as a single string.
    """
    annotations = []
    for col in annotation_cols:
        if col not in x.index:
            continue
        val = x[col]
        if val is None:
            continue
        # handle iterables (lists/arrays/Series) and scalars
        if isinstance(val, (list, tuple, np.ndarray, pd.Series)):
            for item in val:
                if pd.notnull(item):
                    annotations.append(str(item))
        else:
            if pd.notnull(val):
                annotations.append(str(val))
    # keep unique preserving order
    seen = set()
    unique_ann = []
    for a in annotations:
        if a not in seen:
            seen.add(a)
            unique_ann.append(a)
    return unique_ann