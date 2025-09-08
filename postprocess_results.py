import numpy as np
import pandas as pd
import geopandas as gpd
import geopy as gpy
import time
import itertools
import regex as re
from matplotlib import pyplot as plt
from src.data import *
from src.text_processing_functions import *
from src.plot_functions import *
from src.post_process_functions import *
from src.geocoding import *
from src.hazard_def import *
from src.impact_def import *
from src.sanity_checks import *

### Post process
#0. Formatting
#1. Reclassify hazards
#2. Reclassify impactSubtypes
#3. Reclassify units

## Parameters
filename_in = "labelled_reports_impacts_all_v080925.csv" #'llm_response_impact_labelled_reports_test_multiprompt_continue_v050925_21rep_meta-llama_llama-4-scout-17b-16e-instruct.csv'
filename_out =  "post_processed_" + filename_in
data_path = DATA_LABELLED #DATA_OUT_LLMS (depending on whether we want to process the LLM output or the labelled data)
force_unit_to_subtype = False #whether or not we want to force unit to default unit of subtype when unknown unit

## Load data
response_df = pd.read_csv(DATA_LABELLED / filename_in)

#copy data
response_df_proc = cp.deepcopy(response_df)

## Formatting
#get rid of nans
response_df_proc = response_df_proc.dropna(subset=["nathaz_text"]) if "nathaz_text" in response_df_proc.columns else response_df_proc
#process impactValue
response_df_proc[["impactValue", "impactValueMin", "impactValueMax"]] = response_df_proc.apply(parse_impact_value_precision, axis=1)
#convert numerical columns
num_cols = ["impactValue", "impactValueMin", "impactValueMax","startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"]
list_cols = ["country","location", "hazards", "valueAnnotation", "locationAnnotation", "dateAnnotation", "hazardsAnnotation", "annotation"]
list_cols = [key for key in list_cols if key in response_df_proc.columns]
response_df_proc = format_output(response_df_proc, num_cols=num_cols, list_cols=list_cols)

#add iso3
response_df_proc["country_iso3"] = response_df_proc["country"].apply(list_country_name_to_iso3)
response_df_proc["country_iso3_kw"] = response_df_proc["country_kw"].apply(list_country_name_to_iso3) if "country_kw" in response_df_proc.columns else None

## Reclassify impacType
response_df_proc["impactSubtype"] = response_df_proc.apply(reclassify_impact_subtype, allowed_impact_types=impactSubtype_list, impact_kw_reclass=impact_kw_reclass, axis=1)

## Reclassify hazard
response_df_proc["hazards"] = response_df_proc.apply(reclassify_hazard, hazard_kw_reclass=hazard_kw_reclass, axis=1)

## Units reclassification
#replace numbers in units
response_df_proc[["impactValue", "impactUnit"]] = response_df_proc.apply(replace_numbers_unit, axis=1)
#convert money
response_df_proc[["impactValue", "impactUnit"]] = response_df_proc.apply(convert_monetary_units, axis=1)
#standardize SI units
response_df_proc[["impactValue", "impactUnit"]]  = response_df_proc.apply(standardize_units, std_unit_kw_reclass=std_unit_kw_reclass, unit_mapping=unit_mapping, axis=1)
#convert convertible (non-money) units
response_df_proc = response_df_proc.apply(convert_unit, unit_converter=unit_converter, axis=1)
#assign unit type (e.g. surface, volume, mass)
response_df_proc["unit_type"] = response_df_proc.apply(assign_unit_type, unit_type_kw_reclass=unit_type_kw_reclass, axis=1)
#reclassify non convertible units
response_df_proc["impactUnit"] = response_df_proc.apply(reclassify_units, unit_kw_reclass=unit_kw_reclass, default_subtype_unit=default_subtype_unit, force_unit_to_subtype=force_unit_to_subtype, axis=1)


## Save
response_df_proc.to_csv(DATA_OUT_PROC / filename_out, index=False)