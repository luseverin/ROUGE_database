
## Script to filter final data
#1 drop duplicates
#2 select columns

import pandas as pd
import geopandas as gpd
from src.data import *
from src.data_format import *
from src.post_process_functions import merge_annotations
from src.sanity_checks import gather_flags
from src.geocoding import atomic_gpkg_save
from src.geocoding_utils import split_continents
from src.logger_setup import set_logger

## Parameters
dedup_cols = ["appealCode","impactSubtype", "impactValue", "impactUnit", "country",
              "location", "startYear", "startMonth", "startDay","endYear", "endMonth",
              "endDay", "hazards"]

##load data (model)
res_savename = "post_processed_geocoded_all_appeals_longest_1-717_meta-llama_llama-4-scout-17b-16e-instruct_v121225_geo_v191225"
#"post_processed_labelled_reports_fixed_impact_desc_meta-llama_llama-4-scout-17b-16e-instruct_v271025"
#"post_processed_new_unit_std_labelled_reports_impacts_all_v111025"
suffix = ""
res_savename_geo = res_savename + suffix
response_df = pd.read_csv(DATA_OUT_PROC / (res_savename + ".csv"))
response_df_geo = gpd.read_file(DATA_OUT_PROC / (res_savename_geo+".gpkg"))

# Sort list columns
response_df = format_output(response_df)
response_df_geo = format_output(response_df_geo)

for col in LIST_COLS : 
    if col in response_df.columns : 
        response_df[col] = response_df[col].apply(sorted)
    if col in response_df_geo.columns : 
        response_df_geo[col] = response_df_geo[col].apply(sorted)

response_df = delistify_cols(response_df)
response_df_geo = delistify_cols(response_df_geo)

# Set up final name
filename_out = "filt_" + res_savename
filename_out_geo = "filt_" + res_savename_geo

#set up logger
logger_name = "data_filter"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

## drop duplicates (needs to be done before formatting as lists dtypes cannot be dedup)
init_len = len(response_df)
init_len_geo = len(response_df_geo)
duplicates = response_df.duplicated(subset=dedup_cols)
duplicates_geo = response_df_geo.duplicated(subset=dedup_cols)
with pd.option_context(
    "display.max_rows", None,
    "display.max_columns", None,
    "display.width", None,
):
    LOGGER.info("Duplicates:\n %s", response_df.loc[duplicates, dedup_cols])#.to_string(max_rows=None, max_cols=None)
    LOGGER.info("Duplicates in geolocated data:\n %s", response_df_geo.loc[duplicates_geo, dedup_cols])#.to_string(max_rows=None, max_cols=None)

response_df = response_df[~duplicates]
response_df_geo = response_df_geo[~duplicates_geo]

LOGGER.info(f"Dropped {init_len - len(response_df)} duplicates")
LOGGER.info(f"Dropped {init_len_geo - len(response_df_geo)} duplicates in geolocated data")

## Parse to correct dtypes
response_df = format_output(response_df)
response_df_geo = format_output(response_df_geo)

##Filter unwanted flags
unwanted_flags = ["flag_remove_cat", "flag_value_no_unit", "flag_unit_nonstd", "flag_response_unit", "flag_unknown_subtype"]
for flag in unwanted_flags:
    if flag not in response_df.columns:
        LOGGER.warning(f"Flag {flag} not found in data")
        continue
    if flag not in response_df_geo.columns:
        LOGGER.warning(f"Flag {flag} not found in geolocated data")
        continue
    init_len = len(response_df)
    init_len_geo = len(response_df_geo)
    response_df = response_df[response_df[flag]==False]
    response_df_geo = response_df_geo[response_df_geo[flag]==False]
    LOGGER.info(f"Filtered {init_len - len(response_df)} entries based on {flag} flag")
    LOGGER.info(f"Filtered {init_len_geo - len(response_df_geo)} entries based on {flag} flag in geolocated data")

## gather flag columns
flag_unit_std = ['flag_unit_harmonization', 'flag_non-SI_unit_standardization']
flag_error_columns = ["flag_remove_number_unit_error",
                      "flag_unit_conversion_error",
                      "flag_non-SI_unit_standardization_error",
                      "flag_SI_unit_standardization_error",
                      'flag_failed_currency_conversion']

response_df = gather_flags(response_df, flag_unit_std, flag_name="flag_non-SI_unit_standardization")
response_df_geo = gather_flags(response_df_geo, flag_unit_std, flag_name="flag_non-SI_unit_standardization")
response_df = gather_flags(response_df, flag_error_columns, flag_name="flag_unit_processing_error")
response_df_geo = gather_flags(response_df_geo, flag_error_columns, flag_name="flag_unit_processing_error")

## gather annotation columns
annotation_columns = ["valueAnnotation", "locationAnnotation", "dateAnnotation", "hazardsAnnotation"]
response_df["sourceExcerpts"] = response_df.apply(merge_annotations, args=(annotation_columns,), axis=1)
response_df_geo["sourceExcerpts"] = response_df_geo.apply(merge_annotations, args=(annotation_columns,), axis=1)

## Filter unwanted columns
columns_data_final = ["appealCode", "reportDate", "reportLink", "disasterType",
                 "impactSubtype", "impactValue", "impactValueMin", "impactValueMax", "impactValuePrecision", "impactUnit",
                 "startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay", "hazards", "location",
                 "locationPolygon", "locationLowestAdmin", "iso3_code", "sourceExcerpts"]

columns_flags_final = ['valid_errors_impactValue',
         'valid_errors_loc',
         'valid_errors_dates',
         'valid_errors_haz',
         'flag_value_not_in_text',
         'flag_impactSubtype_reclass',
         'flag_hazards_reclass',
         'flag_remove_number_unit',
         'flag_SI_unit_standardization',
         'flag_non-SI_unit_standardization',
         'flag_unit_processing_error',
         'flag_unit_nonstd',
         'flag_reclass_subtype_from_unit',
         'flag_pop_cntry',
         'flag_value_no_unit',
         'flag_partial_unit',
         'flag_geocoding_country',
         'flag_geocoding_osm']

response_df_filtered = response_df.copy()
response_df_filtered = response_df_filtered[columns_data_final + columns_flags_final]
response_df_geo_filtered = response_df_geo.copy()
response_df_geo_filtered = response_df_geo_filtered[columns_data_final + ["geometry"] + columns_flags_final]

## Rename cols
col_rename = {
    "iso3_code": "country_iso3",
    "disasterType": "disasterType_IFRC"
}
response_df_geo_filtered = response_df_geo_filtered.rename(columns=col_rename)
response_df_filtered = response_df_filtered.rename(columns=col_rename)

## Save
atomic_gpkg_save(response_df_geo_filtered, DATA_OUT_PROC / (filename_out_geo + ".gpkg"))
response_df_geo_filtered.to_parquet(DATA_OUT_PROC / (filename_out_geo+".parquet"),compression="zstd", index=False)
response_df_filtered.to_csv(DATA_OUT_PROC / (filename_out + ".csv"), index=False)

## Split per continent
world = gpd.read_file(ADMIN_PATH / "ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")
#need to be formated to list
response_df_geo_filtered_continent = split_continents(response_df_geo_filtered, world)
for continent, df in response_df_geo_filtered_continent.items():
    continent = continent.replace(" ", "_")
    if len(str(DATA_OUT_PROC / f"{filename_out_geo}_{continent}.parquet")) > 260 : 
        LOGGER.info(f"More than 260 characters, Unable to save file to {str(DATA_OUT_PROC / f"{filename_out_geo}_{continent}.parquet")}")
    else : 
        df.to_parquet(DATA_OUT_PROC / (f"{filename_out_geo}_{continent}"+".parquet"),compression="zstd", index=False)
    atomic_gpkg_save(df, DATA_OUT_PROC / (f"{filename_out_geo}_{continent}" + ".gpkg"))