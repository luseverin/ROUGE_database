from tracemalloc import start
import pandas as pd
import time
import regex as re
from matplotlib import pyplot as plt
from src.logger_setup import set_logger
import ast, json, re

from src.data import *
from src.text_processing_functions import *
from src.post_process_functions import *
from src.data_format import format_output
from src.geocoding_utils import *
from src.geocoding import *
from src.hazard_def import *
from src.sanity_checks import *

similarity_th = 0.5
similarity_polygon = 0.6
print_info = False
polygon_source = "GAUL"
res_savename = None

filename_in = (
    "post_processed_0-717_latest_reports_1quali_chunksize1000_Noneit_meta-llama_llama-4-scout-17b-16e-instruct_v230426_v180526_geo"
)
filename_out = (
    "post_processed_" + filename_in + f"_v{dt.datetime.now().strftime('%d%m%y')}"
)
data_path = DATA_OUT_PROC

logger_name = "postprocessing"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{filename_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

response_df = pd.read_csv(data_path / (filename_in + ".csv"))
response_df_proc = cp.deepcopy(response_df)
response_df_proc = response_df_proc.rename(columns={"country_robust": "country", "country_robust_iso3": "country_iso3"})
response_df_proc = format_output(response_df_proc)

col_to_list = ["location", "country", "country_iso3", "country_robust_iso2"]
response_df_proc[col_to_list] = response_df_proc[col_to_list].map(lambda x: listify_strings(x))

response_df_proc["country_robust"] = response_df_proc["country"]
response_df_proc["country_robust_iso3"] = response_df_proc["country_iso3"]

# add iso3
# if "country_iso3" not in response_df_proc.columns:
#     # response_df_proc["country_iso3"] = response_df_proc["country"].apply(lambda c: country_to_iso(c, representation="alpha3"))
#     response_df_proc["country_iso3"] = response_df_proc["country"].apply(
#         country_list_to_iso3
#     )
# if "country_iso3_kw" not in response_df_proc.columns:
#     response_df_proc["country_iso3_kw"] = (
#         response_df_proc["country_kw"].apply(
#             lambda c: country_to_iso(c, representation="alpha3")
#         )
#         if "country_kw" in response_df_proc.columns
#         else None
#     )

# Prepare dataset
df_geo = deepcopy(response_df_proc)

if "country_kw" in df_geo.columns:
    col_to_list = ["location", "country", "country_kw", "country_iso3"]
else:
    col_to_list = ["location", "country", "country_iso3"]
df_geo[col_to_list] = df_geo[col_to_list].map(lambda x: listify_strings(x))

# Open Polygons
gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)

# Collect unique locations and associated countries
start = time.time()
if "country_robust" not in df_geo.columns:
    if "country_kw" in df_geo.columns:
        df_geo = identify_robust_country(
            df_geo,
            ctr_col1="country",
            ctr_col2="country_kw",
            output_col="country_robust",
        )
    else:
        df_geo["country_robust"] = df_geo["country"]
if "country_robust_iso3" not in df_geo.columns:
    if "country_iso3_kw" in df_geo.columns:
        df_geo = identify_robust_country(
            df_geo,
            ctr_col1="country_iso3",
            ctr_col2="country_iso3_kw",
            output_col="country_robust_iso3",
        )
    else:
        df_geo["country_robust_iso3"] = df_geo["country_iso3"]

# Derive ISO2 from the robust ISO3 column
if "country_robust_iso2" not in df_geo.columns:
    df_geo["country_robust_iso2"] = df_geo["country_robust_iso3"].apply(
        get_iso2_from_iso3
    )

unique_loc = identify_unique_location_country(df_geo)
end = time.time()
time_open = (end - start) / 60
LOGGER.info("Number of unique locations : %s", len(unique_loc))
LOGGER.info("Time to identify all locations %.2fmins", time_open)

# Run nominatim for each loc (or load existing results)
res_savename = "220526"
if not res_savename:
    nominatim_save_path = DATA_OUT_PROC / (
        f"nominatim_output_{dt.date.today().strftime('%d%m%y')}"
    )
else:
    nominatim_save_path = DATA_OUT_PROC / (f"nominatim_output_{res_savename}")

# If a previous nominatim .pkl exists, load it and skip re-querying
pkl_path = nominatim_save_path.with_suffix(".pkl")
if pkl_path.exists():
    LOGGER.info("Found existing nominatim pickle at %s, loading", pkl_path)
    unique_loc = pd.read_pickle(pkl_path)
else:
    start = time.time()
    nom_loc_dict = {}

    cols = [
        "nom_result",
        "coords",
        "match_info",
        "country",
        "country_iso3",
        "country_iso2",
    ]
    unique_loc.loc[:, cols] = unique_loc.apply(
        lambda row: find_best_nomin(row, similarity_th, print_info=True), axis=1
    )

    end = time.time()
    time_open = (end - start) / 60
    LOGGER.info("Time to geocode all locations %.2fmins", time_open)

    try:
        unique_loc.to_parquet(nominatim_save_path.with_suffix(".parquet"))
    except Exception as e:
        LOGGER.info("Parquet save failed %s", e)

        # Convert problematic object columns to string
        unique_loc_save = unique_loc.copy()

        for col in unique_loc_save.select_dtypes(include="object").columns:
            unique_loc_save[col] = unique_loc_save[col].astype(str)

        unique_loc_save.to_parquet(nominatim_save_path.with_suffix(".parquet"))

    try:
        unique_loc.to_pickle(nominatim_save_path.with_suffix(".pkl"))
    except Exception as e:
        LOGGER.info("Pickle save failed %s", e)
    LOGGER.info("Nominatim output saved in %s", nominatim_save_path)


# Convert nominatim output to polygons
start = time.time()
max_workers = min(10, (os.cpu_count() or 1) + 2)
df_geo_individual_locs = run_parallel_geocode(
    unique_loc, gpd_files, print_info=False, max_workers=max_workers
)
end = time.time()
time_open = (end - start) / 60
LOGGER.info("Time to geocode all locations %.2fmins", time_open)
if not res_savename :
    geocode_unique_save_path = DATA_OUT_PROC / (f"geocode_unique_{dt.date.today().strftime('%d%m%y')}.gpkg")
else :  
    geocode_unique_save_path = DATA_OUT_PROC / (f"geocode_unique_{res_savename}.gpkg")
atomic_gpkg_save(
    df_geo_individual_locs, geocode_unique_save_path, layer_name="multipolygons"
)
LOGGER.info("Geocoded unique locations saved in %s", geocode_unique_save_path)