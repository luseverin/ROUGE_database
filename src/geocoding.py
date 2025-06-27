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
from shapely.ops import unary_union
from src.post_process_functions import *
from src.data import *

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
    'admin2': {'admin_level': 2, 'nominatim_keys': ['city', 'town', 'village', 'hamlet', 'municipality', 'locality', 'borough', 'suburb', 'neighbourhood']},
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

def open_admin_gpd(ADMIN_PATH) : 
    gpd_files = {}
    try : 
        ##### ADMIN0 From Natural Earth 
        gpd_files["ADM_0"] = gpd.read_file(ADMIN_PATH+"ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp")
        gpd_files["ADM_0"] = gpd_files["ADM_0"].rename({"ADMIN":"ADMIN_0"}, axis=1)
        
        ##### ADMIN1 From GAUL 
        gpd_files["ADM_1"] = gpd.read_file(ADMIN_PATH+"GAUL_2024_L1/GAUL_2024_L1.shp")
        gpd_files["ADM_1"] = gpd_files["ADM_1"].rename({"gaul0_name":"ADMIN_0", "gaul1_name":"ADMIN_1"}, axis=1)
        
        ##### ADMIN2 From GAUL 
        gpd_files["ADM_2"] = gpd.read_file(ADMIN_PATH+"GAUL_2024_L2/GAUL_2024_L2.shp")        
        gpd_files["ADM_2"] = gpd_files["ADM_2"].rename({"gaul0_name":"ADMIN_0", "gaul1_name":"ADMIN_1", "gaul2_name":"ADMIN_2"}, axis=1)
        
    except Exception as e:
        print(f"[open_admin_gpd] Error loading GPD files: {e}")
        return None
    return gpd_files

def get_polygon(gdf_file, country_name, level_name, target_name, admin_level):
    """
    Get polygon for a target_name at a specific level within a country from the full admin GPKG.
    """
    try:
        choices = gdf_file.loc[gdf_file["ADMIN_0"]==country_name]
        matches = choices[choices[level_name].str.contains(target_name, na=False)]
        if not matches.empty:
            return matches.copy()

    except Exception as e:
        print(f"[get_polygon] Error: {e}")
    
    return None

def query_nominatim(location, country, last_request_time, delay=1):
    """
    Make nominatim query
    """
    if time.time() - last_request_time <= delay:
        time.sleep(delay)
    query = f"{location}, {country}"
    result = geolocator.geocode(query, exactly_one=True, language="en")
    return result, time.time()

def query_reverse_geocode(coords, last_request_time, country, lang="en", delay=1):
    """
    Reverse geocoded object to extract adress informations
    """
    # if time.time() - last_request_time <= delay:
    #     time.sleep(delay)
    # reverse_result = geolocator.reverse(coords, exactly_one=True, addressdetails=True, language="en")
    # if reverse_result is None:
    #     lang = lang_dict.get(country)
    #     reverse_result = geolocator.reverse(coords, exactly_one=True, addressdetails=True, language=lang)
    # return reverse_result.raw.get("address", {}) if reverse_result and isinstance(reverse_result.raw, dict) else {}, time.time()
    if time.time() - last_request_time <= delay:
        time.sleep(delay)
    reverse_result = geolocator.reverse(coords, exactly_one=True, addressdetails=True, language=lang)
    return reverse_result.raw.get("address", {}) if reverse_result and isinstance(reverse_result.raw, dict) else {}, time.time()

def find_best_match(loc_clean, address, similarity_th, print_info):
    """
    Match the best location from reverse geocode result
    """
    best_sim = 0
    best_info = {}

    for loc_level, admin_info in LOCATION_LEVEL_MAPPING.items():
        admin_level = admin_info['admin_level']
        admin_field = f"ADMIN_{admin_level}"
        for key in admin_info['nominatim_keys']:
            if key in address:
                val = address[key]
                val_clean = remove_admin_words(str(val))
                sim = rotated_levenshtein_similarity(loc_clean, val_clean)
                if print_info:
                    print(f"Found geocoding at resolution {admin_level}, Initial: {loc_clean}, Geocoded: {val}, Similarity: {sim:.2f}")
                if sim >= similarity_th and sim > best_sim:
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
            df_gpd["location"] = country
            df_gpd["geocoding_flag"] = 1
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
                conditions = gpd_files[layer_name]["COUNTRY"] == row["COUNTRY"]
                if lowest_level >= 1:
                    conditions &= gpd_files[layer_name]["ADM_1"] == row["ADM_1"]
                if lowest_level == 2:
                    conditions &= gpd_files[layer_name]["ADM_2"] == row["ADM_2"]
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
                continue
    
            # Evaluate similarity
            loc_clean = remove_admin_words(location)
            result_clean = remove_admin_words(nominatim_result.raw.get('name', ''))
            similarity = rotated_levenshtein_similarity(loc_clean, result_clean)

            if similarity < similarity_th:
                if print_info:
                    print(f"Low similarity: {similarity:.2f} for location {location}")
                continue
    
            # Reverse geocoding to get administrative levels
            coords = (nominatim_result.latitude, nominatim_result.longitude)
            address, time_last_request = query_reverse_geocode(coords, time_last_request, curr_country, LANGUAGES)

            match_info, sim = find_best_match(loc_clean, address, similarity_th, print_info)
            if sim > best_sim:
                best_sim = sim
                best_result = {
                    **match_info,
                    "coords": coords,
                    "country": curr_country
                }

        # If a satisfactory location is found
        if best_result : 
            # Try to extract the polygon with English 
            df_gpd = get_polygon(gdf_file[f"ADM_{best_level}"], best_result["country"], best_result["admin_field"], best_result["name"], best_result["admin_level"])
            
            #If not found, loop over the languages 
            if df_gpd is None : 
                language = LANGUAGES.get(best_country)
                address, _ = query_reverse_geocode(best_result['coords'], time_last_request, best_result["country"], language)
                fallback_name = address.get(best_result['key'])
                df_gpd = get_polygon(
                    gdf_file[f"ADM_{best_result['admin_level']}"],
                    best_result["country"],
                    best_result["admin_field"],
                    fallback_name,
                    best_result["admin_level"]
                )
        
            if df_gpd is not None:
                if print_info:
                    print(f"Best match: {best_result['name']} (sim={best_result['sim']:.2f}) at level {best_result['admin_level']}")
                df_gpd["finest_level"] = best_result["admin_level"]
                df_gpd["location"] = best_result["name"]
                df_gpd["geocoding_flag"] = 0
            return df_gpd
            
    except Exception as e : 
        if print_info:
            print(f"[geocode_unique_loc] {e}. Falling back to country level.")
            
    # Fallback to country level
    try : 
        return fallback_country_union(gdf_file, countries)
            
    except Exception as e : 
        print(f"[geocode_unique_loc fallback] Error: {e}")
        return None

def geocode_df_to_polygon(df, gather_admin_level=False, similarity_th=0.2, print_info=False, DATA_OUT_LLMS=None, res_savename=None) : 
    """
    For each row, perform the geocoding and create a polygon corresponding the location found 
    If the gather_admin_level is True, the polygons are downgraded to the lowest resolution found 
    """
    df_geo = deepcopy(df)

    #Convet to list columns related to locations & countries
    for col in ["location", "country", "country_kw"]: 
        df_geo[col] = df_geo[col].apply(lambda x: ast.literal_eval(x) 
                                                      if pd.notna(x) and isinstance(x, str) and x.startswith("[") 
                                                      else ([x] if pd.notna(x) else x))
        
    #Open Polygons 
    start = time.time()
    gpd_files = open_admin_gpd(ADMIN_PATH)
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
            geocoding_flag = None
            locations = row_data['location']
            country = row["country"] or row["country_kw"]

            if not countries:
                continue

            geocoding_flag = None
            df_locations = []
            
            for location in locations : 
                df_loc = geocode_unique_loc(gpd_files, location, country, similarity_th, time_last_request, print_info)
                time_last_request = time.time()
                if df_loc is not None : 
                    if geocoding_flag is not None : 
                        df_loc["geocoding_flag"] = geocoding_flag
                    df_locations.append(df_loc)   
            if not df_locations : 
                continue
                
            df_locations = pd.concat(df_locations, axis=0)
            df_locations = df_locations[df_locations['geometry'].notnull()]
            if df_locations.empty:
                continue

            #Retrieve the lowest admin level
            lowest_level = df_locations["finest_level"].min()
            layer_name = f"ADM_{lowest_level}"
    
            if gather_admin_level:
                merged_geometry = gather_to_lowest_admin(df_locations, gpd_files, lowest_level)
            else:
                merged_geometry = unary_union(df_locations["geometry"])
    
            #Update the final database
            df_geo.loc[row_index, "locationPolygon"] = merged_geometry
            df_geo.loc[row_index, "locationLowestAdmin"] = layer_name
            downgrade_flag = 1 if (df_locations["geocoding_flag"] == 1).any() else 0
            df_geo.loc[row_index, "geocoding_flag"] = downgrade_flag
            
            # Save 
            if DATA_OUT_LLMS and res_savename:
                save_df = df_geo.copy()
                save_df["location"] = save_df["location"].apply(lambda x: str(x) if isinstance(x, list) else x)
                save_gdf = gpd.GeoDataFrame(save_df, geometry='locationPolygon')
                try:
                    suffix = "_geo_gather" if gather_admin_level else "_geo"
                    save_gdf.to_file(f"{DATA_OUT_LLMS}{res_savename}{suffix}.gpkg",
                                     layer="multipolygons", driver="GPKG")
                except Exception as e:
                    print(f"[GeoPackage Save Error] {e}")
                    
        except Exception as e : 
            print(f"[Row {row_index}] Error: {e}")
            continue
    df_geo["location"] = df_geo["location"].apply(lambda x: str(x) if isinstance(x, list) else x)
    return df_geo

######### OLD FUNCTIONS #########
def geocoding_reports_location(df, print_info=False, locations_levels=['country', 'region', 'state', 'city']) :
    """
    Use this function if the input df has only the columns ['location'] to describe the location
    Finer location can be added such as :
    - village
    - suburb
    - road
    """
    df = df.replace({np.nan: None})
    columns_input = list(filter(lambda x: (x != "country")&(x != "location"), df.columns.tolist()))
    df_geo = pd.DataFrame(columns=columns_input+['latitude', 'longitude']+locations_levels)
    for index, row in df.iterrows():
        country = row["country"]
        if row.location:
            finest_loc_id = "location"
            finest_loc_vals = row.location
        else:
            finest_loc_id = "country"
            finest_loc_vals = row.country

        if finest_loc_id:
            time_last_request = time.time()
            if finest_loc_id != "country" :
                nominatim_query=finest_loc_vals+", "+country
            else :
                nominatim_query=country

            time_new_request = time.time()
            if time_new_request - time_last_request <= 1:
                time.sleep(1)#time_new_request - time_last_request)
            nominatim_result = geolocator.geocode(nominatim_query, exactly_one=True, language="en")
            time_last_request = time_new_request

            #If no result for a query with region or city -> Try again a query with country only
            if (nominatim_result is None) and (finest_loc_id != "country"):
                if print_info :
                    print("No results for query: ", nominatim_query, "Try country only")
                #Change to try with country
                finest_loc_id = "country"
                finest_loc_vals = row.country

                nominatim_query = country
                time_new_request = time.time()
                if time_new_request - time_last_request <= 1:
                    time.sleep(1)#time_new_request - time_last_request)
                nominatim_result = geolocator.geocode(nominatim_query, exactly_one=True, language="en")
                time_last_request = time_new_request

            #Test if the query gives a results
            if nominatim_result is None :
                if print_info :
                    print("No results for query: ", nominatim_query)
            else:
                ## Double check that the known information is similar to the one found
                finest_loc_vals_cleaned = remove_admin_words(finest_loc_vals)
                nominatim_result_cleaned = remove_admin_words(nominatim_result.raw['name'])
                similarity = rotated_levenshtein_similarity(finest_loc_vals_cleaned, nominatim_result_cleaned)

                if similarity > 0.4 :
                    if print_info :
                        print("CORRECT location "+nominatim_result.raw['name']+" for "+finest_loc_vals+", similarity = "+str(similarity))
                    row["latitude"] = nominatim_result.latitude
                    row["longitude"] = nominatim_result.longitude
                    row[finest_loc_id] = nominatim_result.raw['name']

                    #Reverse geocoding to correct the spelling
                    time_new_request = time.time()
                    if time_new_request - time_last_request <= 1:
                        time.sleep(1)#time_new_request - time_last_request)
                    location_details = geolocator.reverse((nominatim_result.latitude, nominatim_result.longitude), exactly_one=True, addressdetails=True, language="en")
                    time_last_request = time_new_request
                    address = location_details.raw.get("address", {})

                    for loc_level in locations_levels :
                        if loc_level in address.keys() :
                            row[loc_level] = address.get(loc_level)
                        else :
                            row[loc_level] = None

                    #Add the row to the DataFrame with geocoding
                    df_geo = pd.concat([df_geo, row.to_frame().T], ignore_index=True)
                else :
                    if print_info :
                        print("WRONG location "+nominatim_result.raw['name']+" for "+finest_loc_vals+", similarity = "+str(similarity))
    return df_geo

def geocoding_reports_region_cities(df, print_info=False, locations_levels=['country', 'region', 'state', 'city']) :
    """
    Finer location can be added such as :
    - village
    - suburb
    - road
    """
    df = df.replace({np.nan: None})
    new_columns = [col for col in locations_levels if col not in df.columns]
    df_geo = pd.DataFrame(columns=df.columns.tolist()+['latitude', 'longitude']+new_columns)
    for index, row in df.iterrows():
        country = row["country"]
        if row.city:
            finest_loc_id = "city"
            finest_loc_vals = row.city
        elif row.region:
            finest_loc_id = "region"
            finest_loc_vals = row.region
        else:
            finest_loc_id = "country"
            finest_loc_vals = row.country
        if finest_loc_id:
            time_last_request = time.time()
            if finest_loc_id != "country" :
                nominatim_query=finest_loc_vals+", "+country
            else :
                nominatim_query=country

            time_new_request = time.time()
            if time_new_request - time_last_request <= 1.2:
                time.sleep(1)#time_new_request - time_last_request)
            nominatim_result = geolocator.geocode(nominatim_query, exactly_one=True, language="en")
            time_last_request = time_new_request

            #If no result for a query with region or city -> Try again a query with country only
            if (nominatim_result is None) and (finest_loc_id != "country"):
                if print_info :
                    print("No results for query: ", nominatim_query, "Try country only")
                #Change to try with country
                finest_loc_id = "country"
                finest_loc_vals = row.country

                nominatim_query = country

                time_new_request = time.time()
                if time_new_request - time_last_request <= 1.2:
                    time.sleep(1)#time_new_request - time_last_request)
                nominatim_result = geolocator.geocode(nominatim_query, exactly_one=True, language="en")
                time_last_request = time_new_request

            #Test if the query gives a results
            if nominatim_result is None :
                if print_info :
                    print("No results for query: ", nominatim_query)
            else:
                ## Double check that the known information is similar to the one found
                # similarity = Levenshtein.normalized_similarity(finest_loc_vals, nominatim_result.raw['name'])
                finest_loc_vals_cleaned = remove_admin_words(finest_loc_vals)
                nominatim_result_cleaned = remove_admin_words(nominatim_result.raw['name'])
                similarity = rotated_levenshtein_similarity(finest_loc_vals_cleaned, nominatim_result_cleaned)

                if similarity > 0.4 :
                    if print_info :
                        print("CORRECT location "+nominatim_result.raw['name']+" for "+finest_loc_vals+", similarity = "+str(similarity))
                    row["latitude"] = nominatim_result.latitude
                    row["longitude"] = nominatim_result.longitude
                    row[finest_loc_id] = nominatim_result.raw['name']

                    #Reverse geocoding to correct the spelling
                    time_new_request = time.time()
                    if time_new_request - time_last_request <= 1.2:
                        time.sleep(1)#time_new_request - time_last_request)
                    location_details = geolocator.reverse((nominatim_result.latitude, nominatim_result.longitude), exactly_one=True, addressdetails=True, language="en")
                    time_last_request = time_new_request

                    address = location_details.raw.get("address", {})
                    for loc_level in locations_levels :
                        if loc_level in address.keys() :
                            row[loc_level] = address.get(loc_level)
                        else :
                            row[loc_level] = None

                    #Add the row to the DataFrame with geocoding
                    df_geo = pd.concat([df_geo, row.to_frame().T], ignore_index=True)
                else :
                    if print_info :
                        print("WRONG location "+nominatim_result.raw['name']+" for "+finest_loc_vals+", similarity = "+str(similarity))
    return df_geo

# Geocoding of impact
# For impact we cannot separate the locations to have only one location per row --> Need to keep as a list
# The list of locations will be further divided into a list of cities/state/regions as well as a list of lat/lon for each impact

def geocode_single_location(location, locations_levels=['country', 'region', 'state', 'city'], time_last_request=time.time(), print_info=False, similarity_th=0.4) :
    # Geocode the given location
    time_new_request = time.time()
    if time_new_request - time_last_request <= 1:
        time.sleep(1)#time_new_request - time_last_request)
    nominatim_result = geolocator.geocode(location, exactly_one=True, language="en")
    time_last_request = time_new_request

    if nominatim_result is None :
        if print_info :
            print("No results for query: ", location)
        return None, time_last_request
    else:
        ## Double check that the known information is similar to the one found
        finest_loc_vals_cleaned = remove_admin_words(location)
        nominatim_result_cleaned = remove_admin_words(nominatim_result.raw['name'])
        similarity = rotated_levenshtein_similarity(finest_loc_vals_cleaned, nominatim_result_cleaned)

        if similarity > similarity_th :
            location_dict = {}
            if print_info :
                print("CORRECT location "+nominatim_result.raw['name']+" for "+finest_loc_vals+", similarity = "+str(similarity))
            location_dict["latitude"] = nominatim_result.latitude
            location_dict["longitude"] = nominatim_result.longitude

            #Reverse geocoding to correct the spelling
            time_new_request = time.time()
            if time_new_request - time_last_request <= 1:
                time.sleep(1)#time_new_request - time_last_request)
            location_details = geolocator.reverse((nominatim_result.latitude, nominatim_result.longitude), exactly_one=True, addressdetails=True, language="en")
            time_last_request = time_new_request
            address = location_details.raw.get("address", {})

            for loc_level in locations_levels :
                if loc_level in address.keys() :
                    location_dict[loc_level] = address.get(loc_level)
                else :
                    location_dict[loc_level] = None
            return location_dict, time_last_request
        else :
            if print_info :
                print("WRONG location "+nominatim_result.raw['name']+" for "+finest_loc_vals+", similarity = "+str(similarity))
            return None, time_last_request

def geocoding_impact_location(df, print_info=False, locations_levels=['country', 'region', 'state', 'city']) :
    """
    Use this function if the input df has only the columns ['location'] to describe the location
    Finer location can be added such as :
    - village
    - suburb
    - road
    """
    time_last_request=time.time()
    df = df.replace({np.nan: None})
    columns_input = list(filter(lambda x: (x != "country")&(x != "location"), df.columns.tolist()))
    df_geo = pd.DataFrame(columns=columns_input+['latitude', 'longitude']+locations_levels)
    for index, row in df.iterrows():
        country = row["country"]
        #Check if precise location informations are available
        if row.location:
            for col in locations_levels+['latitude', 'longitude'] :
                row[col] = []
            for loc in row.location :
                location_dict, time_last_request = geocode_single_location(loc, locations_levels, time_last_request, print_info=False, similarity_th=0.4)
                if location_dict :
                    for col in locations_levels+['latitude', 'longitude'] :
                        row[col].append(location_dict[col])
            #Kepp only the set of unique occurence
            for col in locations_levels+['latitude', 'longitude'] :
                row[col] = list(set(row[col])) if row[col] else None
            df_geo = pd.concat([df_geo, row.to_frame().T], ignore_index=True)
        #Otherwise work with country level
        else:
            location_dict, time_last_request = geocode_single_location(row.country, locations_levels, time_last_request, print_info=False, similarity_th=0.4)
            if location_dict :
                for col in locations_levels+['latitude', 'longitude'] :
                    row[col] = location_dict[col]
            df_geo = pd.concat([df_geo, row.to_frame().T], ignore_index=True)
    return df_geo

def make_nominatim_query(irow, response_row, geolocator):
    '''Function to extract geoloactions from text using nominatim'''
    country = response_row["country"]
    regions = separate_locs(response_row["region"])
    states = separate_locs(response_row["state"])
    cities = separate_locs(response_row["city"])
    row_rest = response_row.drop(["country","region", "city"])
    regions = remove_startspace(regions)
    states = remove_startspace(states)
    cities =remove_startspace(cities)
    df_list = []
    i = 1
    if cities:
        finest_loc_id = "city"
        finest_loc_vals = cities
    elif states:
        finest_loc_id = "state"
        finest_loc_vals = states
    elif regions:
        finest_loc_id = "region"
        finest_loc_vals = regions
    else:
        finest_loc_id = None
    print("No location information for response: ", response_row.appealCode)

    if finest_loc_id:
        time_last_request = time.time()
        for ctry, loc in itertools.product([country], finest_loc_vals):#zip([country]*len(regions), regions, states, cities):
            nominatim_query = {
                "country": ctry,
                finest_loc_id: loc
            }

            time_new_request = time.time()
            if time_new_request - time_last_request < 2:
                time.sleep(time_new_request - time_last_request)
            nominatim_result = geolocator.geocode(nominatim_query)
            time_last_request = time_new_request
            if nominatim_result is None:
                print("No results for query: ", nominatim_query)
                continue
            else:
                nominatim_query["latitude"] = nominatim_result.latitude
                nominatim_query["longitude"] = nominatim_result.longitude
                nominatim_query.update(row_rest.to_dict())
                new_row = pd.DataFrame(nominatim_query, index=pd.MultiIndex.from_tuples([(response_row.appealCode, irow+i+1)], names=['appealCode', 'index']))
                df_list.append(new_row)
            i+=1

    return df_list