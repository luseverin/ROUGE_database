
## Script to filter final data
#1 drop duplicates
#2 select columns

from colorama import init
import pandas as pd
import geopandas as gpd
from src.data import *
from src.post_process_functions import merge_impact_subtypes, label_quanti_quali
from src.geocoding import atomic_gpkg_save
from src.geocoding_utils import split_continents
from src.impact_def import IMPACT_SUBTYPE_MERGER
from src.logger_setup import set_logger

## Parameters
dedup_cols = ["appealCode","impactSubtype", "impactValue", "impactUnit", "country",
              "location", "startYear", "startMonth", "startDay","endYear", "endMonth",
              "endDay", "hazards"]

##load data (model)
res_savename = "post_processed_all_appeals_longest_1-717_meta-llama_llama-4-scout-17b-16e-instruct_v121225"
#"post_processed_labelled_reports_fixed_impact_desc_meta-llama_llama-4-scout-17b-16e-instruct_v271025"
#"post_processed_new_unit_std_labelled_reports_impacts_all_v111025"
suffix = "_geo_v171225"
res_savename_geo = res_savename + suffix
response_df = pd.read_csv(DATA_OUT_PROC / (res_savename + ".csv"))
response_df_geo = gpd.read_file(DATA_OUT_PROC / (res_savename_geo+".gpkg"))

filename_out = "merged_subtypes_" + res_savename
filename_out_geo = "merged_subtypes_" + res_savename_geo

#set up logger
logger_name = "data_filter"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

##Filter unwanted flags
unwanted_flags = ["flag_remove_cat", "flag_value_no_unit"]
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

## drop duplicates
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

## Filter unwanted columns
columns_final = ["appealCode", "reportDate", "reportLink", "disasterType",
                 "impactSubtype", "impactValue", "impactValueMin", "impactValueMax", "impactValuePrecision", "impactUnit", "valueAnnotation",
                 "startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay", "dateAnnotation",
                 "hazards", "hazardsAnnotation",
                 "location", "locationAnnotation"]

flags = ['valid_errors_impactValue',
         'valid_errors_loc',
         'valid_errors_dates',
         'valid_errors_haz',
         'flag_value_not_in_text',
         'flag_impactSubtype_reclass',
         'flag_hazards_reclass',
         'flag_reformat_unit',
         'flag_unit_standardization',
         'flag_unit_type',
         'flag_unit_harmonization',
         'flag_unit_nonstd',
         'flag_reclass_subtype_from_unit',
         'flag_currency_conversion',
         'flag_failed_currency_conversion',
         'flag_pop_cntry',
         'flag_value_no_unit',
         'flag_partial_unit',
         'flag_geocoding_country',
         'flag_geocoding_osm']
colums_final_geo = columns_final + ["locationPolygon", "locationLowestAdmin", "iso3_code", "geometry"]

response_df_filtered = response_df.copy()
response_df_filtered = response_df_filtered[columns_final]
response_df_geo_filtered = response_df_geo.copy()
response_df_geo_filtered = response_df_geo_filtered[colums_final_geo]

## Split per continent 
world = gpd.read_file(ADMIN_PATH / "ne_50m_admin_0_countries/ne_50m_admin_0_countries.shp")
response_df_geo_filtered_continent = split_continents(response_df_geo_filtered, world)
for continent, df in response_df_geo_filtered_continent.items():
    atomic_gpkg_save(df, DATA_OUT_PROC / f"{filename_out_geo}_{continent}")