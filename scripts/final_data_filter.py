## Script to filter final data
# 1 drop duplicates
# 2 Filter unwanted flags
# 3 gather flag columns
# 4 gather annotation columns
# 5 merge infra and service access
# 6 Filter unwanted columns
# 7 Rename cols
# 8 Split per continent
# 9 Save

import pandas as pd
import geopandas as gpd
from src.data import *
from src.data_format import *
from src.post_process_functions import merge_annotations, merge_impact_subtypes
from src.impact_def import IMPACT_SUBTYPE_MERGER
from src.sanity_checks import gather_flags
from src.geocoding import atomic_gpkg_save
from src.geocoding_utils import split_continents
from src.logger_setup import set_logger

## Parameters
dedup_cols = [  # columns to check for duplicates
    "appealCode",
    "impactSubtype",
    "impactValue",
    "impactUnit",
    "iso3_code",
    "location",
    "startYear",
    "startMonth",
    "startDay",
    "endYear",
    "endMonth",
    "endDay",
    "hazards",
]
unwanted_flags = [  # flags to filter out (i.e. keep only rows for which these flags are False)
    "flag_remove_cat",
    "flag_value_no_unit",
    "flag_unit_nonstd",
    "flag_response_unit",
    "flag_unknown_subtype",
    "flag_all_hazards_unknown",
    # "flag_hazards_unknown",
]
flag_groups = {  # groups of flags to gather into a single flag
    "flag_unit_std": [
        "flag_unit_harmonization",
        "flag_non-SI_unit_standardization",
    ],
    "flag_unit_error": [
        "flag_remove_number_unit_error",
        "flag_unit_conversion_error",
        "flag_non-SI_unit_standardization_error",
        "flag_SI_unit_standardization_error",
        "flag_failed_currency_conversion",
    ],
}

merge_subtypes = False  # whether to merge impact subtypes based on keywords (e.g. infra and service access)
remove_unknown_hazards = (
    True  # whether to remove impacts for which all hazards are unknown
)
##load data (model)
res_savename = "post_processed_0-717_latest_reports_1quali_chunksize1000_Noneit_meta-llama_llama-4-scout-17b-16e-instruct_v230426_v230426_geo"

# Set up final name
filename_out = "filter_" + res_savename

# set up logger
logger_name = "data_filter"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

## Load data
response_df = gpd.read_file(DATA_OUT_PROC / (res_savename + ".gpkg"))

# Sort list columns
response_df = format_output(response_df)

response_df = delistify_cols(response_df)

## drop duplicates (needs to be done before formatting as lists dtypes cannot be dedup)
init_len = len(response_df)
duplicates = response_df.duplicated(subset=dedup_cols)
with pd.option_context(
    "display.max_rows",
    None,
    "display.max_columns",
    None,
    "display.width",
    None,
):
    LOGGER.info(
        "Duplicates:\n %s", response_df.loc[duplicates, dedup_cols]
    )  # .to_string(max_rows=None, max_cols=None)

response_df = response_df[~duplicates]

LOGGER.info(f"Dropped {init_len - len(response_df)} duplicates")

## Parse to correct dtypes
response_df = format_output(response_df)

# hot fix, replace nan of null with null
response_df["impactUnit"] = response_df["impactUnit"].replace({"nan of null": "null"})
if remove_unknown_hazards:
    response_df["flag_all_hazards_unknown"] = response_df.apply(
        lambda x: all(haz == "Unknown" for haz in x["hazards"]), axis=1
    )

##Filter unwanted flags
for flag in unwanted_flags:
    if flag not in response_df.columns:
        LOGGER.warning(f"Flag {flag} not found in data")
        continue

    init_len = len(response_df)
    response_df = response_df[response_df[flag] == False]
    LOGGER.info(f"Filtered {init_len - len(response_df)} entries based on {flag} flag")

## gather flag columns
if flag_groups is not None:
    for new_flag, group_flags in flag_groups.items():
        response_df = gather_flags(response_df, group_flags, flag_name=new_flag)

## gather annotation columns
response_df["sourceExcerpts"] = response_df.apply(
    merge_annotations, args=(ANNOTATION_COLS,), axis=1
)

## merge infra and service access
if merge_subtypes:
    response_df = response_df.apply(
        merge_impact_subtypes, impact_kw_reclass=IMPACT_SUBTYPE_MERGER, axis=1
    )

## Filter unwanted columns
response_df_filtered = response_df.copy()
response_df_filtered = response_df_filtered[
    [
        col
        for col in FINAL_DATA_COLS + FINAL_FLAG_COLS
        if col in response_df_filtered.columns
    ]
]

## Rename cols
col_rename = {"iso3_code": "country_iso3", "disasterType": "disasterType_IFRC"}
response_df_filtered = response_df_filtered.rename(columns=col_rename)

## Split per continent
world = gpd.read_file(
    ADMIN_PATH / "ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
)
response_df_filtered_continent = split_continents(response_df_filtered, world)

## Save
atomic_gpkg_save(
    response_df_filtered_continent, DATA_OUT_PROC / (filename_out + ".gpkg")
)
response_df_filtered_continent.to_parquet(
    DATA_OUT_PROC / (filename_out + ".parquet"), compression="zstd", index=False
)
response_df_filtered.drop(columns=["geometry"]).to_csv(
    DATA_OUT_PROC / (filename_out + ".csv"), index=False
)

# save per continent
for continent, df in response_df_filtered_continent.explode("continent").groupby(
    "continent"
):
    continent = continent.replace(" ", "_")
    if len(str(DATA_OUT_PROC / f"{filename_out}_{continent}.parquet")) > 260:
        LOGGER.info(
            f'More than 260 characters, Unable to save file to {str(DATA_OUT_PROC / f"{filename_out}_{continent}.parquet")}'
        )
    else:
        df.to_parquet(
            DATA_OUT_PROC / (f"{filename_out}_{continent}" + ".parquet"),
            compression="zstd",
            index=False,
        )
    atomic_gpkg_save(df, DATA_OUT_PROC / (f"{filename_out}_{continent}" + ".gpkg"))
