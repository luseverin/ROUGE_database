import numpy as np
import pandas as pd

MODEL_NAMES_MAP = {  # short names for model
    "meta-llama_llama-4-scout-17b-16e-instruct": "instruct",
    "llama-3.1-8b-instant": "instant",
    "llama-3.3-70b-versatile": "versatile",
}


def detect_annotation_cols(df):
    """Detect annotation columns in the dataframe based on column names"""
    annotation_cols = [col for col in df.columns if "annotation" in col.lower()]
    return annotation_cols


def print_impact(df):
    """Display function to better visualize impact df"""
    annot_cols = detect_annotation_cols(df)
    return df[
        [
            "appealCode",
            "impactSubtype",
            "impactValue",
            "impactUnit",
            "location",
            "locationPolygon",
            "startYear",
            "startMonth",
            "startDay",
            "endYear",
            "endMonth",
            "endDay",
            "hazards",
        ]
        + annot_cols
    ]


def print_match(matched_df):
    """Display function to better visualize match df"""
    return matched_df[
        [
            "appealCode",
            "impactSubtype",
            "impactSubtype_matched",
            "impactValue",
            "impactValue_matched",
            "impactUnit",
            "impactUnit_matched",
            "location",
            "location_matched",
            "locationPolygon",
            "locationPolygon_matched",
            "impactSubtype_sim",
            "impactValue_error",
            "impactValue_sim",
            "impactUnit_sim",
            "geometry_sim",
            "startYear_sim",
            "startMonth_sim",
            "startDay_sim",
            "endYear_sim",
            "endMonth_sim",
            "endDay_sim",
            "hazards_sim",
            "match_sim",
            "valueAnnotation",
            "annotation_matched",
        ]
    ]


def filter_by_flags(df, flag_filters=list):
    for flt_flag in flag_filters:
        df = df[~df[flt_flag]]
    return df


def filter_matches(matched_df, value_error_th=0.05, sim_th=0.6, match_cat=None):
    """Filter matches based on value error threshold for quantitative and similarity threshold for qualitative"""
    # filter matches
    matched_df_filter_qt = matched_df.copy()
    matched_df_filter_qt = matched_df_filter_qt[
        (matched_df_filter_qt["match_sim"] >= sim_th)
        & (matched_df_filter_qt["impactValue_error"] <= value_error_th)
        & (matched_df_filter_qt["quanti"] == "quanti")
    ]
    matched_df_filter_ql = matched_df.copy()
    matched_df_filter_ql = matched_df_filter_ql[
        (matched_df_filter_ql["match_sim"] >= sim_th)
        & (matched_df_filter_ql["quanti"] == "quali")
    ]
    if match_cat:
        matched_df_filter_ql = pd.concat(
            [
                matched_df_filter_ql.query(f"{cat} == {cat}_matched").dropna(
                    how="all", axis=0
                )
                for cat in match_cat
            ]
        ).sort_index()
    return pd.concat([matched_df_filter_qt, matched_df_filter_ql], axis=0)


def normalize_flags(x, output_type="bool"):
    """Normalize flags to boolean values (0 or 1)"""
    if output_type == "bool":
        pos = True
        neg = False
    elif output_type == "int":
        pos = 1
        neg = 0
    else:
        raise ValueError("output_type must be 'bool' or 'int'")
    if pd.isna(x):
        return neg
    elif x in [0, 0.0, "0", "0.0", "np.nan", "null", False]:
        return neg
    elif x in [1, 1.0, "1", "1.0", True]:
        return pos
    else:
        return x


def get_flag_cols(df):
    """Get all columns in the dataframe that are flags (start with 'flag_' or 'valid_)"""
    return [
        col for col in df.columns if col.startswith("flag_") or col.startswith("valid_")
    ]


def gather_flags(extracted_data, flag_columns, flag_name, how="any"):
    """
    Gathers all flag columns into a single column "any_flag", which is True if any of the flag columns are True, and False otherwise.

    Parameters
    ----------
    extracted_data : pandas.DataFrame
        The dataframe containing the extracted data
    flag_columns : list
        The list of flag columns to gather
    flag_name : str, default "any_flag"
        The name of the column to store the gathered flags

    Returns
    -------
    pandas.DataFrame
        The dataframe with the added column
    """

    def check_any_flag(x):
        return any(x[flag] for flag in flag_columns if flag in x.index)

    def check_all_flags(x):
        return all(x[flag] for flag in flag_columns if flag in x.index)

    if how == "any":
        gather_func = check_any_flag
    elif how == "all":
        gather_func = check_all_flags
    else:
        raise ValueError("Invalid value for 'how'. Must be 'any' or 'all'.")

    extracted_data[flag_name] = np.nan
    extracted_data[flag_name] = extracted_data.apply(gather_func, axis=1)
    # drop individual flag columns
    flags_drop = [flag for flag in flag_columns if flag != flag_name]
    extracted_data = extracted_data.drop(columns=flags_drop)
    return extracted_data
