import pandas as pd
import numpy as np
import ast
import geopy as gpy
import itertools
import time
import math
import pycountry
import langcodes
from copy import deepcopy
from rapidfuzz import fuzz
import geopandas as gpd
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from src.post_process_functions import *
from src.data import *
import os
import tempfile
import shutil

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

geolocator = gpy.geocoders.Nominatim(user_agent='orienternet')
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
            gpd_files["ADM_0"] = geoBoundaries0

            ### ADMIN 1 
            geoBoundaries1 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM1.gpkg")
            geoBoundaries1 = geoBoundaries1.rename({"shapeName" : "ADMIN_1", "shapeGroup" : "iso3_code"}, axis=1)
            geoBoundaries1 = pd.merge(geoBoundaries1, geoBoundaries0[["iso3_code", "ADMIN_0"]], on="iso3_code", how="left").drop_duplicates()
            gpd_files["ADM_1"] = geoBoundaries1

            ### ADMIN 2 
            geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2.gpkg")
            gpd_files["ADM_2"] = geoBoundaries2

        except Exception as e:
            print(f"[open_admin_gpd][geoBoundaries] Error loading GPD files: {e}")
            return None
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

def query_nominatim(location, country, last_request_time, delay=1):
    """
    Make nominatim query
    """
    if time.time() - last_request_time <= delay:
        time.sleep(delay)

    if not location :
        query = f"{country}"
    else :
        query = f"{location}, {country}"
    result = geolocator.geocode(query, exactly_one=True, language="en", addressdetails =True, geometry="geojson")
    return result, time.time()

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
                    if sim >= similarity_th and sim > best_sim and admin_level>=best_info["admin_level"]:
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
            if sim >= similarity_th and sim > best_sim and admin_level>=best_info["admin_level"]:
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
    return unary_union(geometries)

# Main geocoding functions
def geocode_unique_loc(gdf_file, location, country, similarity_th, time_last_request, print_info=True):
    #Make sure countries are in list format
    countries = [country] if isinstance(country, str) else country
    try :
        best_result = None
        best_sim = 0

        for curr_country in countries :
            nom_result, time_last_request = query_nominatim(location, curr_country, time_last_request)

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

def geocode_df_to_polygon(df, similarity_th=0.2, split_lowest_levels=True, print_info=False, save_path=False, res_savename=False, polygon_source="GAUL") :
    """
    For each row, perform the geocoding and create a polygon corresponding the location found
    If the gather_admin_level is True, the polygons are downgraded to the lowest resolution found
    """
    df_geo = deepcopy(df)
    if polygon_source == "GAUL" : 
        extra_columns_output = ["gaul0_code", "gaul1_code", "gaul2_code", 
                                "locationPolygon", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon"]
    else : 
        extra_columns_output = ["locationPolygon", "locationLowestAdmin", 
                                "geocoding_country_flag", "geocoding_osm_flag", 
                                "locationOsm", "locationPolygon"]

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
    if print_info :
        print(f"Time to open files {time_open}mins")

    time_last_request = time.time()

    #Convert each row to polygon
    if gpd_files is None :
        return None

    start = time.time()
    for row_index, row_data in df_geo.iterrows():
        try : 
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
            for merge_level in range(lowest_level, highest_level+1) :
                layer_name = f"ADM_{merge_level}"
                df_location_subset = df_locations.loc[df_locations.finest_level>=merge_level]
                merged_geometry = gather_to_lowest_admin(df_location_subset, gpd_files, merge_level)
                
                df_row_append = df_geo.loc[row_index].copy()
                df_row_append.loc["locationPolygon"] = merged_geometry
                df_row_append.loc["locationLowestAdmin"] = layer_name
                df_row_append.loc["geocoding_country_flag"] = count_geocoding_country_flag
                df_row_append.loc["geocoding_osm_flag"] = count_geocoding_osm_flag
                df_row_append.loc["locationOsm"] = df_location_subset["locationOsm"].unique().tolist()
                df_row_append.loc["locationPolygon"] = df_location_subset["locationPolygon"].unique().tolist()

                # For the codes, take the list 
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
        
        except Exception as e : 
            print(f"[Row {row_index}] Error: {e}")
            continue

    # Save 
    if save_path and res_savename:
        save_df = df_geo_output.copy()
        save_df = delistify_cols(save_df)
        save_gdf = gpd.GeoDataFrame(save_df, geometry='locationPolygon')
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
