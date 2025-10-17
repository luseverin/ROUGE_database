import numpy as np
import pandas as pd
import geopandas as gpd
import geopy as gpy
import time
import itertools
import regex as re
from matplotlib import pyplot as plt

# import sys
# import os
# current_dir = os.getcwd()
# project_root = os.path.dirname(current_dir)
# sys.path.append(project_root)

from src.data import *
from src.text_processing_functions import *
from src.plot_functions import *
from src.post_process_functions import *
from src.geocoding import *
from src.hazard_def import *
from src.sanity_checks import *

### Post process
#0. Formatting
#1. Reclassify hazards
#2. Reclassify impactSubtypes
#3. Reclassify, convert and standardize units
#4. Geocoding

## Parameters
filename_in =  "labelled_reports_turnoff_subtype_val_meta-llama_llama-4-scout-17b-16e-instruct_v131025"
#"labelled_reports_turnoff_subtype_val_meta-llama_llama-4-scout-17b-16e-instruct_v131025"
#"labelled_reports_turnoff_subtype_val_openai_gpt-oss-20b_v141025"
#"labelled_reports_turnoff_subtype_val_all_llama-3.3-70b-versatile_v141025"
#"labelled_reports_ext_flags_meta-llama_llama-4-scout-17b-16e-instruct_v111025"
#"monty_200rep_meta-llama_llama-4-scout-17b-16e-instruct_v190925"
#"labelled_reports_llama-3.1-8b-instant_v250925"
#"labelled_reports_impacts_all_v111025"
filename_out =  "post_processed_new_unit_std_" + filename_in#post_processed_flags_
data_path = DATA_OUT_LLMS #DATA_LABELLED DATA_OUT_LLMS  (depending on whether we want to process the LLM output or the labelled data)
#postprocess params
post_proc = True #whether or not we want to process the LLM output or the labelled data
force_unit_to_subtype = False #whether or not we want to force unit to default unit of subtype when unknown unit
reclass_subtype = True #whether or not we want to reclassify impact subtype in function of the unit
filter_unknown_subtype = True #whether or not we want to filter out unknown impact subtype
#geocoding params
geocode = True #whether or not we want to geocode
geocode_load = False #f"post_processed_{filename_in}_GEOCODE_v141025" #geocoded file to load or false
similarity_th=0.2
similarity_polygon = 0.6
print_info=False
polygon_source="geoBoundaries"

## Load data
if not post_proc: #try directly loading the postprocess data
    response_df_proc = pd.read_csv(DATA_OUT_PROC / (filename_out + ".csv"))
    # response_df_proc = pd.read_csv(os.path.join(DATA_OUT_PROC, filename_out+'.csv'))

else:
    response_df = pd.read_csv(data_path / (filename_in + ".csv"))
    # response_df = pd.read_csv(os.path.join(data_path, filename_in+'.csv'))

    #copy data
    response_df_proc = cp.deepcopy(response_df)

    ## Formatting
    ##get rid of nans
    #response_df_proc = response_df_proc.dropna(subset=["nathaz_text"]) if "nathaz_text" in response_df_proc.columns else response_df_proc
    #convert numerical columns
    num_cols = ["impactValue", "impactValueMin", "impactValueMax","startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"]
    list_cols = ["country","location", "hazards", "valueAnnotation", "locationAnnotation", "dateAnnotation", "hazardsAnnotation", "annotation"]
    list_cols = [key for key in list_cols if key in response_df_proc.columns]
    response_df_proc = format_output(response_df_proc, num_cols=num_cols, list_cols=list_cols)

    #process impactValue
    response_df_proc = response_df_proc.apply(parse_impact_value_precision, axis=1)

    #pre conversion flags
    if "nathaz_text" in response_df_proc.columns:
        response_df_proc["flag_value_not_in_text"] = response_df_proc.apply(flag_value_in_text, axis=1)

    #add iso3
    response_df_proc["country_iso3"] = response_df_proc["country"].apply(list_country_name_to_iso3)
    response_df_proc["country_iso3_kw"] = response_df_proc["country_kw"].apply(list_country_name_to_iso3) if "country_kw" in response_df_proc.columns else None

    ## Reclassify impacType
    response_df_proc = response_df_proc.apply(reclassify_impact_subtype, axis=1)
    if filter_unknown_subtype:
        response_df_proc = response_df_proc[response_df_proc["impactSubtype"] != "Unknown"]

    ## Reclassify hazard
    response_df_proc = response_df_proc.apply(reclassify_hazard, hazard_kw_reclass=hazard_kw_reclass, axis=1)

    ## Units reclassification
    #replace numbers in units
    response_df_proc = response_df_proc.apply(replace_numbers_unit, axis=1)
    #convert money
    response_df_proc = response_df_proc.apply(convert_monetary_units, axis=1)
    #standardize metric units
    response_df_proc = response_df_proc.apply(standardize_metric_units, axis=1)
    #assign unit type (e.g. surface, volume, mass)
    response_df_proc = response_df_proc.apply(assign_unit_type, axis=1)
    #harmonize non metric units
    response_df_proc = response_df_proc.apply(harmonize_units, axis=1)
    #convert convertible (non-money) units
    response_df_proc = response_df_proc.apply(convert_unit, axis=1)
    #reclassify units
    response_df_proc = response_df_proc.apply(reclassify_units,force_unit_to_subtype=force_unit_to_subtype, reclass_subtype=reclass_subtype, axis=1)
    #normalize people units
    response_df_proc = response_df_proc.apply(normalize_people_unit, axis=1)

    ## Post conversion flags
    country_pop = pd.read_csv(DATA_PATH / ("API_SP.POP.TOTL_DS2_en_csv_v2_131993/"+"API_SP.POP.TOTL_DS2_en_csv_v2_131993.csv"),sep=',', header=2).dropna(how="all",axis=1)
    # country_pop = pd.read_csv(os.path.join(DATA_PATH, "API_SP.POP.TOTL_DS2_en_csv_v2_131993", "API_SP.POP.TOTL_DS2_en_csv_v2_131993.csv"),sep=',', header=2).dropna(how="all",axis=1)

    response_df_proc["flag_pop_cntry"] = response_df_proc.apply(pop_cntry_check, country_pop=country_pop, axis=1)
    response_df_proc["flag_value_no_unit"] = response_df_proc.apply(flag_value_no_unit, axis=1)
    response_df_proc["flag_partial_unit"] = response_df_proc.apply(flag_partial_unit, axis=1)
    response_df_proc["flag_percent"] = response_df_proc.apply(flag_percent, axis=1)
    ## Save pre-geocoding results
    response_df_proc.to_csv(DATA_OUT_PROC / (filename_out + ".csv"), index=False)
    # response_df_proc.to_csv(os.path.join(DATA_OUT_PROC, filename_out+"csv"), index=False)

## Geocoding
if geocode:
    df_geo_output_split, df_geo_output = geocode_df_to_polygon_by_unique_loc(response_df_proc, similarity_th=similarity_th, print_info=print_info, save_path=DATA_OUT_PROC, res_savename=filename_out, polygon_source=polygon_source)
elif geocode_load:
    #load geocoded data
    df_geo_output_split = gpd.read_file(DATA_OUT_PROC / (geocode_load.replace("GEOCODE", "geo_split_lowest")+".gpkg"))
    df_geo_output =  gpd.read_file(DATA_OUT_PROC / (geocode_load.replace("GEOCODE", "geo")+".gpkg"))