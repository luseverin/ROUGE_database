import pandas as pd
import numpy as np
import json_repair

BASE_EXTRACT_COLS = [  # columns to be extracted in the initial extraction step
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

NUM_COLS = [
    "impactValue",
    "impactValueMin",
    "impactValueMax",
    "startYear",
    "startMonth",
    "startDay",
    "endYear",
    "endMonth",
    "endDay",
    "valid_errors_impactValue",
    "valid_errors_loc",
    "valid_errors_dates",
    "valid_errors_haz",
]

LIST_COLS = [
    "valueAnnotation",
    "country",
    "country_kw",
    "location",
    "hazards",
    "locationAnnotation",
    "dateAnnotation",
    "hazardsAnnotation",
    "annotation",
    "sourceExcerpts",
    "country_iso3",
    "nathaz_text",
    "locationOsm",
    "locationPolygon",
    "continent",
    "iso3_code",
]

ANNOTATION_COLS = [
    "valueAnnotation",
    "locationAnnotation",
    "dateAnnotation",
    "hazardsAnnotation",
]

# final target data cols
FINAL_DATA_COLS = [
    "appealCode",
    "reportDate",
    "reportLink",
    "disasterType",
    "impactSubtype",
    "impactValue",
    "impactValueMin",
    "impactValueMax",
    "impactValuePrecision",
    "impactUnit",
    "startYear",
    "startMonth",
    "startDay",
    "endYear",
    "endMonth",
    "endDay",
    "hazards",
    "location",
    "geometry",
    "locationPolygon",
    "locationLowestAdmin",
    "iso3_code",
    "sourceExcerpts",
]

# final target flag cols
FINAL_FLAG_COLS = [
    "valid_errors_impactValue",
    "valid_errors_loc",
    "valid_errors_dates",
    "valid_errors_haz",
    "flag_value_not_in_text",
    "flag_impactSubtype_reclass",
    "flag_hazards_reclass",
    "flag_remove_number_unit",
    "flag_SI_unit_standardization",
    "flag_non-SI_unit_standardization",
    "flag_unit_processing_error",
    "flag_unit_nonstd",
    "flag_reclass_subtype_from_unit",
    "flag_pop_cntry",
    "flag_value_no_unit",
    "flag_partial_unit",
    "flag_nomin_no_result",
    "flag_nomin_sim_below_th",
    "flag_nomin_translate",
    "flag_location_to_country",
    "flag_osm_polygon",
]


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
        try:
            x = json_repair.loads(x)
        except:
            x = [x]
        return x
    elif isinstance(x, list):
        return x
    elif pd.isna(x) or x is None:
        return []
    else:
        return x


def format_output(df, num_cols=NUM_COLS, list_cols=LIST_COLS):
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
    num_cols = [key for key in df.columns if key in NUM_COLS]
    list_cols = [key for key in df.columns if key in LIST_COLS]
    # test that num and list do not overlap
    overlap = set(num_cols).intersection(set(list_cols))
    if len(overlap) > 0:
        raise ValueError(f"Columns {overlap} are in both num_cols and list_cols")
    if num_cols:
        df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

    if list_cols:
        df[list_cols] = df[list_cols].map(lambda x: listify_strings(x))
    return df
