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


def filter_matches(
    matched_df, value_error_th=0.05, sim_th=0.6, match_cat=["impactSubtype"]
):
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
