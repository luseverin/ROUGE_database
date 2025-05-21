import pandas as pd
import numpy as np
import ast
import geopy as gpy
import itertools
import time
from src.post_process_functions import *

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