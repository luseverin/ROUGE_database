from tracemalloc import start
from venv import logger
import numpy as np
import pandas as pd
import geopandas as gpd
import geopy as gpy
import time
import itertools
import regex as re
from matplotlib import pyplot as plt
from src.logger_setup import set_logger

# import sys
# import os
# current_dir = os.getcwd()
# project_root = os.path.dirname(current_dir)
# sys.path.append(project_root)

from src.data import *
from src.text_processing_functions import *
from src.post_process_functions import *
from src.data_format import DATE_FIELDS, DEF_MAX_YEAR, DEF_MIN_YEAR, format_output
from src.geocoding_utils import *
from src.geocoding import *
from src.hazard_def import *
from src.sanity_checks import *

### Post process
# 0. Formatting
# 1. Reclassify hazards
# 2. Reclassify impactSubtypes
# 3. Reclassify, convert and standardize units
# 4. Geocoding

## Parameters
filename_in = "0-717_latest_reports_1quali_chunksize1000_Noneit_meta-llama_llama-4-scout-17b-16e-instruct_v230426"
# "labelled_reports_impacts_gaps_v050426"  # name of file to process (without extension)
# "test_reports_gaps_chunksize1000_llama-3.3-70b-versatile_v060426"  # name of file to process (without extension)
# "test_reports_gaps_chunksize1000_meta-llama_llama-4-scout-17b-16e-instruct_v070426"

filename_out = (
    "test_post_processed_" + filename_in + f"_v{dt.datetime.now().strftime('%d%m%y')}"
)  # "post_processed_" + filename_in#post_processed_flags_
data_path = DATA_OUT_LLMS  # DATA_LABELLED DATA_OUT_LLMS  (depending on whether we want to process the LLM output or the labelled data)
# postprocess params
post_proc = (
    True  # whether or not we want to process the LLM output or the labelled data
)
check_flag_value_in_text = (
    True  # whether or not we want to check if the value is in the original text
)
convert_to_people = True  # whether or not we want to convert convertible units to people (e.g. families -> 3 people)
force_unit_to_subtype_default = False  # whether or not we want to force unit to default unit of subtype when unknown unit
force_no_unit_quali = (
    True  # whether or not we want to force unit to null when impact is quali
)
infer_subtype_from_unit = (
    True  # whether or not we want to reclassify impact subtype in function of the unit
)
filter_unknown_subtype = (
    False  # whether or not we want to filter out unknown impact subtype
)
merge_subtypes = True  # whether or not we want to merge impact subtypes
date_fields = (
    DATE_FIELDS  # list of date fields to check for missing values and inconsistencies
)
infer_startYear_method = "most_frequent_startYear"  # method to infer startYear when missing. Options: "most_frequent_startYear", "from_endYear". Use None to disable inference.
min_allowed_year = DEF_MIN_YEAR  # minimum allowed year for startYear and endYear. Use None to disable check.
max_allowed_year = DEF_MAX_YEAR  # maximum allowed year for startYear and endYear. Use None to disable check.
remove_cats = [
    "DREF Allocation",
    "DREF Allocation & Funding requirements",
    "Targeted People",
    "Assisted People",
    "Other Human Impacts",
]  # list of impactSubtypes to remove

remove_hazards_list = ["Epidemic", "Conflict"]  # list of hazards to remove

dedup_cols = [
    "appealCode",
    "impactSubtype",
    "impactValue",
    "impactUnit",
    "country_iso3",
    "location",
    "startYear",
    "startMonth",
    "startDay",
    "endYear",
    "endMonth",
    "endDay",
    "hazards",
]

# geocoding params
geocode = True  # whether or not we want to geocode
geocode_load = False  # set to True to load previously geocoded data
similarity_th = 0.5
similarity_polygon = 0.6
print_info = False
polygon_source = "GAUL"

# set up logger
logger_name = "postprocessing"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)
start_time = time.time()
## Load data
country_pop = pd.read_csv(
    DATA_PATH
    / (
        "API_SP.POP.TOTL_DS2_en_csv_v2_131993/"
        + "API_SP.POP.TOTL_DS2_en_csv_v2_131993.csv"
    ),
    sep=",",
    header=2,
).dropna(how="all", axis=1)

if not post_proc:  # try directly loading the postprocess data
    LOGGER.info("Reading %s", filename_in)
    response_df_proc = pd.read_csv(data_path / (filename_in + ".csv"))
else:
    if geocode_load:
        LOGGER.info("Loading geocoded data %s...", filename_in)
        # load geocoded data
        response_df = gpd.read_file(data_path / (filename_in + ".gpkg"))
    else:
        LOGGER.info("Reading %s...", filename_in)
        # load initial data
        response_df = pd.read_csv(data_path / (filename_in + ".csv"))

    # copy data
    response_df_proc = cp.deepcopy(response_df).iloc[:10]

    ## Formatting
    # convert numerical columns
    response_df_proc = format_output(response_df_proc)

    # process impactValue
    response_df_proc = response_df_proc.apply(parse_impact_value_precision, axis=1)

    # mark quanti and quali rows
    response_df_proc = response_df_proc.apply(label_quanti_quali, axis=1)

    # parse nan or none unit to null string
    response_df_proc = response_df_proc.apply(convert_null_unit, axis=1)

    # consolidate dates
    # for col in ["startYear", "startMonth", "startDay"]:
    #    response_df_proc = consolidate_dates(response_df_proc, col, np.nanmin)
    #
    # for col in ["endYear", "endMonth", "endDay"]:
    #    response_df_proc = consolidate_dates(response_df_proc, col, np.nanmax)
    #
    # response_df_proc["startDate"] = response_df_proc.apply(lambda x: pd.to_datetime(f"{int(x.startYear)}-{int(x.startMonth)}-{int(x.startDay)}"),axis=1)
    # response_df_proc["endDate"] = response_df_proc.apply(lambda x: pd.to_datetime(f"{int(x.endYear)}-{int(x.endMonth)}-{int(x.endDay)}"),axis=1)

    # pre processing flags
    if check_flag_value_in_text:
        response_df_proc["flag_value_not_in_text"] = response_df_proc.apply(
            flag_value_in_text, axis=1
        )
    # Process dates
    response_df_proc = response_df_proc.apply(
        lambda x: flag_missing_date_field(x, date_fields), axis=1
    )
    response_df_proc = response_df_proc.apply(
        lambda x: flag_startYear_after_endYear(x), axis=1
    )
    if min_allowed_year is not None or max_allowed_year is not None:
        response_df_proc = response_df_proc.apply(
            lambda x: flag_inconsistent_year(x, min_allowed_year, max_allowed_year),
            axis=1,
        )
    response_df_proc = response_df_proc.apply(
        lambda x: flag_inconsistent_month(x), axis=1
    )
    response_df_proc = response_df_proc.apply(
        lambda x: flag_inconsistent_day(x), axis=1
    )

    # add iso3
    if "country_iso3" not in response_df_proc.columns:
        response_df_proc["country_iso3"] = response_df_proc["country"].apply(
            country_list_to_iso3
        )
    if "country_iso3_kw" not in response_df_proc.columns:
        response_df_proc["country_iso3_kw"] = (
            response_df_proc["country_kw"].apply(
                lambda c: country_to_iso(c, representation="alpha3")
            )
            if "country_kw" in response_df_proc.columns
            else None
        )

    ## Reclassify impacType
    response_df_proc = response_df_proc.apply(reclassify_impact_subtype, axis=1)

    ## Reclassify hazard
    response_df_proc = response_df_proc.apply(
        reclassify_hazard, hazard_kw_reclass=hazard_kw_reclass, axis=1
    )

    ## Units reclassification
    # replace numbers in units
    response_df_proc = response_df_proc.apply(replace_numbers_unit, axis=1)
    # standardize metric units
    response_df_proc = response_df_proc.apply(standardize_metric_units, axis=1)
    # harmonize non metric units
    response_df_proc = response_df_proc.apply(harmonize_units, axis=1)
    # convert convertible (non-money) units
    if convert_to_people:
        response_df_proc = response_df_proc.apply(convert_unit, axis=1)
    # reclassify units
    response_df_proc = response_df_proc.apply(reclassify_units, axis=1)
    # normalize people units
    response_df_proc = response_df_proc.apply(normalize_people_unit, axis=1)
    # convert money
    response_df_proc = response_df_proc.apply(convert_monetary_units, axis=1)
    # force unit to subtype default
    if force_unit_to_subtype_default:
        response_df_proc = response_df_proc.apply(force_unit_to_subtype, axis=1)
    # infer subtype from unit
    if infer_subtype_from_unit:
        response_df_proc = response_df_proc.apply(reclass_subtype_from_unit, axis=1)

    # process damage degree
    response_df_proc = response_df_proc.apply(classify_damage_degree, axis=1)

    # filter unknown subtype
    if filter_unknown_subtype:
        response_df_proc = response_df_proc[
            response_df_proc["impactSubtype"] != "Unknown"
        ]
    if force_no_unit_quali:
        response_df_proc.loc[response_df_proc["quanti"] == "quali", "impactUnit"] = (
            "null"
        )
    if merge_subtypes:
        response_df_proc = response_df_proc.apply(merge_impact_subtypes, axis=1)

    # process dates
    if infer_startYear_method is not None:
        response_df_proc = infer_startYear(
            response_df_proc, method=infer_startYear_method
        )

    # Filter duplicates
    if dedup_cols is not None:
        # stringify dedup_cols to avoid issues with unhashable types in geometry column
        response_df_proc[dedup_cols] = response_df_proc[dedup_cols].astype(str)
        init_len = len(response_df_proc)
        duplicates = response_df_proc.duplicated(subset=dedup_cols)
        with pd.option_context(
            "display.max_rows",
            None,
            "display.max_columns",
            None,
            "display.width",
            None,
        ):
            LOGGER.info(
                "Duplicates:\n %s", response_df_proc.loc[duplicates, dedup_cols]
            )  # .to_string(max_rows=None, max_cols=None)

        response_df_proc = response_df_proc[~duplicates]

        LOGGER.info(f"Dropped {init_len - len(response_df_proc)} duplicates")

        # convert dedup_cols back to original types
        response_df_proc = format_output(response_df_proc)

    ## Post conversion flags
    response_df_proc["flag_unit_nonstd"] = response_df_proc.apply(
        flag_unit_nonstd, axis=1
    )
    response_df_proc["flag_value_no_unit"] = response_df_proc.apply(
        flag_value_no_unit, axis=1
    )
    response_df_proc["flag_partial_unit"] = response_df_proc.apply(
        flag_partial_unit, axis=1
    )
    response_df_proc["flag_percent"] = response_df_proc.apply(flag_percent, axis=1)
    response_df_proc["flag_remove_cat"] = response_df_proc.apply(
        flag_remove_cat, remove_cats=remove_cats, axis=1
    )
    response_df_proc["flag_remove_unit"] = response_df_proc.apply(
        flag_remove_unit, axis=1
    )
    response_df_proc["flag_response_unit"] = response_df_proc.apply(
        flag_response_unit, axis=1
    )
    # Flag rows with unwanted hazards
    response_df_proc["flag_remove_hazard"] = response_df_proc.apply(
        flag_remove_hazard,
        axis=1,
        args=(remove_hazards_list,),
    )
    # Flag rows with all hazards unknown
    response_df_proc["flag_all_hazards_unknown"] = response_df_proc.apply(
        flag_hazard_all_unknown, axis=1
    )
    if not geocode and not geocode_load:
        response_df_proc["flag_pop_cntry"] = response_df_proc.apply(
            pop_cntry_check, country_pop=country_pop, axis=1
        )
        ## Save pre-geocoding results
        response_df_proc.to_csv(DATA_OUT_PROC / (filename_out + ".csv"), index=False)
    elif geocode_load:
        response_df_proc["flag_pop_cntry"] = response_df_proc.apply(
            pop_cntry_check, country_pop=country_pop, country_col="iso3_code", axis=1
        )
        ## Save post-geocoding results
        save_df_geo(response_df_proc, DATA_OUT_PROC, filename_out)
        response_df_proc.drop(columns=["geometry"]).to_csv(
            DATA_OUT_PROC / (filename_out + ".csv"), index=False
        )

## Geocoding
if geocode and not geocode_load:
    LOGGER.info("Geodecoding %s...", filename_in)
    # add iso3
    if "country_iso3" not in response_df_proc.columns:
        # response_df_proc["country_iso3"] = response_df_proc["country"].apply(lambda c: country_to_iso(c, representation="alpha3"))
        response_df_proc["country_iso3"] = response_df_proc["country"].apply(
            country_list_to_iso3
        )
    if "country_iso3_kw" not in response_df_proc.columns:
        response_df_proc["country_iso3_kw"] = (
            response_df_proc["country_kw"].apply(
                lambda c: country_to_iso(c, representation="alpha3")
            )
            if "country_kw" in response_df_proc.columns
            else None
        )
    df_geo_output_split, df_geo_output = geocode_df_to_polygon_by_unique_loc(
        response_df_proc,
        similarity_th=similarity_th,
        print_info=print_info,
        polygon_source=polygon_source,
    )

    # Post geocoding flags
    df_geo_output["flag_pop_cntry"] = df_geo_output.apply(
        pop_cntry_check, country_pop=country_pop, country_col="iso3_code", axis=1
    )
    df_geo_output_split["flag_pop_cntry"] = df_geo_output_split.apply(
        pop_cntry_check, country_pop=country_pop, country_col="iso3_code", axis=1
    )

    # save without geometry column
    df_geo_output.drop(columns=["geometry"]).to_csv(
        DATA_OUT_PROC / (filename_out + "_geo.csv"), index=False
    )
    df_geo_output_split.drop(columns=["geometry"]).to_csv(
        DATA_OUT_PROC / (filename_out + "_geo_split_lowest.csv"), index=False
    )

    # save with geometry column
    save_df_geo(df_geo_output, DATA_OUT_PROC, filename_out + "_geo")
    save_df_geo(df_geo_output_split, DATA_OUT_PROC, filename_out + "_geo_split_lowest")

end_time = time.time()

LOGGER.info("Total postprocessing time %.2f seconds", end_time - start_time)
