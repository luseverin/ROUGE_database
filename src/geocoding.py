import pandas as pd
import numpy as np
import ast
import geopy as gpy
import itertools
import time

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