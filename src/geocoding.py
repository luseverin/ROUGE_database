import pandas as pd
import numpy as np
import ast
import geopy as gpy
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import itertools
import time
import pycountry
import langcodes
from copy import deepcopy
import geopandas as gpd
from functools import partial
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from tqdm import tqdm
from shapely.geometry import Point, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
from src.post_process_functions import *
from src.data import *
import os
import tempfile
import shutil
from urllib.parse import quote
import requests
from collections import defaultdict
import datetime as dt
import gc
import logging
import multiprocessing as mp
import pandarallel
import traceback
import pprint
import sqlite3
import threading
import time
import geopy as gpy
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# set up logger
LOGGER = logging.getLogger("postprocessing")

#Countries
import pycountry
import re

# Add Geolocation and spatial information (region from cities)
from geopy.extra.rate_limiter import RateLimiter
from rapidfuzz.distance import Levenshtein
from src.client import NOMINATIM_USER_AGENT
from src.geocoding_utils import *

# --- Create shared SQLite cache for back nominatim ---
CACHE_DB = "reverse_geocode_cache.db"
_conn = sqlite3.connect(CACHE_DB, check_same_thread=False)
_cur = _conn.cursor()

_cur.execute("""
CREATE TABLE IF NOT EXISTS reverse_cache (
    lat REAL,
    lon REAL,
    lang TEXT,
    zoom INTEGER,
    result TEXT,
    PRIMARY KEY (lat, lon, lang, zoom)
)
""")
_conn.commit()

# Lock guarantees safe concurrent writes
_cache_lock = threading.Lock()

#### Preprocessing of the location 
def identify_robust_country(df_geo) : 
    unique_loc_with_country = {}
    unique_locations_countries = defaultdict(set)
    unique_locations_countries_iso = defaultdict(set)

    for _, row in df_geo.iterrows():
        # Handle countries 
        countries = row["country"]
        isos = row["country_iso3"]

        isos_is_missing = (
            isos is None or
            (isinstance(isos, float) and pd.isna(isos)) or
            (isinstance(isos, (list, tuple)) and (len(isos) == 0 or all(x is None for x in isos)))
        )

        countries_is_missing = (
            countries is None or
            (isinstance(countries, float) and pd.isna(countries)) or
            (isinstance(countries, (list, tuple)) and len(countries) == 0)
        )

        if countries_is_missing or isos_is_missing:
            isos = row["country_iso3_kw"]
            countries = row["country_kw"]

        # ensure iterable
        if not isinstance(countries, (list, set, tuple)):
            countries = [countries]
        if not isinstance(isos, (list, set, tuple)):
            isos = [isos]

        # Handle locations 
        locations = row["location"]
        if not locations:
            # No specific location → use country as both key and location
            for c, iso in zip(countries, isos):
                key = (c, c)
                unique_loc_with_country[key] = True
                unique_locations_countries[key].add(c)
                unique_locations_countries_iso[key].add(iso)
        else:
            # Multiple locations in the row
            for loc in locations:
                for c, iso in zip(countries, isos):

                    # --- NEW KEY (loc, country) ---
                    key = (loc, c)
                    unique_loc_with_country[key] = True

                    unique_locations_countries[key].add(c)
                    unique_locations_countries_iso[key].add(iso)
    # unique_locations_countries = dict(unique_locations_countries)
    # unique_locations_countries_iso = dict(unique_locations_countries_iso)
    unique_loc_with_country = list(unique_loc_with_country.keys())
    return unique_loc_with_country, unique_locations_countries, unique_locations_countries_iso

# def sanitize_and_merge_geometries(geometries):
#     """
#     Takes a list of geometries and returns a clean, valid merged geometry.
#     Uses the existing clean_geometry() function. No inner functions.
#     """

#     # 1. Drop None / empty
#     cleaned = []
#     for g in geometries:
#         if g is None:
#             continue
#         if g.is_empty:
#             continue

#         # ensure polygon validity using your existing function
#         g2 = clean_geometry(g)
#         if g2 is None or g2.is_empty:
#             continue

#         cleaned.append(g2)

#     if not cleaned:
#         return None

#     # 2. Unary union merge (most efficient)
#     try:
#         merged = unary_union(cleaned)
#     except Exception as e:
#         LOGGER.error("[sanitize merge] unary_union failed: %s", e)
#         # fallback: MultiPolygon collection
#         merged = MultiPolygon([g for g in cleaned if isinstance(g, Polygon)])

#     # 3. If merge returns GeometryCollection → flatten polygons only
#     if isinstance(merged, GeometryCollection):
#         polys = [g for g in merged.geoms if isinstance(g, (Polygon, MultiPolygon))]
#         if len(polys) == 0:
#             return None
#         try:
#             merged = unary_union(polys)
#         except:
#             merged = MultiPolygon([g for g in polys if isinstance(g, Polygon)])

#     # 4. Final cleanup pass
#     if merged is None or merged.is_empty:
#         return None

#     if not merged.is_valid:
#         try:
#             merged = merged.buffer(0)
#         except:
#             pass

#     if not merged.is_valid:
#         try:
#             merged = shapely.make_valid(merged)
#         except:
#             pass

#     return merged

#### Function to Geocode one location
def match_admin1_for_row(row, gpd_files):
    """ Given a row of df_geo and gpd_files, find the ADM1 boundary that contains/intersects the geometry."""
    geom = row["geometry"]
    adm0 = row["ADMIN_0"]

    adm1_match = get_polygon_for_geometry(geom, adm0, gpd_files, level=1)
    if adm1_match is not None and "ADMIN_1" in adm1_match:
        return adm1_match["ADMIN_1"].values[0]
    return None

def open_admin_gpd(ADMIN_PATH, polygon_source="GAUL") :
    """Load administrative boundary GeoDataFrames (ADM_0, ADM_1, ADM_2) from either GAUL or geoBoundaries sources and return them as a dictionary."""
    gpd_files = {}
    if polygon_source == "GAUL" :
        try :
            ##### ADMIN2 From GAUL
            # gaul2 = gpd.read_file(ADMIN_PATH+"GAUL_2024_L2/GAUL_2024_L2.shp")
            gaul2 = gpd.read_file(os.path.join(ADMIN_PATH, 'GAUL_2024_L2', 'GAUL_2024_L2.shp'))
            gaul2 = gaul2.rename({"gaul0_name":"ADMIN_0", "gaul1_name":"ADMIN_1", "gaul2_name":"ADMIN_2"}, axis=1)
            gpd_files["ADM_2"] = gaul2

            ##### ADMIN1 From GAUL
            # gaul1 = gpd.read_file(ADMIN_PATH+"GAUL_2024_L1/GAUL_2024_L1.shp")
            gaul1 = gpd.read_file(os.path.join(ADMIN_PATH, 'GAUL_2024_L1', 'GAUL_2024_L1.shp'))
            gaul1 = gaul1.rename({"gaul0_name":"ADMIN_0", "gaul1_name":"ADMIN_1"}, axis=1)
            gaul1["gaul2_code"] = None
            gpd_files["ADM_1"] = gaul1

            ##### ADMIN0 From Natural Earth
            # ne_0 = gpd.read_file(ADMIN_PATH+"ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp")
            ne_0 = gpd.read_file(os.path.join(ADMIN_PATH, 'ne_10m_admin_0_countries', 'ne_10m_admin_0_countries.shp'))
            ne_0 = ne_0.rename({"ADMIN":"ADMIN_0", "ISO_A3" : "iso3_code"}, axis=1)
            ne_0["gaul1_code"] = None
            ne_0["gaul2_code"] = None
            ne_0 = pd.merge(ne_0, gaul1[["iso3_code", "gaul0_code"]], on="iso3_code", how="left").drop_duplicates()
            gpd_files["ADM_0"] = ne_0

        except Exception as e:
            LOGGER.error("[open_admin_gpd][GAUL] Error loading GPD files: %s", e)
            return None
    elif polygon_source == "geoBoundaries" :
        try :
            ### ADMIN 0
            # geoBoundaries0 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM0.gpkg")
            geoBoundaries0 = gpd.read_file(os.path.join(ADMIN_PATH, 'geoBoundaries', 'geoBoundariesCGAZ_ADM0.gpkg'))
            geoBoundaries0 = geoBoundaries0.rename({"shapeName" : "ADMIN_0", "shapeGroup" : "iso3_code"}, axis=1)
            geoBoundaries0 = geoBoundaries0.loc[geoBoundaries0["shapeType"]=="ADM0"]
            gpd_files["ADM_0"] = geoBoundaries0

            ### ADMIN 1
            # geoBoundaries1 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM1.gpkg")
            geoBoundaries1 = gpd.read_file(os.path.join(ADMIN_PATH, 'geoBoundaries', 'geoBoundariesCGAZ_ADM1.gpkg'))
            geoBoundaries1 = geoBoundaries1.rename({"shapeName" : "ADMIN_1", "shapeGroup" : "iso3_code"}, axis=1)
            geoBoundaries1 = geoBoundaries1.loc[geoBoundaries1["shapeType"]=="ADM1"]
            geoBoundaries1 = pd.merge(geoBoundaries1, geoBoundaries0[["iso3_code", "ADMIN_0"]], on="iso3_code", how="left").drop_duplicates()
            gpd_files["ADM_1"] = geoBoundaries1

            ### ADMIN 2
            # geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2.gpkg")
            # geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2_corrected.gpkg")
            geoBoundaries2 = gpd.read_file(os.path.join(ADMIN_PATH, 'geoBoundaries', 'geoBoundariesCGAZ_ADM2_corrected.gpkg'))
            geoBoundaries2 = geoBoundaries2.rename({"shapeName" : "ADMIN_2", "shapeGroup" : "iso3_code"}, axis=1)
            geoBoundaries2 = geoBoundaries2.loc[geoBoundaries2["shapeType"]=="ADM2"]
            gpd_files["ADM_2"] = geoBoundaries2

            if not "ADMIN_0" in gpd_files["ADM_2"].columns :
                gpd_files["ADM_2"] = pd.merge(gpd_files["ADM_2"], geoBoundaries0[["iso3_code", "ADMIN_0"]], on="iso3_code", how="left").drop_duplicates()

            if not "ADMIN_1" in gpd_files["ADM_2"].columns :
                pandarallel.initialize(nb_workers=8)
                func = partial(match_admin1_for_row, gpd_files=gpd_files)
                gpd_files["ADM_2"]["ADMIN_1"] = gpd_files["ADM_2"].parallel_apply(func, axis=1)

        except Exception as e:
            LOGGER.error("[open_admin_gpd][geoBoundaries] Error loading GPD files: %s", e)
            return None

    #Correct potential invalid mask 
    for i in range(2):
        invalid_mask = ~gpd_files[f"ADM_{i}"]["geometry"].is_valid
        gpd_files[f"ADM_{i}"].loc[invalid_mask, "geometry"] = gpd_files[f"ADM_{i}"].loc[invalid_mask, "geometry"].buffer(0)

    return gpd_files

def find_closest_country(curr_country, gpd_files, threshold=0.5):
    """
    Find the closest country name in gpd_files['ADMIN_0'] to curr_country
    using Levenshtein similarity.

    Parameters:
        curr_country (str): Input country name
        gpd_files (GeoDataFrame): Must contain 'ADMIN_0' column with country names
        threshold (float): Minimum similarity score to accept match (0-1)

    Returns:
        str or None: Closest matching country name, or None if no match above threshold
    """
    country_list = gpd_files["ADMIN_0"].unique()

    similarities = [(c, rotated_levenshtein_similarity(curr_country, c)) for c in country_list]
    best_match, best_score = max(similarities, key=lambda x: x[1])

    if best_score >= threshold:
        return best_match
    else:
        return None

def get_polygon(gdf_file, country_name, country_iso, level_name, target_name, admin_level, polygon_similarity_th=0.7):
    """ Get polygon for a target_name at a specific level within a country_name from the full admin GDF."""
    try:
        #Verify that the country exist otherwise take the country with the highest similarity
        if country_name not in gdf_file["ADMIN_0"].unique() :
            #Option 1 : Use the ISO
            if country_iso in gdf_file["iso3_code"].unique() :
                choices = gdf_file.loc[gdf_file["iso3_code"]==country_iso]
            #Option 2 : Look for the real name of the country with buffing
            else :
                country_name = find_closest_country(country_name, gdf_file)
                choices = gdf_file.loc[gdf_file["ADMIN_0"]==country_name]
        else :
            choices = gdf_file.loc[gdf_file["ADMIN_0"]==country_name]

        # Direct matching
        if level_name != "ADMIN_0" :
            matches = choices[choices[level_name].str.contains(target_name, na=False, regex=False)]
        else :
            matches = choices

        # Remove admin words and retry
        if matches.empty :
            target_name_modified = remove_admin_words(target_name)
            matches = choices[choices[level_name].str.contains(target_name_modified, na=False, regex=False)]

        # Similarity search (threshold ≥ polygon_similarity_th)
        if matches.empty:
            similarities = choices[level_name].dropna().apply(
                lambda x: rotated_levenshtein_similarity(str(x), target_name)
            )
            # Select rows >= polygon_similarity_th similarity
            similar_idx = similarities[similarities >= polygon_similarity_th].index

            if len(similar_idx) > 0:
                matches = choices.loc[similar_idx]

        # Similarity with the target_name_modified
        if matches.empty:
            similarities = choices[level_name].dropna().apply(
                lambda x: rotated_levenshtein_similarity(str(x), target_name_modified)
            )
            # Select rows >= polygon_similarity_th similarity
            similar_idx = similarities[similarities >= polygon_similarity_th].index

            if len(similar_idx) > 0:
                matches = choices.loc[similar_idx]

        # Return if matches were found
        if not matches.empty:
            return matches.copy()

    except Exception as e:
        LOGGER.error("[get_polygon] Error: %s", e)
    return None

def get_polygon_for_geometry(geom, country_name, gpd_files, level=2):
    """
    Find the administrative polygon containing the geometry at the specified level.

    Parameters:
    - geom: shapely Point or Polygon
    - country_name: string, country name matching 'NAME_0' in ADM_0 layer
    - gpd_files: dict with keys 'ADM_0', 'ADM_1', 'ADM_2' holding GeoDataFrames
    - level: int, either 0, 1 or 2

    Returns:
    - GeoDataFrame with matching polygon(s) at requested level, or None if not found
    """
    adm0_gdf = gpd_files["ADM_0"]
    adm1_gdf = gpd_files["ADM_1"]
    adm2_gdf = gpd_files["ADM_2"]

    # Filter country in ADM_0
    if country_name not in adm0_gdf["ADMIN_0"].unique() :
        country_name = find_closest_country(country_name, adm0_gdf)

    adm0_country = adm0_gdf[adm0_gdf["ADMIN_0"] == country_name]
    if adm0_country.empty:
        return None  # country not found

    if level == 0 :
        # Reuturn adm0 polygons
        return adm0_country

    # Filter ADM_1 to those inside the country
    adm1_country = adm1_gdf[adm1_gdf["ADMIN_0"] == country_name]

    if level == 1 :
        # Return adm1 polygons intersecting geometry
        adm1_match = adm1_country[adm1_country.intersects(geom)]
        return adm1_match if not adm1_match.empty else None

    elif level == 2:
        # Find matching ADM_1 polygon(s) first
        adm1_match = adm1_country[adm1_country.intersects(geom)]
        if adm1_match.empty:
            return None

        # Filter ADM_2 to those inside matched ADM_1
        adm2_candidates = adm2_gdf[
            adm2_gdf["ADMIN_1"].isin(adm1_match["ADMIN_1"].unique())
        ]

        # Find ADM_2 polygons intersecting the geometry
        adm2_match = adm2_candidates[adm2_candidates.intersects(geom)]
        return adm2_match if not adm2_match.empty else None

def fallback_country_union(gdf_file, countries, iso_countries):
    """Fallback: Combine polygons of all possible countries"""
    country_polygons = []
    for country, country_iso in zip(countries, iso_countries):
        df_gpd = get_polygon(gdf_file["ADM_0"], country, country_iso, "ADMIN_0", country, 0)
        if df_gpd is not None:
            df_gpd["finest_level"] = 0
            df_gpd["locationOsm"] = country
            df_gpd["locationPolygon"] = country
            df_gpd["flag_geocoding_osm"] = 0
            df_gpd["flag_geocoding_country"] = 1
            country_polygons.append(df_gpd)

    if country_polygons:
        combined = pd.concat(country_polygons)
        combined["geometry"] = unary_union(combined["geometry"])
        # combined["geometry"] = MultiPolygon(combined["geometry"])
        # combined["geometry"] = GeometryCollection(combined["geometry"].tolist())
        combined = combined.iloc[[0]]
        return combined
    
    # If no columns found 
    empty_cols = [
        "finest_level",
        "locationOsm",
        "locationPolygon",
        "flag_geocoding_osm",
        "flag_geocoding_country",
        "geometry"
    ]

    # Create a one-row dataframe with NaN / None
    empty_df = pd.DataFrame(
        {col: [None] for col in empty_cols}
    )
    print("Fail to find country polygon")
    return empty_df

def gather_to_lowest_admin(df_locations, gpd_files, lowest_level):
    """
    Downgrades all polygons to the lowest admin level available
    """
    geometries = []
    locations_names = []
    layer_name = f"ADM_{lowest_level}"

    for _, row in df_locations.iterrows():
        try:
            if row["finest_level"] == lowest_level:
                geom = clean_geometry(row["geometry"])
                if geom and not geom.is_empty :
                    geometries.append(geom)
                    locations_names.append(row["locationPolygon"])
            else:
                conditions = (gpd_files[layer_name]["ADMIN_0"] == row["ADMIN_0"])
                if lowest_level >= 1:
                    conditions &= gpd_files[layer_name]["ADMIN_1"] == row["ADMIN_1"]
                if lowest_level == 2:
                    conditions &= gpd_files[layer_name]["ADMIN_2"] == row["ADMIN_2"]
                matches = gpd_files[layer_name].loc[conditions]

                geometries.extend(matches["geometry"].tolist())
                locations_names.extend(matches[f"ADMIN_{lowest_level}"].tolist())
        except Exception as e:
            LOGGER.error("[gather admin fallback] Error: %s", e)

    # Merge the polygons
    if not geometries:
        return None, []
    
    merged_geometry = sanitize_and_merge_geometries(geometries)

    if not merged_geometry or merged_geometry.is_empty:
        return None, locations_names

    return merged_geometry, locations_names

#### Queries nominatim and find best match

def query_nominatim(location, country, max_retries=2, initial_delay=1, timeout=10):
    """
    Make nominatim query with robust error handling
    From location and country, return a OSM object 
    """
    # Initialize geolocator with longer timeout
    geolocator = gpy.geocoders.Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=timeout)

    if not location:
        query = f"{country}"
    else:
        query = f"{location}, {country}"

    for attempt in range(max_retries):
        try:
            result = geolocator.geocode(
                query,
                exactly_one=True,
                language="en",
                addressdetails=True,
                geometry="geojson"
            )
            return result

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == max_retries - 1:  # Last attempt
                LOGGER.error("[query_nominatim] Failed after %i attempts: %s", max_retries, e)
                return None

            # Exponential backoff
            sleep_time = initial_delay * (2 ** attempt)
            LOGGER.info("[query_nominatim] Attempt %i failed. Retrying in %.1f seconds...", attempt + 1, sleep_time)
            time.sleep(sleep_time)

        except Exception as e:
            LOGGER.error("[query_nominatim] Unexpected error: %s", e)
            return None
    return None

# def query_reverse_geocode(coords, lang, max_retries=2, initial_delay=1, timeout=10):
#     """
#     Make reverse nominatim query with robust error handling
#     From coordinates, return an OSM location object 
#     """
#     # Initialize geolocator with longer timeout
#     geolocator = gpy.geocoders.Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=timeout)

#     for attempt in range(max_retries):
#         try:
#             reverse_result = geolocator.reverse(coords, exactly_one=True, addressdetails=True, language=lang, zoom=13)
#             return reverse_result

#         except (GeocoderTimedOut, GeocoderServiceError) as e:
#             if attempt == max_retries - 1:  # Last attempt
#                 LOGGER.error("[query_nominatim] Failed after %i attempts: %s", max_retries, e)
#                 return None

#             # Exponential backoff
#             sleep_time = initial_delay * (2 ** attempt)
#             LOGGER.info("[query_nominatim] Attempt %i failed. Retrying in %.1fs...", attempt + 1, sleep_time)
#             time.sleep(sleep_time)

#         except Exception as e:
#             LOGGER.error("[query_nominatim] Unexpected error: %s", e)
#             return None
#     return None

def query_reverse_geocode(coords, lang, max_retries=2, initial_delay=1, timeout=10, zoom=13):
    """
    Parallel-safe reverse geocode with SQLite caching.
    """

    lat, lon = float(coords[0]), float(coords[1])

    # 1. Check cache first
    with _cache_lock:  # Lock needed for SQLite SELECT when multiple writers exist
        row = _cur.execute("""
            SELECT result FROM reverse_cache
            WHERE lat=? AND lon=? AND lang=? AND zoom=?
        """, (lat, lon, lang, zoom)).fetchone()

    if row:
        # Reconstruct geopy Location object from stored JSON
        try:
            return gpy.location.Location(**json.loads(row[0]))
        except Exception:
            pass  # If reconstruction fails, fall back to Nominatim

    # 2. Create geolocator
    geolocator = gpy.geocoders.Nominatim(
        user_agent=NOMINATIM_USER_AGENT,
        timeout=timeout
    )

    # 3. Retry logic
    for attempt in range(max_retries):

        try:
            reverse_result = geolocator.reverse(
                (lat, lon),
                exactly_one=True,
                addressdetails=True,
                language=lang,
                zoom=zoom
            )

            # 4. Cache result (serialize geopy Location object)
            if reverse_result is not None:
                loc_dict = {
                    "address": reverse_result.raw.get("address"),
                    "latitude": reverse_result.latitude,
                    "longitude": reverse_result.longitude,
                    "raw": reverse_result.raw,
                }
                loc_json = json.dumps(loc_dict)

                with _cache_lock:
                    _cur.execute("""
                        INSERT OR REPLACE INTO reverse_cache
                        (lat, lon, lang, zoom, result)
                        VALUES (?, ?, ?, ?, ?)
                    """, (lat, lon, lang, zoom, loc_json))
                    _conn.commit()

            return reverse_result

        except (GeocoderTimedOut, GeocoderServiceError) as e:

            if attempt == max_retries - 1:
                LOGGER.error("[query_nominatim] Failed after %i attempts: %s", max_retries, e)
                return None

            sleep_time = initial_delay * (2 ** attempt)
            LOGGER.info("[query_nominatim] Attempt %i failed. Retrying in %.1fs...",
                        attempt + 1, sleep_time)
            time.sleep(sleep_time)

        except Exception as e:
            LOGGER.error("[query_nominatim] Unexpected error: %s", e)
            return None

    return None

def find_best_match(loc_clean, address, similarity_th, print_info):
    """
    Match the best location from reverse geocode result
    """
    best_sim = 0
    best_info = {"admin_level":0}

    for address_key in address.keys() :
        found = False
        for _, admin_info in LOCATION_LEVEL_MAPPING.items():
            admin_level = admin_info['admin_level']
            admin_field = f"ADMIN_{admin_level}"
            for key in admin_info['nominatim_keys']:
                if key==address_key:
                    val = address[key]
                    val_clean = remove_admin_words(str(val))
                    sim = rotated_levenshtein_similarity(loc_clean, val_clean)

                    if print_info:
                        LOGGER.info("Found geocoding at resolution %s, Initial: %s, Geocoded: %s, Similarity: %.2f", admin_level, loc_clean, val, sim)
                    # print("Found geocoding at resolution %s, Initial: %s, Geocoded: %s, Similarity: %.2f", admin_level, loc_clean, val, sim)

                    if sim == 1 :
                        found = True
                        best_sim = sim
                        best_info = {
                            "sim": sim,
                            "admin_level": admin_level,
                            "admin_field": admin_field,
                            "name": val,
                            "key": key
                        }
                        return best_info, best_sim
                    
                    if sim >= similarity_th and sim > best_sim : #and admin_level>=best_info["admin_level"]:
                        found = True
                        best_sim = sim
                        best_info = {
                            "sim": sim,
                            "admin_level": admin_level,
                            "admin_field": admin_field,
                            "name": val,
                            "key": key
                        }
                    break
            if found :
                break
        # If the address key is not found in the location, it mean it's associated with an ADMIN_3
        if not found :
            admin_level = 3
            admin_field = f"ADMIN_{admin_level}"

            val = address[address_key]
            val_clean = remove_admin_words(str(val))
            sim = rotated_levenshtein_similarity(loc_clean, val_clean)
            if print_info:
                LOGGER.info("Found geocoding at resolution %s, Initial: %s, Geocoded: %s, Similarity: %.2f", admin_level, loc_clean, val, sim)
            # print("Found geocoding at resolution %s, Initial: %s, Geocoded: %s, Similarity: %.2f", admin_level, loc_clean, val, sim)

            #If exact match, return it directly
            if sim == 1 :
                best_sim = sim
                best_info = {
                    "sim": sim,
                    "admin_level": admin_level,
                    "admin_field": admin_field,
                    "name": val,
                    "key": key
                }
                return best_info, best_sim

            elif sim >= similarity_th and sim > best_sim :#and admin_level>=best_info["admin_level"]:
                best_sim = sim
                best_info = {
                    "sim": sim,
                    "admin_level": admin_level,
                    "admin_field": admin_field,
                    "name": val,
                    "key": key
                }
    return best_info, best_sim

#### To save files

def atomic_gpkg_save(gdf, target_path, layer_name="multipolygons"):
    """Save to a temporary file then rename (atomic operation)"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Save to temp file
        temp_path = os.path.join(temp_dir, "temp.gpkg")
        gdf.to_file(temp_path, layer=layer_name, driver="GPKG")

        # Remove existing file if it exists
        if os.path.exists(target_path):
            os.remove(target_path)

        # Move to final location (atomic on Unix, may need copy on Windows)
        shutil.move(temp_path, target_path)
        return True
    except Exception as e:
        LOGGER.error("[Atomic save] failed: %s", e)
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def save_df_geo(df_geo, save_path, res_savename, split_lowest_levels) :
    """Save a GeoDataFrame to a GeoPackage file with standardized CRS and naming."""
    save_df = df_geo.copy()
    save_df = delistify_cols(save_df)
    save_gdf = gpd.GeoDataFrame(save_df, geometry='geometry')
    save_gdf = save_gdf.set_crs("EPSG:4326", allow_override=True)

    if save_path :
        try:
            suffix = "_geo_split_lowest" if split_lowest_levels else "_geo"
            suffix = suffix + f"_v{dt.datetime.now().strftime('%d%m%y')}"

            #Save gpkg
            # gpkg_path = save_path + f"{res_savename}{suffix}.gpkg"
            gpkg_path = os.path.join(save_path, f"{res_savename}{suffix}.gpkg")
            if not atomic_gpkg_save(save_gdf, gpkg_path):
                raise Exception(f"[GeoPackage Save Error] Failed to save GeoPackage to {gpkg_path}")
        except Exception as e:
            LOGGER.error("[GeoPackage Save Error] %s", e)

#### Optimize geocoding and work per unique location found

##### Functions for nominatim

def find_best_nomin(location, countries, countries_iso, similarity_th, print_info=False) :
    """Query Nominatim for a location across candidate countries and
    return the best matching result with similarity evaluation."""
    best_result = None
    best_sim = 0

    #If extracted location is too long and correspond to a sentence, return None, None
    if len(location) > 20 :
        return None, None

    for curr_country, curr_iso in zip(countries, countries_iso) :
        # print(curr_country, curr_iso)
        nom_result = query_nominatim(location, curr_country)

        if nom_result is None:
            return None, None

        # Evaluate similarity
        loc_clean = remove_admin_words(location)
        # print(f"Location {location}, location cleaned {loc_clean}")
        coords = (nom_result.latitude, nom_result.longitude)
        address = nom_result.raw.get("address", {}) if nom_result and isinstance(nom_result.raw, dict) else {}

        match_info, sim = find_best_match(loc_clean, address, similarity_th, print_info)
        if sim > best_sim:
            best_sim = sim
            best_result = {
                **match_info,
                "coords": coords,
                "country": curr_country,
                "country_iso" : curr_iso
            }
        if sim == 1 :
            break
    return nom_result, best_result

##### Convert individual locations to polygons

def try_fallback_strategies(gdf_file, best_nomin, best_result, adm_lev):
    """Attempt alternative strategies to match an administrative polygon
    when the direct lookup fails (alternative Nominatim keys, language-based fallbacks)."""
    # Strategy 1: Alternative nominatim keys
    try :
        fallback_address = best_nomin.raw.get("address", {})
        for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
            if nomin_key_admin in fallback_address:
                df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"], best_result["country_iso"],
                                f"ADMIN_{adm_lev}", fallback_address[nomin_key_admin], adm_lev)
                if df_gpd is not None:
                    return df_gpd

        # Strategy 2: Language fallbacks (with rate limiting)
        language = LANGUAGES.get(best_result["country"][0] if isinstance(best_result["country"], list) else best_result["country"])
        for lang in [language, "fr", "es", "de"]:
            if lang:  # Skip None languages
                coords = (best_nomin.latitude, best_nomin.longitude)
                address = query_reverse_geocode(coords, lang)
                for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
                    if nomin_key_admin in address:
                        df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"], best_result["country_iso"],
                                        best_result["admin_field"], address[nomin_key_admin], adm_lev)
                        if df_gpd is not None:
                            return df_gpd
    except Exception as e :
        LOGGER.warning("[try_fallback_strategies] %s. Falling back to country level.", e)
        return None

def try_nominatim_key_fallback(gdf_file, best_nomin, best_result, adm_lev):
    """
    Strategy 1 only: try alternative Nominatim keys.
    """
    try:
        fallback_address = best_nomin.raw.get("address", {})
        for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
            if nomin_key_admin in fallback_address:
                df_gpd = get_polygon(
                    gdf_file[f"ADM_{adm_lev}"],
                    best_result["country"],
                    best_result["country_iso"],
                    f"ADMIN_{adm_lev}",
                    fallback_address[nomin_key_admin],
                    adm_lev
                )
                if df_gpd is not None:
                    return df_gpd

        return None  # signal: API fallback may be needed

    except Exception as e:
        LOGGER.warning("[try_fallback_local_strategies] %s", e)
        return None

def try_translate_language_fallback(gdf_file, best_nomin, best_result, adm_lev):
    """
    Strategy 2 only: language-based reverse geocoding.
    MUST BE RUN SEQUENTIALLY (uses Nominatim API)
    """
    try:
        language = LANGUAGES.get(
            best_result["country"][0] if isinstance(best_result["country"], list)
            else best_result["country"]
        )

        coords = (best_nomin.latitude, best_nomin.longitude)

        for lang in [language, "fr", "es", "de"]:
            if not lang:
                continue

            address = query_reverse_geocode(coords, lang)
            if not address:
                continue

            for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
                if nomin_key_admin in address:
                    df_gpd = get_polygon(
                        gdf_file[f"ADM_{adm_lev}"],
                        best_result["country"],
                        best_result["country_iso"],
                        best_result["admin_field"],
                        address[nomin_key_admin],
                        adm_lev
                    )
                    if df_gpd is not None:
                        return df_gpd

        return None

    except Exception as e:
        LOGGER.warning("[try_fallback_API_strategies] %s", e)
        return None

def try_geojson_fallback(gdf_file, best_nomin, best_result, location):
    """Fallback using Nominatim's geojson geometry data"""
    if "geojson" not in best_nomin.raw.keys():
        return None

    try:
        coords = best_nomin.raw['geojson']['coordinates']
        geom_type = best_nomin.raw['geojson']['type'].strip().lower()

        if geom_type == 'point':
            geom = Point(coords[0], coords[1])
        elif geom_type == 'polygon':
            geom = Polygon(coords[0])
        elif geom_type == 'multipolygon':
            geom = MultiPolygon([Polygon(p[0]) for p in coords])
        else:
            return None

        df_gpd = get_polygon_for_geometry(geom, best_result["country"], gdf_file, level=best_result['admin_level'])

        if df_gpd is not None:
            return df_gpd

    except Exception as e:
        LOGGER.error("[Geojson fallback] : %s", e)
        return None

def prepare_result_df(df_gpd, best_result, location, country_flag=0, osm_flag=0):
    """Enrich a matched polygon GeoDataFrame row with geocoding metadata and location info."""
    return df_gpd.assign(
        finest_level=best_result["admin_level"],
        locationOsm=best_result["name"],
        locationPolygon=df_gpd[best_result["admin_field"]],
        flag_geocoding_country=country_flag,
        flag_geocoding_osm=osm_flag,
        location=location
    )

def geocode_from_nominatim_output_optimized(gdf_file, location, best_nomin, best_result, countries, iso_countries, print_info=False):
    """Match a Nominatim geocoding result to the best administrative boundary polygon,
    using fallbacks when necessary, and return the corresponding GeoDataFrame row."""
    try:
        step = "top"
        if not best_result:
            step = "fallback_country_union"
            return fallback_country_union(gdf_file, countries, iso_countries).assign(location=location)

        adm_lev = int(best_result["admin_level"])

        while adm_lev > 0:
            df_gpd = None
            osm_flag = 0

            if adm_lev <= 2:
                step = "get_polygon"
                df_gpd = get_polygon(
                    gdf_file[f"ADM_{adm_lev}"],
                    best_result["country"],
                    best_result["country_iso"],
                    best_result["admin_field"],
                    best_result["name"],
                    adm_lev
                )
            else:
                # force admin level to 2 if higher than 2
                adm_lev = 2
                best_result["admin_field"] = 'ADMIN_2'
                best_result["admin_level"] = 2
                df_gpd = None

            # If not found → try fallback strategies
            if df_gpd is None:
                step = "try_fallback_strategies"
                df_gpd = try_fallback_strategies(gdf_file, best_nomin, best_result, adm_lev)
                # df_gpd = try_nominatim_key_fallback(gdf_file, best_nomin, best_result, adm_lev)

            # If still not found → try geojson fallback
            if df_gpd is None:
                step = "try_geojson_fallback"
                df_gpd = try_geojson_fallback(gdf_file, best_nomin, best_result, location)
                osm_flag=1

            # If something was found → prepare and return
            if df_gpd is not None:
                step = "prepare_result_df"
                return prepare_result_df(df_gpd, best_result, location, osm_flag=osm_flag)
            
            # If we got here, nothing was found → decrease admin level
            adm_lev -= 1
            best_result["admin_field"] = f"ADMIN_{adm_lev}"
            
        # If loop finishes without returning anything
        return fallback_country_union(gdf_file, countries, iso_countries).assign(location=location)
    
    except Exception as e:
        print(step)
        LOGGER.warning("[geocode_from_nomin_output_optimized] %s. Falling back to country level.", e)
        return fallback_country_union(gdf_file, countries, iso_countries).assign(location=location)

def run_parallel_geocode(nom_loc_dict, unique_locations_countries, unique_locations_countries_iso, gdf_file, print_info=False, max_workers=None):
    """Run geocoding for multiple locations in parallel using ThreadPoolExecutor,
    combining results into a single DataFrame."""
    results = []

    # run in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                geocode_from_nominatim_output_optimized,
                gdf_file,
                loc,                              
                best_nomin,
                best_result,
                unique_locations_countries[(loc, country)],  
                unique_locations_countries_iso[(loc, country)],
                print_info
            ): (loc, country)
            for (loc, country), (best_nomin, best_result) in nom_loc_dict.items()
        }

        # for future in futures:
        for future in tqdm(futures, desc="Geocoding locations"): # Version with prints from the function called
            #location = futures[future]
            try:
                df = future.result()
                if df is not None:
                    results.append(df)
            except Exception as e:
                loc, country = futures[future]
                LOGGER.error("Error processing (%s, %s): %s", loc, country, e)

    # combine into single DataFrame
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()

##### Associate rows with multiple locations to unique polygons

def associate_locations_to_polygons(row, df_geo_individual_locs, gdf_file, split_lowest_levels=True, polygon_source="GAUL") :
    """Associate one row of locations with administrative boundary polygons,
    merging geometries to the lowest (or multiple) admin levels and returning
    a GeoDataFrame row with enriched metadata."""
    if row["location"]:  # check if list is non-empty
        df_locations = df_geo_individual_locs.loc[
            df_geo_individual_locs["location"].isin(row["location"])
        ]
    elif row["country"]:
        df_locations = df_geo_individual_locs.loc[
            df_geo_individual_locs["location"].isin(row["country"])
        ]
    else :
        df_locations = df_geo_individual_locs.loc[
                    df_geo_individual_locs["location"].isin(row["country_kw"])
                ]

    df_geo_output = pd.DataFrame()

    # If no matching found, return an empty file
    # if df_locations.empty:
    if df_locations["geometry"].isna().all():
        df_empty = pd.DataFrame([row])  # base row

        # Add all expected output columns filled with NaN or defaults
        df_empty["geometry"] = np.nan
        df_empty["locationLowestAdmin"] = np.nan
        df_empty["flag_geocoding_country"] = np.nan
        df_empty["flag_geocoding_osm"] = np.nan
        df_empty["locationOsm"] = np.nan
        df_empty["locationPolygon"] = np.nan
        df_empty["iso3_code"] = np.nan

        if polygon_source == "GAUL":
            for code in ["gaul0_code", "gaul1_code", "gaul2_code"]:
                df_empty[code] = np.nan

        # Impact fields also NaN
        df_empty["impactValue"] = np.nan
        df_empty["impactUnit"] = np.nan
        df_empty["impactValueApprox"] = np.nan

        return df_empty
    
    #Retrieve the lowest admin level
    lowest_level = df_locations["finest_level"].min()
    highest_level = df_locations["finest_level"].max()

    if split_lowest_levels :
        highest_level = df_locations["finest_level"].max()
    else :
        highest_level = lowest_level

    rows_to_append = []
    #Merge all the locs to the lewest admin levels
    for merge_level in range(lowest_level, highest_level+1) :
        layer_name = f"ADM_{merge_level}"
        df_location_subset = df_locations.loc[df_locations["finest_level"]>=merge_level]
        merged_geometry, location_names = gather_to_lowest_admin(df_location_subset, gdf_file, merge_level)
        
        flag_country_count = (
            df_location_subset
            .loc[df_location_subset["flag_geocoding_country"] == 1, "location"]
            .nunique()
        )

        # Count unique locations where the OSM flag == 1
        flag_osm_count = (
            df_location_subset
            .loc[df_location_subset["flag_geocoding_osm"] == 1, "location"]
            .nunique()
        )

        df_row_append = pd.DataFrame([row])
        df_row_append["geometry"] = merged_geometry
        df_row_append["locationLowestAdmin"] = layer_name
        # df_row_append["flag_geocoding_country"] = df_location_subset['flag_geocoding_country'].sum()#count_flag_geocoding_country
        # df_row_append["flag_geocoding_osm"] = df_location_subset['flag_geocoding_osm'].sum()#count_flag_geocoding_osm
        df_row_append["flag_geocoding_country"] = flag_country_count
        df_row_append["flag_geocoding_osm"] = flag_osm_count
        df_row_append["locationOsm"] = [df_location_subset["locationOsm"].unique().tolist()]
        df_row_append["locationPolygon"] = [location_names]#[df_location_subset["locationPolygon"].unique().tolist()]

        # For the codes, take the list
        df_row_append["iso3_code"] = [df_location_subset["iso3_code"].unique().tolist()]
        if polygon_source == "GAUL" :
            for code in ["gaul0_code", "gaul1_code", "gaul2_code"] :
                df_row_append[code] = df_location_subset[code].unique().tolist()

        # Remove the impact value if it's not the lowest admin level
        if merge_level != lowest_level :
            df_row_append["impactValue"] = np.nan
            df_row_append["impactUnit"] = np.nan
            df_row_append["impactValueApprox"] = np.nan

        rows_to_append.append(df_row_append)
    df_geo_output = pd.concat(rows_to_append, ignore_index=True)
    return df_geo_output

def run_parallel_associate(df_geo, df_geo_individual_locs, gdf_file, split_lowest_levels=True, polygon_source="GAUL", max_workers=None):
    """
    Associate locations in df_geo with polygons from df_geo_individual_locs in parallel.

    This function runs `associate_locations_to_polygons` for each row of df_geo in parallel,
    using a ThreadPoolExecutor. The results are concatenated into a single DataFrame.

    Args:
        df_geo (pd.DataFrame): DataFrame containing rows of location information to process.
        df_geo_individual_locs (pd.DataFrame): DataFrame with geocoded individual locations.
        gdf_file (dict of GeoDataFrames): Dictionary of GeoDataFrames for different admin levels.
        split_lowest_levels (bool): If True, associates each location with polygons at multiple admin levels.
                                     If False, associates only at the lowest level.
        polygon_source (str): Source of polygon codes to store (default: "GAUL").
        max_workers (int or None): Number of threads to use; None means default.

    Returns:
        pd.DataFrame: Concatenated DataFrame of all association results.
    """
    results = []

    # convert rows to dictionaries to pass to subprocesses
    rows = df_geo.to_dict("records")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                associate_locations_to_polygons,
                row,
                df_geo_individual_locs,
                gdf_file,
                split_lowest_levels,
                polygon_source
            ): i
            for i, row in enumerate(rows)
        }

        # for future in futures:
        for future in tqdm(futures, desc="Merging locations"): ### VERSION WITH TRACKING PRINT INFORMATIONS
            i = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    results.append(df)
            except Exception as e:
                row = rows[i]
                debug_subset = {
                    key: row.get(key, "MISSING")
                    for key in ["location", "country", "country_kw", "country_iso", "country_iso3_kw"]
                }
                LOGGER.error("Error processing row %i: %s", i, e)
                LOGGER.error("Type of row: %s", type(row))
                LOGGER.error("Full row content:\n%s", pprint.pformat(debug_subset, indent=4))
                LOGGER.error("Traceback:\n%s", traceback.format_exc())

    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()

def run_parallel_in_batches(df_geo, df_geo_individual_locs, gdf_file, batch_size=1000, **kwargs):
    """
    Process `df_geo` in batches, running `run_parallel_associate` in parallel for each batch.

    This function breaks the DataFrame into batches to limit memory usage and thread overload,
    then concatenates the results.

    Args:
        df_geo (pd.DataFrame): DataFrame containing location rows to process.
        df_geo_individual_locs (pd.DataFrame): DataFrame of geocoded individual locations.
        gdf_file (dict of GeoDataFrames): Dictionary of GeoDataFrames by admin level.
        batch_size (int): Number of rows per batch.
        **kwargs: Additional keyword arguments to pass to `run_parallel_associate`.

    Returns:
        pd.DataFrame: Concatenated DataFrame of all results, or empty DataFrame if none.
    """
    results = []
    for start in range(0, len(df_geo), batch_size):
        end = start + batch_size
        df_batch = df_geo.iloc[start:end]
        res = run_parallel_associate(df_batch, df_geo_individual_locs, gdf_file, **kwargs)
        if res is not None and not res.empty:
            results.append(res)
        # free memory between batches
        gc.collect()
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

##### Global function to perform the whole geocoding

def geocode_df_to_polygon_by_unique_loc(df, similarity_th=0.2, print_info=False, save_path=False, res_savename=False, polygon_source="GAUL") :
    """
    Geocodes a DataFrame of locations into administrative polygons.

    This function processes a DataFrame containing location and country information,
    resolves each unique location via Nominatim geocoding, and then associates the
    results with corresponding administrative polygons (e.g., GAUL).

    The process includes:
        1. Preparing and normalizing location and country columns.
        2. Extracting all unique locations and their associated countries.
        3. Running geocoding for each unique location.
        4. Converting geocoding results into polygons.
        5. Associating locations in the original DataFrame to polygons.
        6. Saving the output to file (optional).

    Parameters:
        df (DataFrame): Input dataset with location and country columns.
        similarity_th (float): Similarity threshold for geocoding matches.
        print_info (bool): Whether to print progress information.
        save_path (str/bool): Path to save results, or False to skip saving.
        res_savename (str/bool): Filename for saving results.
        polygon_source (str): Polygon dataset source, e.g., "GAUL".

    Returns:
        tuple: (df_geo_output_split, df_geo_output)
            df_geo_output_split — DataFrame with split lowest-level polygons.
            df_geo_output — DataFrame with complete polygon association results.
    """
    # Prepare dataset
    df_geo = deepcopy(df)

    if "country_kw" in df_geo.columns :
        col_to_list = ["location", "country", "country_kw"]
        df_type = "llm"
    else :
        col_to_list = ["location", "country"]
        df_type = "labelled"

    # for col in col_to_list : 
    #     df_geo[col] = df_geo[col].apply(
    #         lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.strip().startswith("[") else ([x] if pd.notna(x) else None)
    #     )

    df_geo[col_to_list] = df_geo[col_to_list].map(lambda x: listify_strings(x))


    # Open Polygons
    gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)

    # Collect unique locations and associated countries
    start = time.time()
    unique_loc_with_country, unique_locations_countries, unique_locations_countries_iso = identify_robust_country(df_geo)
    end = time.time()
    time_open = (end - start) / 60
    if print_info :
        LOGGER.info("Number of unique locations : %s", len(unique_locations_countries))
        LOGGER.info("Time to identify all locations %.2fmins", time_open)

    # Run nominatim for each loc
    start = time.time()
    nom_loc_dict = {}
    for (loc, country) in unique_loc_with_country :
        key = (loc, country)
        if key not in nom_loc_dict:
            # countries = unique_locations_countries[loc]
            # countries_iso = unique_locations_countries_iso[loc]
            countries = list(unique_locations_countries.get(key, set()))#[country]
            countries_iso = list(unique_locations_countries_iso.get(key, set()))

            nom_loc_dict[loc] = find_best_nomin(loc, countries, countries_iso, similarity_th, print_info=False)
    end = time.time()
    time_open = (end - start) / 60
    if print_info :
        LOGGER.info("Time to nominatim all locations %.2fmins", time_open)

    # Convert nominatim output to polygons
    start = time.time()
    max_workers = min(10, (os.cpu_count() or 1) + 2)
    df_geo_individual_locs = run_parallel_geocode(nom_loc_dict, unique_locations_countries, unique_locations_countries_iso, gpd_files, print_info=False, max_workers=max_workers)
    end = time.time()
    time_open = (end - start) / 60
    if print_info:
        LOGGER.info("Time to geocode all locations %.2fmins", time_open)

    # Gather the polygons to df_row for 2 split options
    for split_lowest_levels in [True, False] :
        start = time.time()
        max_workers = min(10, (os.cpu_count() or 1))
        df_geo_output = run_parallel_in_batches(df_geo, df_geo_individual_locs, gpd_files, split_lowest_levels=split_lowest_levels, polygon_source=polygon_source, max_workers=max_workers)
        end = time.time()
        time_open = (end - start) / 60
        if print_info :
            LOGGER.info("Time to gather all locations per rows %.2fmins", time_open)

        # Save the final df
        save_df_geo(df_geo_output, save_path, res_savename, split_lowest_levels)
        if split_lowest_levels :
            df_geo_output_split = df_geo_output.copy()

    return df_geo_output_split, df_geo_output
