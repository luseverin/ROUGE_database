import pandas as pd
import geopandas as gpd
from src.data import *
from src.post_process_functions import merge_impact_subtypes, label_quanti_quali
from src.geocoding import atomic_gpkg_save
from src.impact_def import IMPACT_SUBTYPE_MERGER
from src.logger_setup import set_logger

## Parameters

##load data (model)
res_savename = (
    "post_processed_labelled_reports_gaps_llama-3.3-70b-versatile_v270326_v270326_geo"
)

# "post_processed_labelled_reports_impacts_nogaps_v270326_v270326_geo"

# "post_processed_labelled_reports_gaps_meta-llama_llama-4-scout-17b-16e-instruct_v270326_v270326_geo"

suffix = ""
res_savename_geo = res_savename
response_df = pd.read_csv(DATA_OUT_PROC / (res_savename + ".csv"))
response_df_geo = gpd.read_file(DATA_OUT_PROC / (res_savename_geo + ".gpkg"))

filename_out = res_savename
filename_out_geo = res_savename_geo

# set up logger
logger_name = "subtypes_merger"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

## merge infra and service access
response_df_geo = response_df_geo.apply(
    merge_impact_subtypes, impact_kw_reclass=IMPACT_SUBTYPE_MERGER, axis=1
)
response_df = response_df.apply(
    merge_impact_subtypes, impact_kw_reclass=IMPACT_SUBTYPE_MERGER, axis=1
)

## save
atomic_gpkg_save(response_df_geo, DATA_OUT_PROC / (filename_out_geo + ".gpkg"))
response_df.to_csv(DATA_OUT_PROC / (filename_out + ".csv"), index=False)
