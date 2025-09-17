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
from concurrent.futures import ProcessPoolExecutor
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from src.post_process_functions import *
from src.data import *
import os
import tempfile
import shutil
from urllib.parse import quote
import requests
from collections import defaultdict

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

def get_polygon(gdf_file, country_name, level_name, target_name, admin_level):
    """
    Get polygon for a target_name at a specific level within a country from the full admin GPKG.
    """
    try:
        choices = gdf_file.loc[gdf_file["ADMIN_0"]==country_name]
        matches = choices[choices[level_name].str.contains(target_name, na=False)]

        #Try for new matches, removing the admin words 
        if matches.empty : 
            target_name_modified = remove_admin_words(target_name)
            matches = choices[choices[level_name].str.contains(target_name_modified, na=False)]
        if not matches.empty:
            return matches.copy()

    except Exception as e:
        print(f"level_name : {level_name}, target_name : {target_name}")
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
    assert level in [1, 2], "level must be '1' or '2'"

    adm0_gdf = gpd_files["ADM_0"]
    adm1_gdf = gpd_files["ADM_1"]
    adm2_gdf = gpd_files["ADM_2"]

    # Filter country in ADM_0
    adm0_country = adm0_gdf[adm0_gdf["ADMIN_0"] == country_name]
    if adm0_country.empty:
        return None  # country not found

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

# def query_nominatim(location, country, delay=2):
#     """
#     Make nominatim query
#     """
#     # if time.time() - last_request_time <= delay:
#     #     time.sleep(delay)

#     if not location :
#         query = f"{country}"
#     else :
#         query = f"{location}, {country}"

#     # First try to geocode with nominatim
#     try :
#         result = geolocator.geocode(query, exactly_one=True, language="en", addressdetails =True, geometry="geojson")
#         return result
    
#     except Exception as e :
#         time.sleep(delay)
#         #2nd try to geocode with nominatim
#         try : 
#             result = geolocator.geocode(query, exactly_one=True, language="en", addressdetails =True, geometry="geojson")
#             return result
#         except Exception as e : 
#             # time.sleep(delay)
#             # try : 
#             #     result = geolocator.geocode(query, exactly_one=True, language="en", addressdetails =True, geometry="geojson")
#             #     return result
#             # # If error raised again, return a flag to track which row were not geocoded 
#             # except Exception as e : 
#             #     return "Failed"
#             print("[query_nominatim] Exception found : ", e)
#             return None

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

# def query_nominatim(location, country, max_retries=3, timeout=30):
#     """
#     Direct HTTP request to Nominatim API with better error handling
#     """
#     base_url = "https://nominatim.openstreetmap.org/search"
    
#     if not location:
#         query = f"{country}"
#     else:
#         query = f"{location}, {country}"
    
#     params = {
#         'q': query,
#         'format': 'json',
#         'limit': 1,
#         'addressdetails': 1,
#         'accept-language': 'en',
#         'polygon_geojson': 1
#     }
    
#     headers = {
#         'User-Agent': 'IFRC/1.0 (laura.hasbini@lsce.ipsl.fr)',
#         'Accept': 'application/json'
#     }
    
#     for attempt in range(max_retries):
#         try:
#             response = requests.get(
#                 base_url, 
#                 params=params, 
#                 headers=headers, 
#                 timeout=timeout
#             )
            
#             if response.status_code == 200:
#                 data = response.json()
#                 if data:
#                     return data[0]  # Return first result
#                 return None
            
#             elif response.status_code == 429:  # Too Many Requests
#                 retry_after = int(response.headers.get('Retry-After', 5))
#                 print(f"Rate limited. Retrying after {retry_after} seconds...")
#                 time.sleep(retry_after)
#                 continue
                
#             else:
#                 print(f"HTTP Error {response.status_code}: {response.text}")
#                 return None
                
#         except requests.exceptions.Timeout:
#             if attempt == max_retries - 1:
#                 print("All retries failed due to timeout")
#                 return None
#             sleep_time = 2 * (attempt + 1)
#             print(f"Timeout on attempt {attempt + 1}. Retrying in {sleep_time}s...")
#             time.sleep(sleep_time)
            
#         except requests.exceptions.ConnectionError:
#             if attempt == max_retries - 1:
#                 print("Connection error after all retries")
#                 return None
#             sleep_time = 3 * (attempt + 1)
#             print(f"Connection error. Retrying in {sleep_time}s...")
#             time.sleep(sleep_time)
            
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return None
    
#     return None

def query_reverse_geocode(coords, last_request_time, country, lang="en", delay=1):
    """
    Reverse geocoded object to extract adress informations
    """
    if time.time() - last_request_time <= delay:
        time.sleep(delay)
    reverse_result = geolocator.reverse(coords, exactly_one=True, addressdetails=True, language=lang, zoom=13)
    return reverse_result.raw.get("address", {}) if reverse_result and isinstance(reverse_result.raw, dict) else {}, time.time()

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

def fallback_country_union(gdf_file, countries):
    """
    Fallback: Combine polygons of all possible countries
    """
    country_polygons = []
    for country in countries:
        df_gpd = get_polygon(gdf_file["ADM_0"], country, "ADMIN_0", country, 0)
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

def gather_to_lowest_admin(df_locations, gpd_files, lowest_level):
    """
    Downgrades all polygons to the lowest admin level available
    """
    geometries = []
    layer_name = f"ADM_{lowest_level}"

    for _, row in df_locations.iterrows():
        try:
            if row["finest_level"] == lowest_level:
                geometries.append(row["geometry"])
            else:
                conditions = gpd_files[layer_name]["ADMIN_0"] == row["ADMIN_0"]
                if lowest_level >= 1:
                    conditions &= gpd_files[layer_name]["ADMIN_1"] == row["ADMIN_1"]
                if lowest_level == 2:
                    conditions &= gpd_files[layer_name]["ADMIN_2"] == row["ADMIN_2"]
                matches = gpd_files[layer_name][conditions]
                geometries.extend(matches["geometry"])
        except Exception as e:
            print(f"[gather admin fallback] Error: {e}")
        # print(geometries)
    # print(geometries)
    return unary_union(geometries)

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

def find_best_nomin(gdf_file, location, countries, similarity_th, print_info=False) : 
    best_result = None
    best_sim = 0

    for curr_country in countries :
        nom_result = query_nominatim(location, curr_country)

        if nom_result is None:
            if print_info:
                print(f"No results for query: {location}, {curr_country}")
            return fallback_country_union(gdf_file, countries)
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
            # best_nomin = nom_result
    return nom_result, best_result

def geocode_from_nominatim_output(gdf_file, location, best_nomin, best_result, countries, print_info=False) :
    #Make sure countries are in list format
    try :
        # If a satisfactory matching is found, and it doesn't correspond to an ADMIN 3 level, look for a GADM polygon
        if best_result : #and (best_result["admin_level"]!=3) :
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
                df_gpd["location"] = location
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
                    df_gpd["location"] = location
                    return df_gpd
        else : 
            df_gpd =  fallback_country_union(gdf_file, countries)
            df_gpd["location"] = location
            return df_gpd
        
        #If no polygon found, loop for higher levels 
            
    except Exception as e :
        # if print_info:
        print(f"[geocode_unique_loc] {e}. Falling back to country level.")

def run_parallel_geocode(nom_loc_dict, unique_locations_countries, gdf_file, print_info=False, max_workers=None):
    results = []
    
    # run in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                geocode_from_nominatim_output,
                gdf_file,
                location,
                best_nomin,
                best_result,
                unique_locations_countries[location],
                print_info
            ): location
            for location, (best_nomin, best_result) in nom_loc_dict.items()
        }

        for future in futures:
            location = futures[future]
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
    df_locations = df_geo_individual_locs.loc[df_geo_individual_locs["location"].isin(row["location"])]
    df_geo_output = pd.DataFrame()

    #Retrieve the lowest admin level
    lowest_level = df_locations["finest_level"].min()
    highest_level = df_locations["finest_level"].max()
    
    if split_lowest_levels : 
        highest_level = df_locations["finest_level"].max()
    else : 
        highest_level = lowest_level

    #Merge all the locs to the lewest admin levels
    for merge_level in range(lowest_level, highest_level+1) :
        layer_name = f"ADM_{merge_level}"
        df_location_subset = df_locations.loc[df_locations["finest_level"]>=merge_level]
        merged_geometry = gather_to_lowest_admin(df_location_subset, gdf_file, merge_level)

        df_row_append = pd.DataFrame([row])
        df_row_append["geometry"] = merged_geometry
        df_row_append["locationLowestAdmin"] = layer_name
        df_row_append["geocoding_country_flag"] = df_location_subset['geocoding_country_flag'].sum()#count_geocoding_country_flag
        df_row_append["geocoding_osm_flag"] = df_location_subset['geocoding_osm_flag'].sum()#count_geocoding_osm_flag
        # print(df_location_subset["locationOsm"].unique().tolist())
        # print("df_row_append", df_row_append)
        df_row_append["locationOsm"] = [df_location_subset["locationOsm"].unique().tolist()]
        df_row_append["locationPolygon"] = [df_location_subset["locationPolygon"].unique().tolist()]
        print("df_row_append", df_row_append)

        # For the codes, take the list 
        df_row_append["iso3_code"] = df_location_subset["iso3_code"].unique().tolist()
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
        print(df_row_append)
        df_geo_output = pd.concat([df_geo_output, df_row_append], ignore_index=True)
    return df_geo_output 

def run_parallel_associate(df_geo, df_geo_individual_locs, gdf_file, split_lowest_levels=True, polygon_source="GAUL", max_workers=None):
    results = []

    # convert rows to dictionaries to pass to subprocesses
    rows = df_geo.to_dict("records")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
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

def geocode_df_to_polygon_by_unique_loc(df, similarity_th=0.2, split_lowest_levels=True, print_info=False, save_path=False, res_savename=False, polygon_source="GAUL") :
    # Prepare dataset 
    df_geo = deepcopy(df)

    # if polygon_source == "GAUL" : 
    #     extra_columns_output = ["gaul0_code", "gaul1_code", "gaul2_code", 
    #                             "geometry", "locationLowestAdmin", 
    #                             "geocoding_country_flag", "geocoding_osm_flag", 
    #                             "locationOsm", "locationPolygon", "iso3_code"]
    # else : 
    #     extra_columns_output = ["geometry", "locationLowestAdmin", 
    #                             "geocoding_country_flag", "geocoding_osm_flag", 
    #                             "locationOsm", "locationPolygon", "iso3_code"]

    # df_geo_output = pd.DataFrame(columns = list(df.columns)+extra_columns_output)

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
    unique_locations_countries = defaultdict(set)

    for _, row in df_geo.iterrows():
        countries = row["country"]
        # ensure it's iterable (list), even if single country
        if not isinstance(countries, (list, set, tuple)):
            countries = [countries]
        
        for loc in row["location"]:
            unique_locations_countries[loc].update(countries)
    unique_locations_countries = dict(unique_locations_countries)

    # Run nominatim for each loc 
    nom_loc_dict = {}
    for loc in unique_locations_countries : 
        countries = unique_locations_countries[loc]
        nom_loc_dict[loc] = find_best_nomin(gpd_files, loc, countries, similarity_th, print_info=False)
    
    print("nom_loc_dict", nom_loc_dict)

    # Convert nominatim output to polygons 
    df_geo_individual_locs = run_parallel_geocode(nom_loc_dict, unique_locations_countries, gpd_files, print_info=False, max_workers=4)
    print("All locations geocoded")

    # Gather the polygons to df_row 
    df_geo_output = run_parallel_associate(df_geo, df_geo_individual_locs, gpd_files, split_lowest_levels=split_lowest_levels, polygon_source=polygon_source, max_workers=4)

    # Save the final df

    return df_geo_output



#### Test for parrallelization 

def geocode_df_to_polygon_v1_parrallele(df, similarity_th=0.2, split_lowest_levels=True, print_info=False, save_path=False, res_savename=False, polygon_source="GAUL", max_workers=None):
    """
    For each row, perform the geocoding and create a polygon corresponding the location found
    If the gather_admin_level is True, the polygons are downgraded to the lowest resolution found
    """
    df_geo = deepcopy(df)
    if polygon_source == "GAUL": 
        extra_columns_output = ["gaul0_code", "gaul1_code", "gaul2_code", 
                                "geometry", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon", "iso3_code"]
    else: 
        extra_columns_output = ["geometry", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon", "iso3_code"]

    df_geo_output = pd.DataFrame(columns=list(df.columns) + extra_columns_output)

    # Convert to list columns related to locations & countries
    if "country_kw" in df_geo.columns: 
        col_to_list = ["location", "country", "country_kw"]
        df_type = "llm"
    else: 
        col_to_list = ["location", "country"]
        df_type = "labelled"

    for col in col_to_list: 
        df_geo[col] = df_geo[col].apply(
            lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.strip().startswith("[") else ([x] if pd.notna(x) else None)
        )

    # Open Polygons
    start = time.time()
    gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)
    end = time.time()
    time_open = (end - start) / 60
    if print_info:
        print(f"Time to open files {time_open}mins")

    if gpd_files is None:
        return None

    # Function to process a single row
    def process_row(row_data, row_index, gpd_files, similarity_th, df_type, split_lowest_levels, polygon_source):
        try:
            locations = row_data['location']
            country = row_data["country"]
            if not country and df_type == "llm": 
                country = row_data["country_kw"]

            # If no country is found, don't look for any polygon 
            if not country:
                df_row_append = row_data.copy()
                return [df_row_append]

            # If no location, change to have it as a list
            if not locations: 
                locations = [None]
            
            df_locations = []
            count_geocoding_osm_flag = 0 
            count_geocoding_country_flag = 0 
            
            for location in locations:
                df_loc = geocode_unique_loc(gpd_files, location, country, similarity_th, time.time(), print_info)
                if df_loc is not None: 
                    if (df_loc["geocoding_osm_flag"] == 1).any(): 
                        count_geocoding_osm_flag += 1
                    if (df_loc["geocoding_country_flag"] == 1).any(): 
                        count_geocoding_country_flag += 1
                    df_locations.append(df_loc)   
            
            if not df_locations: 
                return []

            df_locations = pd.concat(df_locations, axis=0)
            df_locations = df_locations[df_locations['geometry'].notnull()]

            if df_locations.empty:
                return []
                
            # Retrieve the lowest admin level
            lowest_level = df_locations["finest_level"].min()
            highest_level = df_locations["finest_level"].max()
            
            if split_lowest_levels: 
                highest_level = df_locations["finest_level"].max()
            else: 
                highest_level = lowest_level

            # Process each merge level
            results = []
            for merge_level in range(lowest_level, highest_level + 1):
                layer_name = f"ADM_{merge_level}"
                df_location_subset = df_locations.loc[df_locations.finest_level >= merge_level]
                merged_geometry = gather_to_lowest_admin(df_location_subset, gpd_files, merge_level)

                df_row_append = row_data.copy()
                df_row_append.loc["geometry"] = merged_geometry
                df_row_append.loc["locationLowestAdmin"] = layer_name
                df_row_append.loc["geocoding_country_flag"] = count_geocoding_country_flag
                df_row_append.loc["geocoding_osm_flag"] = count_geocoding_osm_flag
                df_row_append.loc["locationOsm"] = df_location_subset["locationOsm"].unique().tolist()
                df_row_append.loc["locationPolygon"] = df_location_subset["locationPolygon"].unique().tolist()
                df_row_append.loc["iso3_code"] = df_location_subset["iso3_code"].unique().tolist()
                
                if polygon_source == "GAUL": 
                    for code in ["gaul0_code", "gaul1_code", "gaul2_code"]: 
                        df_row_append.loc[code] = df_location_subset[code].unique().tolist()
                
                # Remove the impact value if it's not the lowest admin level
                if merge_level != lowest_level: 
                    df_row_append.loc["impactValue"] = np.nan
                    df_row_append.loc["impactUnit"] = np.nan
                    df_row_append.loc["impactValueApprox"] = np.nan
                
                results.append(df_row_append)
            
            return results
            
        except Exception as e: 
            print(f"[Row {row_index}] Error: {e}")
            return []

    # Process rows in parallel
    start = time.time()
    
    # Create partial function with fixed arguments
    process_row_partial = partial(
        process_row, 
        gpd_files=gpd_files, 
        similarity_th=similarity_th, 
        df_type=df_type, 
        split_lowest_levels=split_lowest_levels, 
        polygon_source=polygon_source
    )
    
    # Use ThreadPoolExecutor for I/O-bound tasks (geocoding)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_row_partial, row_data, row_index): row_index 
            for row_index, row_data in df_geo.iterrows()
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_index):
            row_index = future_to_index[future]
            try:
                row_results = future.result()
                for result in row_results:
                    # Align columns to df_geo_output
                    result_df = pd.DataFrame([result])
                    common_cols = df_geo_output.columns.intersection(result_df.columns)
                    result_df = result_df[common_cols]
                    df_geo_output = pd.concat([df_geo_output, result_df], ignore_index=True)
            except Exception as e:
                print(f"[Row {row_index}] Error in processing: {e}")
    
    end = time.time()
    time_open = (end - start) / 60
    if print_info:
        print(f"Time to process all rows {time_open}mins")

    # Save 
    if save_path and res_savename:
        save_df = df_geo_output.copy()
        save_df = delistify_cols(save_df)
        save_gdf = gpd.GeoDataFrame(save_df, geometry='geometry')
        save_gdf = save_gdf.set_crs("EPSG:4326", allow_override=True)
        try:
            suffix = "_geo_split_lowest" if split_lowest_levels else "_geo"
            # Save gpkg
            gpkg_path = f"{save_path}{res_savename}{suffix}.gpkg"
            if not atomic_gpkg_save(save_gdf, gpkg_path):
                raise Exception(f"[GeoPackage Save Error] Failed to save GeoPackage to {gpkg_path}")
        except Exception as e:
            print(f"[GeoPackage Save Error] {e}")
    
    return df_geo_output

def _process_single_row(row_data, row_index, gpd_files, similarity_th, df_type, 
                       split_lowest_levels, polygon_source, print_info=False):
    """Process a single row for geocoding (extracted for parallel processing)"""
    try:
        locations = row_data['location']
        country = row_data["country"]
        if not country and df_type == "llm": 
            country = row_data["country_kw"]

        # If no country is found, don't look for any polygon 
        if not country:
            df_row_append = row_data.copy()
            return [df_row_append]

        # If no location, change to have it as a list
        if not locations: 
            locations = [None]
        
        df_locations = []
        count_geocoding_osm_flag = 0 
        count_geocoding_country_flag = 0 
        
        for location in locations:
            df_loc = geocode_unique_loc(gpd_files, location, country, similarity_th, time.time(), print_info)
            if df_loc is not None: 
                if (df_loc["geocoding_osm_flag"] == 1).any(): 
                    count_geocoding_osm_flag += 1
                if (df_loc["geocoding_country_flag"] == 1).any(): 
                    count_geocoding_country_flag += 1
                df_locations.append(df_loc)   
        
        if not df_locations: 
            return []

        df_locations = pd.concat(df_locations, axis=0)
        df_locations = df_locations[df_locations['geometry'].notnull()]

        if df_locations.empty:
            return []
            
        # Retrieve the lowest admin level
        lowest_level = df_locations["finest_level"].min()
        highest_level = df_locations["finest_level"].max()
        
        if split_lowest_levels: 
            highest_level = df_locations["finest_level"].max()
        else: 
            highest_level = lowest_level

        # Process each merge level
        results = []
        for merge_level in range(lowest_level, highest_level + 1):
            layer_name = f"ADM_{merge_level}"
            df_location_subset = df_locations.loc[df_locations.finest_level >= merge_level]
            merged_geometry = gather_to_lowest_admin(df_location_subset, gpd_files, merge_level)

            df_row_append = row_data.copy()
            df_row_append.loc["geometry"] = merged_geometry
            df_row_append.loc["locationLowestAdmin"] = layer_name
            df_row_append.loc["geocoding_country_flag"] = count_geocoding_country_flag
            df_row_append.loc["geocoding_osm_flag"] = count_geocoding_osm_flag
            df_row_append.loc["locationOsm"] = df_location_subset["locationOsm"].unique().tolist()
            df_row_append.loc["locationPolygon"] = df_location_subset["locationPolygon"].unique().tolist()
            df_row_append.loc["iso3_code"] = df_location_subset["iso3_code"].unique().tolist()
            
            if polygon_source == "GAUL": 
                for code in ["gaul0_code", "gaul1_code", "gaul2_code"]: 
                    df_row_append.loc[code] = df_location_subset[code].unique().tolist()
            
            # Remove the impact value if it's not the lowest admin level
            if merge_level != lowest_level: 
                df_row_append.loc["impactValue"] = np.nan
                df_row_append.loc["impactUnit"] = np.nan
                df_row_append.loc["impactValueApprox"] = np.nan
            
            results.append(df_row_append)
        
        return results
        
    except Exception as e: 
        print(f"[Row {row_index}] Error: {e}")
        return []

def geocode_df_to_polygon_v2_parrallel(df, similarity_th=0.2, split_lowest_levels=True, 
                             print_info=False, save_path=False, res_savename=False, 
                             polygon_source="GAUL", max_workers=None):
    """Main function with parallel processing"""
    df_geo = deepcopy(df)
    if polygon_source == "GAUL": 
        extra_columns_output = ["gaul0_code", "gaul1_code", "gaul2_code", 
                                "geometry", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon", "iso3_code"]
    else: 
        extra_columns_output = ["geometry", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon", "iso3_code"]

    df_geo_output = pd.DataFrame(columns=list(df.columns) + extra_columns_output)

    # Convert to list columns related to locations & countries
    if "country_kw" in df_geo.columns: 
        col_to_list = ["location", "country", "country_kw"]
        df_type = "llm"
    else: 
        col_to_list = ["location", "country"]
        df_type = "labelled"

    for col in col_to_list: 
        df_geo[col] = df_geo[col].apply(
            lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.strip().startswith("[") else ([x] if pd.notna(x) else None)
        )

    # Open Polygons
    start = time.time()
    gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)
    end = time.time()
    time_open = (end - start) / 60
    if print_info:
        print(f"Time to open files {time_open}mins")

    if gpd_files is None:
        return None
    
    # Process rows in parallel
    start = time.time()
    
    # Prepare arguments for each row
    tasks = []
    for row_index, row_data in df_geo.iterrows():
        tasks.append((
            row_data, row_index, gpd_files, similarity_th, 
            df_type, split_lowest_levels, polygon_source, print_info
        ))
    
    # Use ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(_process_single_row, *task_args): task_args[1]  # row_index is second argument
            for task_args in tasks
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_index):
            row_index = future_to_index[future]
            try:
                row_results = future.result()
                for result in row_results:
                    result_df = pd.DataFrame([result])
                    common_cols = df_geo_output.columns.intersection(result_df.columns)
                    result_df = result_df[common_cols]
                    df_geo_output = pd.concat([df_geo_output, result_df], ignore_index=True)
            except Exception as e:
                print(f"[Row {row_index}] Error in processing: {e}")
    
    end = time.time()
    time_open = (end - start) / 60
    if print_info:
        print(f"Time to process all rows {time_open}mins")

    # Save 
    if save_path and res_savename:
        save_df = df_geo_output.copy()
        save_df = delistify_cols(save_df)
        save_gdf = gpd.GeoDataFrame(save_df, geometry='geometry')
        save_gdf = save_gdf.set_crs("EPSG:4326", allow_override=True)
        try:
            suffix = "_geo_split_lowest" if split_lowest_levels else "_geo"
            # Save gpkg
            gpkg_path = f"{save_path}{res_savename}{suffix}.gpkg"
            if not atomic_gpkg_save(save_gdf, gpkg_path):
                raise Exception(f"[GeoPackage Save Error] Failed to save GeoPackage to {gpkg_path}")
        except Exception as e:
            print(f"[GeoPackage Save Error] {e}")
    return df_geo_output

#### GARBAGE 
def _process_row_shared_crap(args, df_type, similarity_th, split_lowest_levels, polygon_source, print_info):
    """
    Worker for multiprocessing: process one row.
    """
    global worker_gpd_files
    row_index, row_data = args
    # print("Run row")

    pid = mp.current_process().pid
    print(f"Process {pid} processing row {row_index}")
    print(f"Worker gpd_files is None: {worker_gpd_files is None}")

    try:
        if worker_gpd_files is None:
            print(f"Worker {mp.current_process().pid}: gpd_files is None!")
            return None
        
        locations = row_data['location']
        country = row_data["country"]
        if not country and df_type == "llm":
            country = row_data["country_kw"]

        if not country:
            return pd.DataFrame([row_data])

        if not locations:
            locations = [None]

        df_locations = []
        count_geocoding_osm_flag = 0
        count_geocoding_country_flag = 0

        for location in locations:
            df_loc = geocode_unique_loc(
                worker_gpd_files, location, country, similarity_th, time.time(), print_info
            )
            if df_loc is not None:
                if (df_loc["geocoding_osm_flag"] == 1).any():
                    count_geocoding_osm_flag += 1
                if (df_loc["geocoding_country_flag"] == 1).any():
                    count_geocoding_country_flag += 1
                df_locations.append(df_loc)

        if not df_locations:
            return None

        df_locations = pd.concat(df_locations, axis=0)
        df_locations = df_locations[df_locations['geometry'].notnull()]
        if df_locations.empty:
            return None

        lowest_level = df_locations["finest_level"].min()
        highest_level = df_locations["finest_level"].max()
        if not split_lowest_levels:
            highest_level = lowest_level

        outputs = []
        for merge_level in range(lowest_level, highest_level + 1):
            layer_name = f"ADM_{merge_level}"
            df_location_subset = df_locations.loc[df_locations.finest_level >= merge_level]
            merged_geometry = gather_to_lowest_admin(df_location_subset, gpd_files, merge_level)

            df_row_append = row_data.copy()
            df_row_append.loc["geometry"] = merged_geometry
            df_row_append.loc["locationLowestAdmin"] = layer_name
            df_row_append.loc["geocoding_country_flag"] = count_geocoding_country_flag
            df_row_append.loc["geocoding_osm_flag"] = count_geocoding_osm_flag
            df_row_append.loc["locationOsm"] = df_location_subset["locationOsm"].unique().tolist()
            df_row_append.loc["locationPolygon"] = df_location_subset["locationPolygon"].unique().tolist()
            df_row_append.loc["iso3_code"] = df_location_subset["iso3_code"].unique().tolist()

            if polygon_source == "GAUL":
                for code in ["gaul0_code", "gaul1_code", "gaul2_code"]:
                    df_row_append.loc[code] = df_location_subset[code].unique().tolist()

            if merge_level != lowest_level:
                for col in ["impactValue", "impactUnit", "impactValueApprox"]:
                    if col in df_row_append:
                        df_row_append.loc[col] = np.nan

            outputs.append(pd.DataFrame([df_row_append]))
            # print(outputs)
        return pd.concat(outputs, ignore_index=True)

    except Exception as e:
        print(f"[Row {row_index}] Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def geocode_df_to_polygon_crap(df, similarity_th=0.2, split_lowest_levels=True,
                          print_info=False, save_path=False, res_savename=False,
                          polygon_source="GAUL", n_jobs=None):
    """
    Parallelised geocoding with multiprocessing.
    """
    df_geo = deepcopy(df)

    if polygon_source == "GAUL":
        extra_columns_output = ["gaul0_code", "gaul1_code", "gaul2_code",
                                "geometry", "locationLowestAdmin",
                                "geocoding_country_flag", "geocoding_osm_flag",
                                "locationOsm", "locationPolygon"]
    else:
        extra_columns_output = ["geometry", "locationLowestAdmin",
                                "geocoding_country_flag", "geocoding_osm_flag",
                                "locationOsm", "locationPolygon"]

    df_geo_output = pd.DataFrame(columns=list(df.columns) + extra_columns_output)

    # Convert list-like cols
    if "country_kw" in df_geo.columns:
        col_to_list = ["location", "country", "country_kw"]
        df_type = "llm"
    else:
        col_to_list = ["location", "country"]
        df_type = "labelled"

    for col in col_to_list:
        df_geo[col] = df_geo[col].apply(
            lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.strip().startswith("[") else ([x] if pd.notna(x) else None)
        )

    # # Load polygons
    # start = time.time()
    # # gpd_files = open_admin_gpd(ADMIN_PATH, polygon_source)
    # init_worker(ADMIN_PATH, polygon_source)
    # end = time.time()
    # # if print_info:
    # print(f"Time to open files {(end - start)/60:.2f} mins")

    # if gpd_files is None:
    #     return None

    print("Testing init_worker standalone...")
    init_worker(ADMIN_PATH, polygon_source)
    print("init_worker test completed")
    
    worker_func = partial(_process_row_shared_crap, 
                         df_type=df_type,
                         similarity_th=similarity_th,
                         split_lowest_levels=split_lowest_levels,
                         polygon_source=polygon_source,
                         print_info=print_info)

    # # Prepare args for workers
    # args_list = [
    #     (idx, row, gpd_files, df_type, similarity_th, split_lowest_levels, polygon_source, print_info)
    #     for idx, row in df_geo.iterrows()
    # ]
    args_list = [(idx, row) for idx, row in df_geo.iterrows()]

    # Default: use all CPUs
    start = time.time()
    if n_jobs is None:
        n_jobs = mp.cpu_count()
    end = time.time()
    time_open = (end-start)/60
    print(f"Time to count nb of CPU {time_open}mins")

    print("Number of CPU : ", n_jobs)

    # Run pool
    print("Run parallelisation")
    start = time.time()
    chunksize = max(1, len(df_geo) // (n_jobs * 4))
    # with mp.Pool(processes=n_jobs) as pool:
    #     # results = list(pool.imap_unordered(_process_row_shared, args_list, chunksize=100))
    #     results = list(pool.imap_unordered(worker_func, args_list, chunksize=chunksize))
    with mp.Pool(processes=n_jobs, initializer=init_worker, initargs=(ADMIN_PATH, polygon_source)) as pool:
        print(f"Pool created with {n_jobs} processes")
        print(f"Processing {len(args_list)} rows")

        results = list(pool.imap_unordered(worker_func, args_list, chunksize=chunksize))
    end = time.time()
    time_open = (end-start)/60
    print(f"Time to run all // {time_open}mins")
    
    print(f"Number of results found {len(results)}")
    print("Result 0 : ", results[0])
    results = [r for r in results if r is not None]
    if results:
        df_geo_output = pd.concat(results, ignore_index=True)

    # Save output
    print("Try to save")
    print("Save_path : ", save_path)
    print("res_savename : ", res_savename)
    if save_path and res_savename:
        save_df = df_geo_output.copy()
        save_df = delistify_cols(save_df)
        save_gdf = gpd.GeoDataFrame(save_df, geometry='geometry')
        save_gdf = save_gdf.set_crs("EPSG:4326", allow_override=True)
        try:
            suffix = "_geo_split_lowest" if split_lowest_levels else "_geo"
            gpkg_path = f"{save_path}{res_savename}{suffix}.gpkg"
            if not atomic_gpkg_save(save_gdf, gpkg_path):
                raise Exception(f"[GeoPackage Save Error] Failed to save GeoPackage to {gpkg_path}")
        except Exception as e:
            print(f"[GeoPackage Save Error] {e}")

    return df_geo_output