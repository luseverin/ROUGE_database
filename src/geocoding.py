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
from shapely.geometry import Point, Polygon, MultiPolygon
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

import multiprocessing as mp

#Countries
import pycountry
import re
unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern_country = '|'.join(map(re.escape, unique_country_names))

# Add Geolocation and spatial information (region from cities)
from geopy.extra.rate_limiter import RateLimiter
from rapidfuzz.distance import Levenshtein

# geolocator = gpy.geocoders.Nominatim(user_agent='orienternet')
# geolocator = gpy.geocoders.Nominatim(user_agent="IFRC/0.1 (laura.hasbini@lsce.ipsl.frs)", timeout=10)

LOCATION_LEVEL_MAPPING = {
    'admin2': {'admin_level': 2, 'nominatim_keys': ['city', 'town', 'village', 'municipality',
                                                    'city_district', 'district', 'borough', 'suburb', 'subdivision',
                                                    'hamlet', 'croft', 'isolated_dwelling']},
    'admin1': {'admin_level': 1, 'nominatim_keys': ['state', 'province', 'region', 'county', 'territory', 'department', 'governorate', 'autonomous_region', 'state_district', 'district', 'metropolitan_area', 'subregion', 'zone']},
    'admin0': {'admin_level': 0, 'nominatim_keys': ['country']}
}


def rotated_levenshtein_similarity(str1, str2):
    """Compute the best Levenshtein similarity considering all rotations of words."""
    words1, words2 = str1.split(), str2.split()

    if len(words1) > 6 or len(words2) > 6:
        # Fallback: use simple similarity without permutations
        return Levenshtein.normalized_similarity(str1, str2)

    # Generate all possible word orderings (rotations) for comparison
    permutations1 = [" ".join(p) for p in itertools.permutations(words1)]
    permutations2 = [" ".join(p) for p in itertools.permutations(words2)]

    # Compute the max similarity considering all orderings
    max_similarity = max(Levenshtein.normalized_similarity(p1, p2) for p1 in permutations1 for p2 in permutations2)

    return max_similarity

list_admin_words = [
    "Regency", "Province", "State", "Department", "Region", "River",
    "Territory", "County", "District", "Municipality", "Prefecture",
    "Canton", "Commune", "Borough", "Parish", "Metropolitan Area",
    "Subregion", "Zone", "Subdivision", "Ward", "Township", "City",
    "Village", "Hamlet", "Municipality", "Governorate", "Autonomous Region",
    "County Borough", "Council Area", "Federal District", "Locality"
]

def remove_admin_words(location_str) :
    for word in list_admin_words:
        location_str = location_str.replace(word, "").strip()
    location_str = ' '.join(location_str.split())
    return location_str

def get_country_languages_dict():
    country_languages = {}
    for country in pycountry.countries:
        try:
            lang_code = langcodes.get(country.alpha_2).language
            if lang_code:
                country_languages[country.name] = lang_code
        except:
            continue
    return country_languages
LANGUAGES = get_country_languages_dict()

def clean_geometry(geom):
    """Fix invalid geometries using buffer(0)."""
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        try:
            return geom.buffer(0)
        except Exception as e:
            print(f"[clean_geometry] Failed to fix geometry: {e}")
            return None
    return geom

#### Function to Geocode one location
def match_admin1_for_row(row, gpd_files):
    """
    Given a row of df_geo and gpd_files, find the ADM1 boundary that contains/intersects the geometry.
    """
    geom = row["geometry"]
    adm0 = row["ADMIN_0"]

    adm1_match = get_polygon_for_geometry(geom, adm0, gpd_files, level=1)
    if adm1_match is not None and "ADMIN_1" in adm1_match:
        return adm1_match["ADMIN_1"].values[0]
    return None

def open_admin_gpd(ADMIN_PATH, polygon_source="GAUL") :
    gpd_files = {}
    if polygon_source == "GAUL" : 
        try :
            ##### ADMIN2 From GAUL
            gaul2 = gpd.read_file(ADMIN_PATH+"GAUL_2024_L2/GAUL_2024_L2.shp")
            gaul2 = gaul2.rename({"gaul0_name":"ADMIN_0", "gaul1_name":"ADMIN_1", "gaul2_name":"ADMIN_2"}, axis=1)
            gpd_files["ADM_2"] = gaul2

            ##### ADMIN1 From GAUL
            gaul1 = gpd.read_file(ADMIN_PATH+"GAUL_2024_L1/GAUL_2024_L1.shp")
            gaul1 = gaul1.rename({"gaul0_name":"ADMIN_0", "gaul1_name":"ADMIN_1"}, axis=1)
            gaul1["gaul2_code"] = None
            gpd_files["ADM_1"] = gaul1

            ##### ADMIN0 From Natural Earth
            ne_0 = gpd.read_file(ADMIN_PATH+"ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp")
            ne_0 = ne_0.rename({"ADMIN":"ADMIN_0", "ISO_A3" : "iso3_code"}, axis=1)
            ne_0["gaul1_code"] = None
            ne_0["gaul2_code"] = None
            ne_0 = pd.merge(ne_0, gaul1[["iso3_code", "gaul0_code"]], on="iso3_code", how="left").drop_duplicates()
            gpd_files["ADM_0"] = ne_0

        except Exception as e:
            print(f"[open_admin_gpd][GAUL] Error loading GPD files: {e}")
            return None
    elif polygon_source == "geoBoundaries" :
        try : 
            ### ADMIN 0
            geoBoundaries0 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM0.gpkg")
            geoBoundaries0 = geoBoundaries0.rename({"shapeName" : "ADMIN_0", "shapeGroup" : "iso3_code"}, axis=1)
            geoBoundaries0 = geoBoundaries0.loc[geoBoundaries0["shapeType"]=="ADM0"]
            gpd_files["ADM_0"] = geoBoundaries0

            ### ADMIN 1 
            geoBoundaries1 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM1.gpkg")
            geoBoundaries1 = geoBoundaries1.rename({"shapeName" : "ADMIN_1", "shapeGroup" : "iso3_code"}, axis=1)
            geoBoundaries1 = geoBoundaries1.loc[geoBoundaries1["shapeType"]=="ADM1"]
            geoBoundaries1 = pd.merge(geoBoundaries1, geoBoundaries0[["iso3_code", "ADMIN_0"]], on="iso3_code", how="left").drop_duplicates()
            gpd_files["ADM_1"] = geoBoundaries1

            ### ADMIN 2 
            # geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2.gpkg")
            geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2_corrected.gpkg")
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
            print(f"[open_admin_gpd][geoBoundaries] Error loading GPD files: {e}")
            return None
            #Verify that the geometries are valid 

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

def get_polygon(gdf_file, country_name, country_iso, level_name, target_name, admin_level):
    """
    Get polygon for a target_name at a specific level within a country from the full admin GPKG.
    """
    try:
        #Verify that the country exist otherwise take the country with the highest similarity
        if country_name not in gdf_file["ADMIN_0"].unique() :
            #Option 1 : Use the ISO 
            if country_iso in gdf_file["ADMIN_0"].unique() : 
                # print(f"{country_name} not in countries")
                choices = gdf_file.loc[gdf_file["iso3_code"]==country_iso]
            #Option 2 : Lookf for the real name of the country with buffing 
            else : 
                country_name = find_closest_country(country_name, gdf_file)
                choices = gdf_file.loc[gdf_file["ADMIN_0"]==country_name]
        else : 
            choices = gdf_file.loc[gdf_file["ADMIN_0"]==country_name]
        
        if level_name != "ADMIN_0" : 
            matches = choices[choices[level_name].str.contains(target_name, na=False, regex=False)]
        else : 
            matches = choices

        #Try for new matches, removing the admin words 
        if matches.empty : 
            target_name_modified = remove_admin_words(target_name)
            matches = choices[choices[level_name].str.contains(target_name_modified, na=False, regex=False)]
        if not matches.empty:
            return matches.copy()

    except Exception as e:
        # print(f"level_name : {level_name}, target_name : {target_name}")
        print(f"[get_polygon] Error: {e}")
    return None

def get_polygon_for_geometry(geom, country_name, gpd_files, level=2):
    """
    Find the administrative polygon containing the geometry at the specified level.
    
    Parameters:
    - geom: shapely Point or Polygon
    - country_name: string, country name matching 'NAME_0' in ADM_0 layer
    - gpd_files: dict with keys 'ADM_0', 'ADM_1', 'ADM_2' holding GeoDataFrames
    - level: str, either "ADM_1" or "ADM_2" (default is "ADM_2")
    
    Returns:
    - GeoDataFrame with matching polygon(s) at requested level, or None if not found
    """
    # assert level in [1, 2], "level must be '1' or '2'"

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

def query_nominatim(location, country, max_retries=2, initial_delay=1, timeout=10):
    """
    Make nominatim query with robust error handling
    """
    # Initialize geolocator with longer timeout
    # geolocator = Nominatim(user_agent="your_app_name", timeout=timeout)
    geolocator = gpy.geocoders.Nominatim(user_agent="IFRC/0.1 (laura.hasbini@lsce.ipsl.fr)", timeout=timeout)

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
                print(f"[query_nominatim] Failed after {max_retries} attempts: {e}")
                return None
            
            # Exponential backoff
            sleep_time = initial_delay * (2 ** attempt)
            print(f"[query_nominatim] Attempt {attempt + 1} failed. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"[query_nominatim] Unexpected error: {e}")
            return None
    return None

def query_reverse_geocode(coords, max_retries=2, initial_delay=1, timeout=10):
    """
    Make nominatim query with robust error handling
    """
    # Initialize geolocator with longer timeout
    # geolocator = Nominatim(user_agent="your_app_name", timeout=timeout)
    geolocator = gpy.geocoders.Nominatim(user_agent="IFRC/0.1 (laura.hasbini@lsce.ipsl.fr)", timeout=timeout)

    for attempt in range(max_retries):
        try:
            reverse_result = geolocator.reverse(coords, exactly_one=True, addressdetails=True, language=lang, zoom=13)
            return reverse_result
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == max_retries - 1:  # Last attempt
                print(f"[query_nominatim] Failed after {max_retries} attempts: {e}")
                return None
            
            # Exponential backoff
            sleep_time = initial_delay * (2 ** attempt)
            print(f"[query_nominatim] Attempt {attempt + 1} failed. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"[query_nominatim] Unexpected error: {e}")
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
        for loc_level, admin_info in LOCATION_LEVEL_MAPPING.items():
            admin_level = admin_info['admin_level']
            admin_field = f"ADMIN_{admin_level}"
            for key in admin_info['nominatim_keys']:
                if key==address_key:
                    found = True
                    val = address[key]
                    val_clean = remove_admin_words(str(val))
                    sim = rotated_levenshtein_similarity(loc_clean, val_clean)
                    if print_info:
                        print(f"Found geocoding at resolution {admin_level}, Initial: {loc_clean}, Geocoded: {val}, Similarity: {sim:.2f}")
                    
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

                    if sim >= similarity_th and sim > best_sim : #and admin_level>=best_info["admin_level"]:
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
                print(f"Found geocoding at resolution {admin_level}, Initial: {loc_clean}, Geocoded: {val}, Similarity: {sim:.2f}")
            
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

def fallback_country_union(gdf_file, countries, iso_countries):
    """
    Fallback: Combine polygons of all possible countries
    """
    country_polygons = []
    for country, country_iso in zip(countries, iso_countries):
        df_gpd = get_polygon(gdf_file["ADM_0"], country, country_iso, "ADMIN_0", country, 0)
        if df_gpd is not None:
            df_gpd["finest_level"] = 0
            df_gpd["locationOsm"] = country
            df_gpd["locationPolygon"] = country
            df_gpd["geocoding_osm_flag"] = 0
            df_gpd["geocoding_country_flag"] = 1
            country_polygons.append(df_gpd)

    if country_polygons:
        combined = pd.concat(country_polygons)
        combined["geometry"] = unary_union(combined["geometry"])
        combined = combined.iloc[[0]]
        return combined
    return None

def gather_to_lowest_admin(df_locations, gpd_files, lowest_level, index_dict=None):
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
            # else:
            #     conditions = gpd_files[layer_name]["ADMIN_0"] == row["ADMIN_0"]
            #     if lowest_level >= 1:
            #         conditions &= gpd_files[layer_name]["ADMIN_1"] == row["ADMIN_1"]
            #     if lowest_level == 2:
            #         conditions &= gpd_files[layer_name]["ADMIN_2"] == row["ADMIN_2"]
            #     matches = gpd_files[layer_name][conditions]
            #     geometries.extend(matches["geometry"])
            #     locations_names.append(matches[f"ADMIN_{lowest_level}"].iloc[0])
            else:
                # Look up Parents polygons in precomputed index (if available)
                if index_dict and layer_name in index_dict:
                    key = tuple(row[f"ADMIN_{i}"] for i in range(row["finest_level"]))
                    matches = index_dict[layer_name].get(key, [])
                    geometries.extend(matches)
                else:
                    # Fallback: filter directly (slower)
                    conditions = (gpd_files[layer_name]["ADMIN_0"] == row["ADMIN_0"])
                    if lowest_level >= 1:
                        conditions &= gpd_files[layer_name]["ADMIN_1"] == row["ADMIN_1"]
                    if lowest_level == 2:
                        conditions &= gpd_files[layer_name]["ADMIN_2"] == row["ADMIN_2"]
                    matches = gpd_files[layer_name].loc[conditions]

                    geometries.extend(matches["geometry"].tolist())
                    locations_names.extend(matches[f"ADMIN_{lowest_level}"].tolist())
        except Exception as e:
            print(f"[gather admin fallback] Error: {e}")
    
    # Merge the polygons 
    # geometries = [clean_geometry(g) for g in geometries if g is not None]
    if not geometries:
        return None, []

    merged_geometry = unary_union(geometries)
    if not merged_geometry or merged_geometry.is_empty:
        return None, locations_names
    
    # Avoid expensive union if only one geometry
    # merged_geometry = geometries[0] if len(geometries) == 1 else unary_union(geometries)
    # merged_geometry = clean_geometry(merged_geometry)

    return merged_geometry, locations_names

# Main geocoding functions
def geocode_unique_loc(gdf_file, location, country, similarity_th, time_last_request, print_info=True):
    #Make sure countries are in list format
    countries = [country] if isinstance(country, str) else country
    try :
        best_result = None
        best_sim = 0

        for curr_country in countries :
            nom_result = query_nominatim(location, curr_country)

            if nom_result is None:
                if print_info:
                    print(f"No results for query: {location}, {curr_country}")
                return fallback_country_union(gdf_file, countries)
            # elif nom_result == "Failed" : 
            #     # Add a flag underlines that geocoding must me done again 
            #     df_gpd_failed = fallback_country_union(gdf_file, countries)
            #     df_gpd_failed["Failed"] = True
            #     return df_gpd_failed
            else : 
                if print_info:
                    print(f"Result of the query: {nom_result}")

            # Evaluate similarity
            loc_clean = remove_admin_words(location)
            coords = (nom_result.latitude, nom_result.longitude)
            address = nom_result.raw.get("address", {}) if nom_result and isinstance(nom_result.raw, dict) else {}

            match_info, sim = find_best_match(loc_clean, address, similarity_th, print_info)
            if sim > best_sim:
                best_sim = sim
                best_result = {
                    **match_info,
                    "coords": coords,
                    "country": curr_country
                }
                best_nomin = nom_result

        # If a satisfactory location is found try to match a polygon

        # If a satisfactory matching is found, and it doesn't correspond to an ADMIN 3 level, look for a GADM polygon
        if (best_result) and (best_result["admin_level"]!=3) :
            if print_info : 
                print("Best result :", best_result, " Search for polygon") 
            # Try to extract the polygon with English
            adm_lev = best_result["admin_level"]
            df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"], best_result["admin_field"], best_result["name"], adm_lev)

            #If no polygon found, loop over other nominatim_keys for the same admin 
            if df_gpd is None :
                fallback_address = best_nomin.raw.get("address", {})
                for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
                    fallback_name = address.get(nomin_key_admin)
                    if fallback_name is not None : 
                        df_gpd = get_polygon(
                            gdf_file[f"ADM_{best_result['admin_level']}"],
                            best_result["country"],
                            best_result["admin_field"],
                            fallback_name,
                            best_result["admin_level"]
                        )
                    if df_gpd is not None:
                        best_result["name"] = fallback_name
                        break
            
            #If no polygon found, loop over the languages
            if df_gpd is None : 
                language = LANGUAGES.get(best_result["country"])
                languages = [language, "fr", "es", "de"]
                for lang in languages : 
                    address, _ = query_reverse_geocode(best_result['coords'], time_last_request, best_result["country"], lang)
                    fallback_name = address.get(best_result['key'])
                    if fallback_name is None:
                        # Try alternative keys in LOCATION_LEVEL_MAPPING
                        for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
                            fallback_name = address.get(nomin_key_admin)
                            if fallback_name is not None:
                                df_gpd = get_polygon(
                                    gdf_file[f"ADM_{best_result['admin_level']}"],
                                    best_result["country"],
                                    best_result["admin_field"],
                                    fallback_name,
                                    best_result["admin_level"]
                                )
                                if df_gpd is not None:
                                    break
                    else:
                        df_gpd = get_polygon(
                            gdf_file[f"ADM_{best_result['admin_level']}"],
                            best_result["country"],
                            best_result["admin_field"],
                            fallback_name,
                            best_result["admin_level"]
                        )
                    if df_gpd is not None:
                        break

            #Add extra informations
            if df_gpd is not None:
                if print_info:
                    print(f"Best match: {best_result['name']} (sim={best_result['sim']:.2f}) at level {best_result['admin_level']}")
                df_gpd["finest_level"] = best_result["admin_level"]
                df_gpd["locationOsm"] = best_result["name"]
                df_gpd["locationPolygon"] = df_gpd[best_result["admin_field"]]
                df_gpd["geocoding_country_flag"] = 0
                df_gpd["geocoding_osm_flag"] = 0
                return df_gpd

        # If not polygon found, look to geojson output from nominatim directly
        # Use Nominatim Point/Polygon to retrive the Polygons geometry
        if "geojson" in best_nomin.raw.keys() :
            coords = best_nomin.raw['geojson']['coordinates']

            if best_nomin.raw['geojson']['type'].strip().lower() == 'point':
                geom = Point(coords[0], coords[1])
            else : 
                geom = pd.DataFrame(coords).transpose().apply(Polygon).iloc[0]

            df_gpd = get_polygon_for_geometry(geom, best_result["country"], gdf_file, level=best_result['admin_level'])

            if df_gpd is not None:
                df_gpd["finest_level"] = best_result["admin_level"]
                df_gpd["locationOsm"] = best_result["name"]
                df_gpd["locationPolygon"] = df_gpd[best_result["admin_field"]].tolist()
                df_gpd["geocoding_country_flag"] = 0
                df_gpd["geocoding_osm_flag"] = 1
                return df_gpd
        
        #If no polygon found, loop for higher levels 
            
    except Exception as e :
        if print_info:
            print(f"[geocode_unique_loc] {e}. Falling back to country level.")

    # Fallback to country level
    try :
        return fallback_country_union(gdf_file, countries)

    except Exception as e :
        print(f"[geocode_unique_loc fallback] Error: {e}")
        return None

def geocode_df_to_polygon_old(df, similarity_th=0.2, split_lowest_levels=True, print_info=False, save_path=False, res_savename=False, polygon_source="GAUL") :
    """
    For each row, perform the geocoding and create a polygon corresponding the location found
    If the gather_admin_level is True, the polygons are downgraded to the lowest resolution found
    """
    df_geo = deepcopy(df)
    if polygon_source == "GAUL" : 
        extra_columns_output = ["gaul0_code", "gaul1_code", "gaul2_code", 
                                "geometry", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon", "iso3_code"]
    else : 
        extra_columns_output = ["geometry", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon", "iso3_code"]

    df_geo_output = pd.DataFrame(columns = list(df.columns)+extra_columns_output)

    #Convet to list columns related to locations & countries
    if "country_kw" in df_geo.columns : 
        col_to_list = ["location", "country", "country_kw"]
        df_type = "llm"
    else : 
        col_to_list = ["location", "country"]
        df_type = "labelled"

    for col in col_to_list : 
        df_geo[col] = df_geo[col].apply(
            lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.strip().startswith("[") else ([x] if pd.notna(x) else None)
        )

    #Open Polygons
    start = time.time()
    gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)
    end = time.time()
    time_open = (end-start)/60
    # if print_info :
    # print(f"Time to open files {time_open}mins")

    time_last_request = time.time()

    #Convert each row to polygon
    if gpd_files is None :
        return None

    start = time.time()
    for row_index, row_data in df_geo.iterrows():
        # try : 
        locations = row_data['location']
        country = row_data["country"]
        if not country and df_type=="llm" : 
            country = row_data["country_kw"]

        # If no country is found, don't look for any polygon 
        if not country:
            df_row_append = df_geo.loc[row_index].copy()
            df_geo_output = pd.concat([df_geo_output, df_row_append], ignore_index=True)
            continue

        # If no location, change to have it as a list
        if not locations : 
            locations = [None]
        
        df_locations = []

        start_loop = time.time()
        count_geocoding_osm_flag = 0 
        count_geocoding_country_flag = 0 
        for location in locations : 
            df_loc = geocode_unique_loc(gpd_files, location, country, similarity_th, time_last_request, print_info)
            time_last_request = time.time()
            if df_loc is not None : 
                if (df_loc["geocoding_osm_flag"] == 1).any() : 
                    count_geocoding_osm_flag+=1
                if (df_loc["geocoding_country_flag"] == 1).any() : 
                    count_geocoding_country_flag+=1
                df_locations.append(df_loc)   
        if not df_locations : 
            continue
        end_loop = time.time()
        time_open = (end_loop-start_loop)/60
        # if print_info :
        # print(f"Time to geocode one row {time_open}mins")
            
        df_locations = pd.concat(df_locations, axis=0)
        df_locations = df_locations[df_locations['geometry'].notnull()]

        if df_locations.empty:
            continue
            
        #Retrieve the lowest admin level
        lowest_level = df_locations["finest_level"].min()
        highest_level = df_locations["finest_level"].max()
        
        if split_lowest_levels : 
            highest_level = df_locations["finest_level"].max()
        else : 
            highest_level = lowest_level

        #Merge all the locs to the lewest admin levels
        start_loop = time.time()
        for merge_level in range(lowest_level, highest_level+1) :
            layer_name = f"ADM_{merge_level}"
            df_location_subset = df_locations.loc[df_locations.finest_level>=merge_level]
            # print("df_location_subset :", df_location_subset)
            # print("merge_level :",merge_level)
            merged_geometry = gather_to_lowest_admin(df_location_subset, gpd_files, merge_level)

            df_row_append = df_geo.loc[row_index].copy()
            df_row_append.loc["geometry"] = merged_geometry
            df_row_append.loc["locationLowestAdmin"] = layer_name
            df_row_append.loc["geocoding_country_flag"] = count_geocoding_country_flag
            df_row_append.loc["geocoding_osm_flag"] = count_geocoding_osm_flag
            df_row_append.loc["locationOsm"] = df_location_subset["locationOsm"].unique().tolist()
            df_row_append.loc["locationPolygon"] = df_location_subset["locationPolygon"].unique().tolist()

            # For the codes, take the list 
            # print("iso3_code")
            # print(df_location_subset["iso3_code"])
            df_row_append.loc["iso3_code"] = df_location_subset["iso3_code"].unique().tolist()
            if polygon_source == "GAUL" : 
                for code in ["gaul0_code", "gaul1_code", "gaul2_code"] : 
                    df_row_append.loc[code] = df_location_subset[code].unique().tolist()
            
            # Remove the impact value if it's not the lowest admin level
            if merge_level != lowest_level : 
                df_row_append.loc["impactValue"] = np.nan
                df_row_append.loc["impactUnit"] = np.nan
                df_row_append.loc["impactValueApprox"] = np.nan
            
            # Align columns to df_geo_output
            df_row_append = pd.DataFrame([df_row_append])
            common_cols = df_geo_output.columns.intersection(df_row_append.columns)
            df_row_append = df_row_append[common_cols]
            df_geo_output = pd.concat([df_geo_output, df_row_append], ignore_index=True)
        end_loop = time.time()
        time_open = (end_loop-start_loop)/60
        # if print_info :
        # print(f"Time to merge at lowest level {time_open}mins")
        # except Exception as e : 
        #     print(f"[Row {row_index}] Error: {e}")
        #     continue
    end = time.time()
    time_open = (end-start)/60
    # if print_info :
    # print(f"Time to process all rows {time_open}mins")

    # Save 
    if save_path and res_savename:
        save_df = df_geo_output.copy()
        save_df = delistify_cols(save_df)
        save_gdf = gpd.GeoDataFrame(save_df, geometry='geometry')
        save_gdf = save_gdf.set_crs("EPSG:4326", allow_override=True)
        try:
            suffix = "_geo_split_lowest" if split_lowest_levels else "_geo"
            #Save gpkg
            gpkg_path = f"{save_path}{res_savename}{suffix}.gpkg"
            if not atomic_gpkg_save(save_gdf, gpkg_path):
                raise Exception(f"[GeoPackage Save Error] Failed to save GeoPackage to {gpkg_path}")
            # if os.path.exists(gpkg_path):
            #     os.remove(gpkg_path)
            # save_gdf.to_file(gpkg_path,
            #                 layer="multipolygons", driver="GPKG")
            
            # #Save shp
            # shp_path = f"{save_path}{res_savename}{suffix}.shp"
            # if os.path.exists(shp_path):
            #     os.remove(shp_path)
            # save_gdf.to_file(shp_path, driver="ESRI Shapefile")
        except Exception as e:
            print(f"[GeoPackage Save Error] {e}")
    return df_geo_output

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
        print(f"[Atomic save] failed: {str(e)}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

#### Optimize geocoding and work per unique location found 

def find_best_nomin(location, countries, countries_iso, similarity_th, print_info=False) : 
    best_result = None
    best_sim = 0

    #If extracted location is too long and correspond to a sentence, return None, None
    if len(location) > 20 : 
        return None, None 

    for curr_country, curr_iso in zip(countries, countries_iso) :
        nom_result = query_nominatim(location, curr_country)

        if nom_result is None:
            # if print_info:
            # print(f"No results for query: {location}, {curr_country}")
            return None, None#fallback_country_union(gdf_file, countries)
        # else : 
        #     # if print_info:
        #     print(f"Results for query: {location}, {curr_country}")
        #     print(f"Result of the query: {nom_result}")

        # Evaluate similarity
        loc_clean = remove_admin_words(location)
        coords = (nom_result.latitude, nom_result.longitude)
        address = nom_result.raw.get("address", {}) if nom_result and isinstance(nom_result.raw, dict) else {}

        match_info, sim = find_best_match(loc_clean, address, similarity_th, print_info)
        # print(match_info, sim)
        if sim > best_sim:
            best_sim = sim
            best_result = {
                **match_info,
                "coords": coords,
                "country": curr_country, 
                "country_iso" : curr_iso
            }
            # best_nomin = nom_result
        if sim == 1 : 
            break 
    # print("FINAL OUTPUT : ", nom_result, best_result)
    return nom_result, best_result

def geocode_from_nominatim_output_optimized(gdf_file, location, best_nomin, best_result, countries, iso_countries, print_info=False):
    try:
        Done_get_polygon = False
        Done_fallback = False
        Done_prepare = False

        if not best_result:
            return fallback_country_union(gdf_file, countries, iso_countries).assign(location=location)
        
        adm_lev = int(best_result["admin_level"])
        
        # Try primary polygon match
        # if adm_lev <= 2 : 
        #     df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"], best_result["country_iso"],
        #                         best_result["admin_field"], best_result["name"], adm_lev)
        # else : 
        #     # print("Found Admin 3, location :", best_result["name"], ", country : ", best_result["country"], " adm_lev :", adm_lev)
        #     adm_lev = 2 
        #     best_result["admin_field"] = 'ADMIN_2'
        #     best_result["admin_level"] = 2
        #     df_gpd = None 
        # Done_get_polygon = True

        # # print("Not found, try fallback strategies")
        # if df_gpd is None:
        #     df_gpd = try_fallback_strategies(gdf_file, best_nomin, best_result, adm_lev)
        # Done_fallback = True

        # print("Found, prepare df")
        # if df_gpd is not None:
        #     print(df_gpd)
        #     return prepare_result_df(df_gpd, best_result, location)
        # Done_prepare = True

        # # Try geojson fallback
        # print("Not found, try geojson fallback")
        # return try_geojson_fallback(gdf_file, best_nomin, best_result, location)
        while adm_lev >= 0:
            df_gpd = None  
            osm_flag = 0 

            if adm_lev <= 2:
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
                df_gpd = try_fallback_strategies(gdf_file, best_nomin, best_result, adm_lev)

            # If still not found → try geojson fallback
            if df_gpd is None:
                df_gpd = try_geojson_fallback(gdf_file, best_nomin, best_result, location)
                osm_flag=1

            # If something was found → prepare and return
            if df_gpd is not None:
                return prepare_result_df(df_gpd, best_result, location, osm_flag=osm_flag)

            # If we got here, nothing was found → decrease admin level
            adm_lev -= 1
            best_result["admin_field"] = f"ADMIN_{adm_lev}"

        # If loop finishes without returning anything
        return None        
    except Exception as e:
        print("df_gpd", df_gpd)
        print(f"Done_get_polygon {Done_get_polygon}, Done_fallback {Done_fallback}, Done_prepare {Done_prepare}")
        print(f"Exception found for adm_lev {adm_lev}, best_nomin {best_nomin}, best_result {best_result}")
        print(f"[geocode_from_nomin_output_optimized] {e}. Falling back to country level.")
        return fallback_country_union(gdf_file, countries).assign(location=location)

def try_fallback_strategies(gdf_file, best_nomin, best_result, adm_lev):
    # Strategy 1: Alternative nominatim keys
    try : 
        # print("Fallback nominatim keys")
        fallback_address = best_nomin.raw.get("address", {})
        for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
            if nomin_key_admin in fallback_address:
                # df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"],
                #                    best_result["admin_field"], fallback_address[nomin_key_admin], adm_lev)
                # print(f"Trying get_polygon with ADM_{adm_lev}, target: {fallback_address[nomin_key_admin]}")
                df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"], best_result["country_iso"],
                                f"ADMIN_{adm_lev}", fallback_address[nomin_key_admin], adm_lev)
                if df_gpd is not None:
                    return df_gpd
        
        # Strategy 2: Language fallbacks (with rate limiting)
        language = LANGUAGES.get(best_result["country"][0] if isinstance(best_result["country"], list) else best_result["country"])
        # print([language, "fr", "es", "de"])
        for lang in [language, "fr", "es", "de"]:
            # print("Test if language exist")
            if lang:  # Skip None languages
                coords = (best_nomin.latitude, best_nomin.longitude)
                address = query_reverse_geocode(coords, 
                                                best_result["country"], lang)
                # print(address)
                for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"]:
                    if nomin_key_admin in address:
                        # print(f"Trying get_polygon with ADM_{adm_lev}, target: {fallback_address[nomin_key_admin]}")
                        df_gpd = get_polygon(gdf_file[f"ADM_{adm_lev}"], best_result["country"], best_result["country_iso"],
                                        best_result["admin_field"], address[nomin_key_admin], adm_lev)
                        if df_gpd is not None:
                            return df_gpd
    except Exception as e : 
        # print(LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"]["nominatim_keys"])
        # print(f"[try_fallback_strategies] {e}. Falling back to country level.")
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
            # print(f"[Geojson fallback] : Unsupported geometry type {geom_type}")
            return None
        
        df_gpd = get_polygon_for_geometry(geom, best_result["country"], gdf_file, level=best_result['admin_level'])
        
        if df_gpd is not None:
            return df_gpd
            # return df_gpd.assign(
            #     finest_level=best_result["admin_level"],
            #     locationOsm=best_result["name"],
            #     locationPolygon=df_gpd[best_result["admin_field"]].tolist(),
            #     geocoding_country_flag=0,
            #     geocoding_osm_flag=1,
            #     location=location
            # )
    
    except Exception as e:
        print(f"[Geojson fallback] : {e}")
        return None

def prepare_result_df(df_gpd, best_result, location, country_flag=0, osm_flag=0):
    return df_gpd.assign(
        finest_level=best_result["admin_level"],
        locationOsm=best_result["name"],
        locationPolygon=df_gpd[best_result["admin_field"]],
        geocoding_country_flag=country_flag,
        geocoding_osm_flag=osm_flag,
        location=location
    )

def run_parallel_geocode(nom_loc_dict, unique_locations_countries, unique_locations_countries_iso, gdf_file, print_info=False, max_workers=None):
    results = []
    
    # run in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                geocode_from_nominatim_output_optimized,#geocode_from_nominatim_output,
                gdf_file,
                location,
                best_nomin,
                best_result,
                unique_locations_countries[location],
                unique_locations_countries_iso[location],
                print_info
            ): location
            for location, (best_nomin, best_result) in nom_loc_dict.items()
        }

        # for future in futures:
        for future in tqdm(futures, desc="Geocoding locations"): # Version with prints from the function called 
            #location = futures[future]
            try:
                df = future.result()
                if df is not None:
                    results.append(df)
            except Exception as e:
                print(f"Error processing {futures[future]}: {e}")

    # combine into single DataFrame
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()

def associate_locations_to_polygons(row, df_geo_individual_locs, gdf_file, split_lowest_levels=True, polygon_source="GAUL") :
    
    # df_locations = df_geo_individual_locs.loc[df_geo_individual_locs["location"].isin(row["location"])]
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
    # print(df_locations)

    df_geo_output = pd.DataFrame()

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

        df_row_append = pd.DataFrame([row])
        df_row_append["geometry"] = merged_geometry
        df_row_append["locationLowestAdmin"] = layer_name
        df_row_append["geocoding_country_flag"] = df_location_subset['geocoding_country_flag'].sum()#count_geocoding_country_flag
        df_row_append["geocoding_osm_flag"] = df_location_subset['geocoding_osm_flag'].sum()#count_geocoding_osm_flag
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
        
        # Align columns to df_geo_output
        # df_row_append = pd.DataFrame([df_row_append])
        # common_cols = df_geo_output.columns.intersection(df_row_append.columns)
        # df_row_append = df_row_append[common_cols]
        # print(df_row_append)
        # df_geo_output = pd.concat([df_geo_output, df_row_append], ignore_index=True)
        rows_to_append.append(df_row_append)
    df_geo_output = pd.concat(rows_to_append, ignore_index=True)
    return df_geo_output 

def run_parallel_associate(df_geo, df_geo_individual_locs, gdf_file, split_lowest_levels=True, polygon_source="GAUL", max_workers=None):
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

        for future in futures:
        # for future in tqdm(futures, desc="Merging locations"): ### VERSION WITH TRACKING PRINT INFORMATIONS 
            i = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    results.append(df)
            except Exception as e:
                print(f"Error processing row {i}: {e}")

    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()

def run_parallel_in_batches(df_geo, df_geo_individual_locs, gdf_file, batch_size=1000, **kwargs):
    results = []
    for start in range(0, len(df_geo), batch_size):
        end = start + batch_size
        df_batch = df_geo.iloc[start:end]
        # print(f"Processing rows {start}–{end}")
        res = run_parallel_associate(df_batch, df_geo_individual_locs, gdf_file, **kwargs)
        if res is not None and not res.empty:
            results.append(res)
        # free memory between batches
        gc.collect()
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

def save_df_geo(df_geo, save_path, res_savename, split_lowest_levels) :
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
            print(f"[GeoPackage Save Error] {e}")

def geocode_df_to_polygon_by_unique_loc(df, similarity_th=0.2, print_info=False, save_path=False, res_savename=False, polygon_source="GAUL") :
    # Prepare dataset 
    df_geo = deepcopy(df)

    if "country_kw" in df_geo.columns : 
        col_to_list = ["location", "country", "country_kw"]
        df_type = "llm"
    else : 
        col_to_list = ["location", "country"]
        df_type = "labelled"

    for col in col_to_list : 
        df_geo[col] = df_geo[col].apply(
            lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.strip().startswith("[") else ([x] if pd.notna(x) else None)
        )

    # Open Polygons
    gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)

    # Collect unique locations and associated countries
    start = time.time()
    unique_locations_countries = defaultdict(set)
    unique_locations_countries_iso = defaultdict(set)

    for _, row in df_geo.iterrows():
        # Handle countries 
        countries = row["country"]
        isos = row["country_iso3"]

        if not countries or not isos:
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
            for c, iso in zip(countries, isos):
                unique_locations_countries[c].update([c])
                unique_locations_countries_iso[c].update([iso])
        else : 
            for loc in row["location"]:
                unique_locations_countries[loc].update(countries)
                unique_locations_countries_iso[loc].update(isos)

    unique_locations_countries = dict(unique_locations_countries)
    unique_locations_countries_iso = dict(unique_locations_countries_iso)

    end = time.time()
    time_open = (end - start) / 60
    print(f"Numer of unique locations : {len(unique_locations_countries)}")
    print(f"Time to identify all locations {time_open}mins")

    # Run nominatim for each loc 
    start = time.time()
    nom_loc_dict = {}
    for loc in unique_locations_countries : 
        if loc not in nom_loc_dict:
            countries = unique_locations_countries[loc]
            countries_iso = unique_locations_countries_iso[loc]
            nom_loc_dict[loc] = find_best_nomin(loc, countries, countries_iso, similarity_th, print_info=False)
    end = time.time()
    time_open = (end - start) / 60
    print(f"Time to nominatim all locations {time_open}mins")

    # Convert nominatim output to polygons 
    start = time.time()
    max_workers = min(10, (os.cpu_count() or 1) + 2)
    df_geo_individual_locs = run_parallel_geocode(nom_loc_dict, unique_locations_countries, unique_locations_countries_iso, gpd_files, print_info=False, max_workers=max_workers)
    end = time.time()
    time_open = (end - start) / 60
    print(f"Time to geocode all locations {time_open}mins")

    # Gather the polygons to df_row for 2 split options 
    for split_lowest_levels in [True, False] : 
        start = time.time()
        max_workers = min(10, (os.cpu_count() or 1))
        df_geo_output = run_parallel_in_batches(df_geo, df_geo_individual_locs, gpd_files, split_lowest_levels=split_lowest_levels, polygon_source=polygon_source, max_workers=max_workers)
        end = time.time()
        time_open = (end - start) / 60
        print(f"Time to gather locations per rows {time_open}mins")

        # Save the final df
        save_df_geo(df_geo_output, save_path, res_savename, split_lowest_levels)
        if split_lowest_levels : 
            df_geo_output_split = df_geo_output.copy()

    return df_geo_output_split, df_geo_output
