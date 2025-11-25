from venv import logger
import pandas as pd
import geopandas as gpd
import logging
from src.data import *
from src.post_process_functions import merge_impact_subtypes, label_quanti_quali
from src.geocoding import atomic_gpkg_save
from src.impact_def import IMPACT_SUBTYPE_MERGER
from src.logger_setup import set_logger

##load data (model)
res_savename = "post_processed_new_unit_std_labelled_reports_impacts_all_v111025"
suffix = "_geo_v171025"
res_savename_geo = res_savename + suffix
response_df = pd.read_csv(DATA_OUT_PROC / (res_savename + ".csv"))
response_df_geo = gpd.read_file(DATA_OUT_PROC / (res_savename_geo+".gpkg"))

filename_out = "merged_subtypes_" + res_savename
filename_out_geo = "merged_subtypes_" + res_savename_geo

#set up logger
logger_name = "subtypes_merger"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

##mark quanti vs quali and normalize units
if "quanti" not in response_df_geo.columns:
    response_df_geo = response_df_geo.apply(label_quanti_quali, axis=1)

response_df_geo.loc[response_df_geo["quanti"] == "quali", "impactUnit"] = "null"
if "quanti" not in response_df.columns:
    response_df = response_df.apply(label_quanti_quali, axis=1)

response_df.loc[response_df["quanti"] == "quali", "impactUnit"] = "null"

## merge infra and service access
response_df_geo = response_df_geo.apply(merge_impact_subtypes, impact_kw_reclass=IMPACT_SUBTYPE_MERGER,axis=1)
response_df = response_df.apply(merge_impact_subtypes, impact_kw_reclass=IMPACT_SUBTYPE_MERGER,axis=1)

## drop duplicates
init_len = len(response_df)
init_len_geo = len(response_df_geo)
duplicates = response_df.duplicated(subset=["appealCode","impactSubtype", "impactValue", "impactUnit", "country",
                                                    "location", "startYear", "startMonth", "startDay",
                                                    "endYear", "endMonth", "endDay", "hazards"])
duplicates_geo = response_df_geo.duplicated(subset=["appealCode","impactSubtype", "impactValue", "impactUnit", "country",
                                                    "location", "startYear", "startMonth", "startDay",
                                                    "endYear", "endMonth", "endDay", "hazards"])
LOGGER.info("Duplicates: %s", response_df[duplicates])
LOGGER.info("Duplicates in geolocated data: %s", response_df_geo[duplicates_geo])

response_df = response_df[~duplicates]
response_df_geo = response_df_geo[~duplicates_geo]

LOGGER.info(f"Dropped {init_len - len(response_df)} duplicates")
LOGGER.info(f"Dropped {init_len_geo - len(response_df_geo)} duplicates in geolocated data")

## save
atomic_gpkg_save(response_df_geo, DATA_OUT_PROC / (filename_out_geo + ".gpkg"))
response_df.to_csv(DATA_OUT_PROC / (filename_out + ".csv"), index=False)