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
from src.data_format import delistify_cols, listify_strings, format_output
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
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderRateLimited
from joblib import dump

# set up logger
LOGGER = logging.getLogger("postprocessing")

# Countries
import pycountry
import re

# Add Geolocation and spatial information (region from cities)
from geopy.extra.rate_limiter import RateLimiter
from rapidfuzz.distance import Levenshtein
from src.client import NOMINATIM_USER_AGENT
from src.geocoding_utils import *
from filelock import FileLock

# --- Create shared SQLite cache for back nominatim ---
CACHE_DB = "reverse_geocode_cache.db"
_conn = sqlite3.connect(CACHE_DB, check_same_thread=False)
_cur = _conn.cursor()

_cur.execute(
    """
CREATE TABLE IF NOT EXISTS reverse_cache (
    lat REAL,
    lon REAL,
    lang TEXT,
    zoom INTEGER,
    result TEXT,
    PRIMARY KEY (lat, lon, lang, zoom)
)
"""
)
_conn.commit()

# Lock guarantees safe concurrent writes
# _cache_lock = threading.Lock()
# _cache_lock = FileLock("reverse_geocode_cache.lock")
_cache_lock = FileLock(f"{CACHE_DB}.lock")

# Create geoolocator
geolocator = gpy.geocoders.Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=10)

# Global geolocator
geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1,
    max_retries=3,
    error_wait_seconds=2,
    swallow_exceptions=False,
)

# Rate limited reverse geocoder
reverse_geocode = RateLimiter(
    geolocator.reverse,
    min_delay_seconds=1,
    max_retries=3,
    error_wait_seconds=2,
    swallow_exceptions=False,
)


#### Preprocessing of the location
def normalize_to_list(x):
    if x is None:
        return []
    if isinstance(x, float) and pd.isna(x):
        return []
    if isinstance(x, str):
        x = x.strip()
        if x.lower() in {"none", "nan", ""}:
            return []
        return [x]
    if isinstance(x, (list, tuple, set)):
        out = []
        for v in x:
            if v is None:
                continue
            if isinstance(v, float) and pd.isna(v):
                continue
            if isinstance(v, str) and v.strip().lower() in {"none", "nan", ""}:
                continue
            out.append(v)
        return out
    return [x]


def identify_robust_country(df_geo, ctr_col1, ctr_col2, output_col):
    df = df_geo.copy()

    # Normalize all columns
    countries_col1 = df[ctr_col1].map(normalize_to_list)
    countries_col2 = (
        df[ctr_col2].map(normalize_to_list) if ctr_col2 in df.columns else []
    )

    # Union (vectorized using zip)
    df[output_col] = [
        sorted(set(a) | set(b)) if (a or b) else None
        for a, b in zip(countries_col1, countries_col2)
    ]

    # Drop old columns
    df = df.drop(columns=[ctr_col1, ctr_col2], errors="ignore")

    return df


def identify_unique_location_country(df_geo):
    rows = {}  # key -> (location, country, iso3, iso2) — deduplicates automatically

    for _, row in df_geo.iterrows():
        countries = row["country_robust"] or []
        iso3s = row["country_robust_iso3"] or []
        iso2s = row["country_robust_iso2"] or []

        triplets = list(itertools.zip_longest(countries, iso3s, iso2s, fillvalue=None))
        locations = row["location"] or []

        if not locations:
            for c, iso3, iso2 in triplets:
                # key = (c, c, iso3, iso2)
                key = (c, iso3, iso2)
                # rows[key] = True
                rows[key] = c
        else:
            for loc in locations:
                for c, iso3, iso2 in triplets:
                    key = (loc, iso3, iso2)
                    if key not in rows:
                        rows[key] = c
                        # rows[key] = True

    df_unique = pd.DataFrame(
        [(loc, country, iso3, iso2) for (loc, iso3, iso2), country in rows.items()],
        columns=["location", "country", "country_iso3", "country_iso2"],
    )

    # Correct country names using pycountry (prefer iso3, fallback to iso2)
    def normalize_country(row):
        country = (
            pycountry.countries.get(alpha_3=row["country_iso3"])
            if row["country_iso3"]
            else None
        )
        if country is None and row["country_iso2"]:
            country = pycountry.countries.get(alpha_2=row["country_iso2"])
        return country.name if country else row["country"]

    df_unique["country"] = df_unique.apply(normalize_country, axis=1)

    # Ensure no missing locations: replace missing/empty with country name
    df_unique["location"] = df_unique["location"].where(
        df_unique["location"].notna() & (df_unique["location"] != ""), df_unique["country"]
    )

    return df_unique


def identify_unique_locations_v2(df_geo):
    """
    Each unique location is associated to a unique country list
    Do not gather potential subsets.
    For example you could have :
    ["Paris"] -> ["France", "Italy"]
    ["Paris"] -> ["Italy"]
    ["Paris"] -> ["France"]
    """
    rows = {}  # frozenset(countries) as key to deduplicate identical sets

    for _, row in df_geo.iterrows():
        countries = row["country_robust"] or []
        iso3s = row["country_robust_iso3"] or []
        iso2s = row["country_robust_iso2"] or []

        triplets = list(itertools.zip_longest(countries, iso3s, iso2s, fillvalue=None))
        locations = row["location"]

        loc_list = [c for c, _, _ in triplets] if not locations else None

        def add_entry(loc, triplets):
            key = (loc, frozenset(c for c, _, _ in triplets))
            if key not in rows:
                rows[key] = {
                    "location": loc,
                    "country": [c for c, _, _ in triplets],
                    "country_iso3": [iso3 for _, iso3, _ in triplets],
                    "country_iso2": [iso2 for _, _, iso2 in triplets],
                }

        if not locations:
            for c, iso3, iso2 in triplets:
                add_entry(c, [(c, iso3, iso2)])
        else:
            for loc in locations:
                add_entry(loc, triplets)

    return pd.DataFrame(list(rows.values()))


# Version 3: Subset merging — if (loc, [c1, c2]) exists, don't add (loc, [c1]) or (loc, [c2])
def identify_unique_locations_v3(df_geo):
    """
    Each unique location is associated to a unique country list
    Gather list which are subset of some other
    For example you could have :
    ["Paris"] -> ["France", "Italy"]
    ["Paris"] -> ["Italy"] will be gather to the above one
    ["Paris"] -> ["France"] will be gather to the above one
    """
    # loc -> list of frozensets of countries (with their iso3/iso2 mappings)
    loc_sets = defaultdict(list)  # loc -> [frozenset(countries), ...]
    loc_data = {}  # (loc, frozenset) -> {country, iso3, iso2 lists}

    for _, row in df_geo.iterrows():
        countries = row["country_robust"] or []
        iso3s = row["country_robust_iso3"] or []
        iso2s = row["country_robust_iso2"] or []

        triplets = list(itertools.zip_longest(countries, iso3s, iso2s, fillvalue=None))
        locations = row["location"]

        def add_entry(loc, triplets):
            fset = frozenset(c for c, _, _ in triplets)

            # Check if this set is already a subset of an existing set for this loc
            for existing_fset in loc_sets[loc]:
                if fset <= existing_fset:
                    # Already covered by a larger or equal set → skip
                    return

            # Check if any existing sets are subsets of this new (larger) set
            # If so, remove them as they are now covered by this new entry
            loc_sets[loc] = [
                existing_fset
                for existing_fset in loc_sets[loc]
                if not existing_fset < fset  # remove strict subsets
            ]
            for obsolete_fset in [
                ef for ef in list(loc_data.keys()) if ef[0] == loc and ef[1] < fset
            ]:
                del loc_data[obsolete_fset]

            # Add the new entry
            loc_sets[loc].append(fset)
            loc_data[(loc, fset)] = {
                "location": loc,
                "country": [c for c, _, _ in triplets],
                "country_iso3": [iso3 for _, iso3, _ in triplets],
                "country_iso2": [iso2 for _, _, iso2 in triplets],
            }

        if not locations:
            for c, iso3, iso2 in triplets:
                add_entry(c, [(c, iso3, iso2)])
        else:
            for loc in locations:
                add_entry(loc, triplets)

    return pd.DataFrame(list(loc_data.values()))


#### Function to Geocode one location
def match_admin1_for_row(row, gpd_files):
    """Given a row of df_geo and gpd_files, find the ADM1 boundary that contains/intersects the geometry."""
    geom = row["geometry"]
    adm0 = row["ADMIN_0"]

    adm1_match = get_polygon_for_geometry(geom, adm0, gpd_files, level=1)
    if adm1_match is not None and "ADMIN_1" in adm1_match:
        return adm1_match["ADMIN_1"].values[0]
    return None


def open_admin_gpd(ADMIN_PATH, polygon_source="GAUL"):
    """Load administrative boundary GeoDataFrames (ADM_0, ADM_1, ADM_2) from either GAUL or geoBoundaries sources and return them as a dictionary."""
    gpd_files = {}
    if polygon_source == "GAUL":
        try:
            ##### ADMIN2 From GAUL
            # gaul2 = gpd.read_file(ADMIN_PATH+"GAUL_2024_L2/GAUL_2024_L2.shp")
            gaul2 = gpd.read_file(
                os.path.join(ADMIN_PATH, "GAUL_2024_L2", "GAUL_2024_L2.shp")
            )
            gaul2 = gaul2.rename(
                {
                    "gaul0_name": "ADMIN_0",
                    "gaul1_name": "ADMIN_1",
                    "gaul2_name": "ADMIN_2",
                },
                axis=1,
            )
            gpd_files["ADM_2"] = gaul2

            ##### ADMIN1 From GAUL
            # gaul1 = gpd.read_file(ADMIN_PATH+"GAUL_2024_L1/GAUL_2024_L1.shp")
            gaul1 = gpd.read_file(
                os.path.join(ADMIN_PATH, "GAUL_2024_L1", "GAUL_2024_L1.shp")
            )
            gaul1 = gaul1.rename(
                {"gaul0_name": "ADMIN_0", "gaul1_name": "ADMIN_1"}, axis=1
            )
            gaul1["gaul2_code"] = None
            gpd_files["ADM_1"] = gaul1

            ##### ADMIN0 From Natural Earth
            # ne_0 = gpd.read_file(ADMIN_PATH+"ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")
            ne_0 = gpd.read_file(
                os.path.join(
                    ADMIN_PATH,
                    "ne_50m_admin_0_countries",
                    "ne_50m_admin_0_countries.shp",
                )
            )
            
            #Add the countries which are missing from the 50m resolution
            ne_0_10m = gpd.read_file(
            os.path.join(
                ADMIN_PATH,
                "ne_10m_admin_0_countries",
                "ne_10m_admin_0_countries.shp",
                )
            )  
            missing_iso3 = set(ne_0_10m["ISO_A3"]) - set(ne_0["ISO_A3"]) 
            missing_countries = ne_0_10m[ne_0_10m["ISO_A3"].isin(missing_iso3)]
            ne_0 = pd.concat([ne_0, missing_countries],ignore_index=True)

            #Clean the file structure and merge with GAUL
            ne_0 = ne_0.rename({"ADMIN": "ADMIN_0", "ISO_A3": "iso3_code"}, axis=1)
            ne_0["gaul1_code"] = None
            ne_0["gaul2_code"] = None
            ne_0 = pd.merge(
                ne_0, gaul1[["iso3_code", "gaul0_code"]], on="iso3_code", how="left"
            ).drop_duplicates()
            ne_0 = ne_0[["iso3_code", "gaul0_code", "ADMIN_0", "geometry"]]
            gpd_files["ADM_0"] = ne_0

        except Exception as e:
            LOGGER.error("[open_admin_gpd][GAUL] Error loading GPD files: %s", e)
            return None
    elif polygon_source == "geoBoundaries":
        try:
            ### ADMIN 0
            # geoBoundaries0 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM0.gpkg")
            geoBoundaries0 = gpd.read_file(
                os.path.join(ADMIN_PATH, "geoBoundaries", "geoBoundariesCGAZ_ADM0.gpkg")
            )
            geoBoundaries0 = geoBoundaries0.rename(
                {"shapeName": "ADMIN_0", "shapeGroup": "iso3_code"}, axis=1
            )
            geoBoundaries0 = geoBoundaries0.loc[geoBoundaries0["shapeType"] == "ADM0"]
            gpd_files["ADM_0"] = geoBoundaries0

            ### ADMIN 1
            # geoBoundaries1 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM1.gpkg")
            geoBoundaries1 = gpd.read_file(
                os.path.join(ADMIN_PATH, "geoBoundaries", "geoBoundariesCGAZ_ADM1.gpkg")
            )
            geoBoundaries1 = geoBoundaries1.rename(
                {"shapeName": "ADMIN_1", "shapeGroup": "iso3_code"}, axis=1
            )
            geoBoundaries1 = geoBoundaries1.loc[geoBoundaries1["shapeType"] == "ADM1"]
            geoBoundaries1 = pd.merge(
                geoBoundaries1,
                geoBoundaries0[["iso3_code", "ADMIN_0"]],
                on="iso3_code",
                how="left",
            ).drop_duplicates()
            gpd_files["ADM_1"] = geoBoundaries1

            ### ADMIN 2
            # geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2.gpkg")
            # geoBoundaries2 = gpd.read_file(ADMIN_PATH+"geoBoundaries/geoBoundariesCGAZ_ADM2_corrected.gpkg")
            geoBoundaries2 = gpd.read_file(
                os.path.join(
                    ADMIN_PATH, "geoBoundaries", "geoBoundariesCGAZ_ADM2_corrected.gpkg"
                )
            )
            geoBoundaries2 = geoBoundaries2.rename(
                {"shapeName": "ADMIN_2", "shapeGroup": "iso3_code"}, axis=1
            )
            geoBoundaries2 = geoBoundaries2.loc[geoBoundaries2["shapeType"] == "ADM2"]
            gpd_files["ADM_2"] = geoBoundaries2

            if not "ADMIN_0" in gpd_files["ADM_2"].columns:
                gpd_files["ADM_2"] = pd.merge(
                    gpd_files["ADM_2"],
                    geoBoundaries0[["iso3_code", "ADMIN_0"]],
                    on="iso3_code",
                    how="left",
                ).drop_duplicates()

            if not "ADMIN_1" in gpd_files["ADM_2"].columns:
                pandarallel.initialize(nb_workers=8)
                func = partial(match_admin1_for_row, gpd_files=gpd_files)
                gpd_files["ADM_2"]["ADMIN_1"] = gpd_files["ADM_2"].parallel_apply(
                    func, axis=1
                )

        except Exception as e:
            LOGGER.error(
                "[open_admin_gpd][geoBoundaries] Error loading GPD files: %s", e
            )
            return None

    # Correct potential invalid mask
    for i in range(2):
        invalid_mask = ~gpd_files[f"ADM_{i}"]["geometry"].is_valid
        gpd_files[f"ADM_{i}"].loc[invalid_mask, "geometry"] = (
            gpd_files[f"ADM_{i}"].loc[invalid_mask, "geometry"].buffer(0)
        )

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

    similarities = [
        (c, rotated_levenshtein_similarity(curr_country, c)) for c in country_list
    ]
    best_match, best_score = max(similarities, key=lambda x: x[1])

    if best_score >= threshold:
        return best_match
    else:
        return None


def get_polygon(
    gdf_file,
    country_name,
    country_iso,
    level_name,
    target_name,
    admin_level,
    polygon_similarity_th=0.7,
):
    """Get polygon for a target_name at a specific level within a country_name from the full admin GDF."""
    try:
        # Verify that the country exist otherwise take the country with the highest similarity
        if country_name not in gdf_file["ADMIN_0"].unique():
            # Option 1 : Use the ISO
            if country_iso in gdf_file["iso3_code"].unique():
                choices = gdf_file.loc[gdf_file["iso3_code"] == country_iso]
            # Option 2 : Look for the real name of the country with buffing
            else:
                country_name = find_closest_country(country_name, gdf_file)
                choices = gdf_file.loc[gdf_file["ADMIN_0"] == country_name]
        else:
            choices = gdf_file.loc[gdf_file["ADMIN_0"] == country_name]

        # Direct matching
        if level_name != "ADMIN_0":
            matches = choices[
                choices[level_name].str.contains(target_name, na=False, regex=False)
            ]
        else:
            matches = choices

        # Remove admin words and retry
        if matches.empty:
            target_name_modified = remove_admin_words(target_name)
            matches = choices[
                choices[level_name].str.contains(
                    target_name_modified, na=False, regex=False
                )
            ]

        # Similarity search (threshold ≥ polygon_similarity_th)
        if matches.empty:
            similarities = (
                choices[level_name]
                .dropna()
                .apply(lambda x: rotated_levenshtein_similarity(str(x), target_name))
            )
            # Select rows >= polygon_similarity_th similarity
            similar_idx = similarities[similarities >= polygon_similarity_th].index

            if len(similar_idx) > 0:
                matches = choices.loc[similar_idx]

        # Similarity with the target_name_modified
        if matches.empty:
            similarities = (
                choices[level_name]
                .dropna()
                .apply(
                    lambda x: rotated_levenshtein_similarity(
                        str(x), target_name_modified
                    )
                )
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
    if country_name not in adm0_gdf["ADMIN_0"].unique():
        country_name = find_closest_country(country_name, adm0_gdf)

    adm0_country = adm0_gdf[adm0_gdf["ADMIN_0"] == country_name]
    if adm0_country.empty:
        return None  # country not found

    if level == 0:
        # Reuturn adm0 polygons
        return adm0_country

    # Filter ADM_1 to those inside the country
    adm1_country = adm1_gdf[adm1_gdf["ADMIN_0"] == country_name]

    if level == 1:
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

def fallback_country_union(gdf_file, location, countries, iso_countries):
    """Fallback: Combine polygons of all possible countries"""
    country_polygons = []
    for country, country_iso in zip(countries, iso_countries):
        df_gpd = get_polygon(
            gdf_file["ADM_0"], country, country_iso, "ADMIN_0", country, 0
        )
        if df_gpd is not None:
            df_gpd["finest_level"] = 0
            df_gpd["locationOsm"] = country
            df_gpd["locationPolygon"] = country
            df_gpd["flag_geocoding_osm"] = 0
            # Don't raise flag_geocoding_country if the location if the country
            if location in countries:
                df_gpd["flag_geocoding_country"] = 0
            else:
                df_gpd["flag_geocoding_country"] = 1

            country_polygons.append(df_gpd)

    if country_polygons:
        combined = pd.concat(country_polygons)
        combined["geometry"] = unary_union(combined["geometry"])
        # combined["geometry"] = MultiPolygon(combined["geometry"])
        # combined["geometry"] = GeometryCollection(combined["geometry"].tolist())
        combined = combined.iloc[[0]]
        return combined.assign(location=location)

    # If no columns found
    empty_cols = [
        "finest_level",
        "locationOsm",
        "locationPolygon",
        "flag_geocoding_osm",
        "flag_geocoding_country",
        "geometry",
    ]

    # Create a one-row dataframe with NaN / None
    empty_df = pd.DataFrame({col: [None] for col in empty_cols})
    LOGGER.error(
        "[gather fallback_country_union fallback] Fail to find country's polygons, %s, %s",
        countries,
        iso_countries,
    )
    return empty_df.assign(location=location)

#### Queries nominatim and find best match

def query_nominatim(location, country_iso2, max_retries=2, initial_delay=1):
    """
    Make nominatim query with robust error handling
    From location and country, return a OSM object
    """
    if not location:
        return None

    for attempt in range(max_retries):
        try:
            geocode_kwargs = dict(
                # exactly_one=True,
                exactly_one=False,
                limit=5,
                language="en",
                addressdetails=True,
                geometry="geojson",
                # featuretype=["country", "state", "city", "settlement", "island"],
            )
            if country_iso2:
                geocode_kwargs["country_codes"] = country_iso2

            result = geocode(location, **geocode_kwargs)
            return result

        except (GeocoderTimedOut, GeocoderServiceError, GeocoderRateLimited) as e:
            sleep_time = initial_delay * (2**attempt)
            LOGGER.warning(
                "[query_nominatim] Attempt %i failed: %s. Retrying in %.1f s...",
                attempt + 1,
                e,
                sleep_time,
            )
            time.sleep(sleep_time)

        except Exception as e:
            LOGGER.error("[query_nominatim] Unexpected error: %s", e)
            return None

    LOGGER.error(
        "[query_nominatim] All %i attempts failed for '%s'", max_retries, location
    )
    return None

def query_reverse_geocode(coords, lang="en", zoom=13, max_retries=2, initial_delay=1):
    """
    Reverse geocode a coordinate with SQLite caching.
    Safe for threads and multiple processes.
    Returns a geopy Location object or None.
    """
    lat = round(float(coords[0]), 5)
    lon = round(float(coords[1]), 5)

    for attempt in range(max_retries):
        try:
            with _cache_lock:
                # 1️⃣ Check cache
                row = _cur.execute(
                    """
                    SELECT result FROM reverse_cache
                    WHERE lat=? AND lon=? AND lang=? AND zoom=?
                """,
                    (lat, lon, lang, zoom),
                ).fetchone()

                if row:
                    try:
                        return gpy.location.Location(**json.loads(row[0]))
                    except Exception:
                        pass  # corrupted cache → fallback

            # 2️⃣ Not in cache → query Nominatim
            reverse_result = reverse_geocode(
                (lat, lon),
                exactly_one=True,
                addressdetails=True,
                language=lang,
                zoom=zoom,
            )

            # 3️⃣ Store result in cache
            if reverse_result is not None:
                loc_dict = {
                    "address": reverse_result.raw.get("address"),
                    "latitude": reverse_result.latitude,
                    "longitude": reverse_result.longitude,
                    "raw": reverse_result.raw,
                }
                loc_json = json.dumps(loc_dict)

                with _cache_lock:
                    _cur.execute(
                        """
                        INSERT OR REPLACE INTO reverse_cache
                        (lat, lon, lang, zoom, result)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (lat, lon, lang, zoom, loc_json),
                    )
                    _conn.commit()

            return reverse_result

        except (GeocoderRateLimited, GeocoderTimedOut, GeocoderServiceError) as e:
            # exponential backoff
            sleep_time = initial_delay * (2**attempt)
            print(
                f"[query_reverse_geocode] Attempt {attempt+1} failed: {e}. Retrying in {sleep_time:.1f}s..."
            )
            time.sleep(sleep_time)

        except Exception as e:
            print(f"[query_reverse_geocode] Unexpected error: {e}")
            return None

    return None

def find_best_match(loc_clean, address, similarity_th, print_info=False):
    """
    Match the best location from reverse geocode result
    """
    best_sim = 0
    best_info = {"admin_level": 0}

    for address_key in address.keys():
        found = False
        for _, admin_info in LOCATION_LEVEL_MAPPING.items():
            admin_level = admin_info["admin_level"]
            admin_field = f"ADMIN_{admin_level}"
            for key in admin_info["nominatim_keys"]:
                if key == address_key:
                    val = address[key]
                    val_clean = remove_admin_words(str(val))
                    sim = rotated_levenshtein_similarity(loc_clean, val_clean)

                    if print_info:
                        LOGGER.info(
                            "Found geocoding at resolution %s, Initial: %s, Geocoded: %s, Similarity: %.2f",
                            admin_level,
                            loc_clean,
                            val,
                            sim,
                        )

                    if sim == 1:
                        found = True
                        best_sim = sim
                        best_info = {
                            "sim": sim,
                            "admin_level": admin_level,
                            "admin_field": admin_field,
                            "name": val,
                            "key": key,
                        }
                        return best_info, best_sim

                    if (
                        sim >= similarity_th and sim > best_sim
                    ):  # and admin_level>=best_info["admin_level"]:
                        found = True
                        best_sim = sim
                        best_info = {
                            "sim": sim,
                            "admin_level": admin_level,
                            "admin_field": admin_field,
                            "name": val,
                            "key": key,
                        }
                    break
            if found:
                break
        # If the address key is not found in the location, it mean it's associated with an ADMIN_3
        if not found:
            admin_level = 3
            admin_field = f"ADMIN_{admin_level}"

            val = address[address_key]
            val_clean = remove_admin_words(str(val))
            sim = rotated_levenshtein_similarity(loc_clean, val_clean)
            if print_info:
                LOGGER.info(
                    "Found geocoding at resolution %s, Initial: %s, Geocoded: %s, Similarity: %.2f",
                    admin_level,
                    loc_clean,
                    val,
                    sim,
                )

            # If exact match, return it directly
            if sim == 1:
                best_sim = sim
                best_info = {
                    "sim": sim,
                    "admin_level": admin_level,
                    "admin_field": admin_field,
                    "name": val,
                    "key": key,
                }
                return best_info, best_sim

            elif (
                sim >= similarity_th and sim > best_sim
            ):  # and admin_level>=best_info["admin_level"]:
                best_sim = sim
                best_info = {
                    "sim": sim,
                    "admin_level": admin_level,
                    "admin_field": admin_field,
                    "name": val,
                    "key": key,
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

def save_df_geo(df_geo, save_path, res_savename):
    """Save a GeoDataFrame to a GeoPackage file with standardized CRS and naming."""
    save_df = df_geo.copy()
    save_df = delistify_cols(save_df)
    save_gdf = gpd.GeoDataFrame(save_df, geometry="geometry")
    save_gdf = save_gdf.set_crs("EPSG:4326", allow_override=True)

    if save_path:
        try:
            # Save gpkg
            gpkg_path = os.path.join(save_path, f"{res_savename}.gpkg")
            if not atomic_gpkg_save(save_gdf, gpkg_path):
                raise Exception(
                    f"[GeoPackage Save Error] Failed to save GeoPackage to {gpkg_path}"
                )
        except Exception as e:
            LOGGER.error("[GeoPackage Save Error] %s", e)

#### Optimize geocoding and work per unique location found

##### Functions for nominatim

def find_best_nomin(row, similarity_th, print_info=False):
    """Query Nominatim for a location across candidate countries and
    return the best matching result with similarity evaluation.s

    Args:
        row: A row from the unique locations DataFrame with columns
             'location', 'country', 'country_iso3', 'country_iso2'
    """
    best_result = None
    best_sim = 0

    # Default output
    empty = pd.Series(
        {
            "nom_result": None,
            "coords": None,
            "match_info": None,
            "country": row["country"],
            "country_iso3": row["country_iso3"],
            "country_iso2": row["country_iso2"],
        }
    )

    location = row["location"]
    curr_country = row["country"]
    curr_iso3 = row["country_iso3"]
    curr_iso2 = row["country_iso2"]

    # If extracted location is too long and corresponds to a sentence, return None, None
    if len(location) > 30:
        return empty

    # nom_result = query_nominatim(remove_admin_words(location), curr_iso2)
    nom_results = query_nominatim(remove_admin_words(location), curr_iso2)

    # Try to query only with location
    # if nom_result is None:
    if not nom_results:
        # nom_result = query_nominatim(remove_admin_words(location), None)
        nom_results = query_nominatim(remove_admin_words(location), curr_iso2)

        if nom_results:
            # Filter out results where country doesn't match input
            filtered = []
            for nr in nom_results:
                address = nr.raw.get("address", {})
                nom_iso2 = address.get("country_code", "")
                nom_country = address.get("country", "")
                if (
                    nom_iso2.upper() == curr_iso2.upper()
                    and nom_country == curr_country
                ):
                    filtered.append(nr)
            nom_results = filtered

    # if nom_result is None:
    if not nom_results:
        # return None, None
        return empty

    loc_clean = remove_admin_words(location)
    idx = 0
    while idx < len(nom_results):
        nom_result = nom_results[idx]
        coords = (nom_result.latitude, nom_result.longitude)
        address = (
            nom_result.raw.get("address", {})
            if isinstance(nom_result.raw, dict)
            else {}
        )

        match_info, sim = find_best_match(loc_clean, address, similarity_th, print_info)
        if sim > best_sim:
            best_sim = sim
            best_result = {
                **match_info,
                "coords": coords,
                "country": curr_country,
                "country_iso3": curr_iso3,
                "country_iso2": curr_iso2,
            }
            break  # Found a satisfactory result, stop iterating
        idx += 1

    return pd.Series(
        {
            "nom_result": nom_result,
            "coords": best_result.get("coords") if best_result else None,
            "match_info": best_result,
            "country": best_result.get("country") if best_result else row["country"],
            "country_iso3": (
                best_result.get("country_iso3") if best_result else row["country_iso3"]
            ),
            "country_iso2": (
                best_result.get("country_iso2") if best_result else row["country_iso2"]
            ),
        }
    )

##### Convert individual locations to polygons

def try_fallback_strategies(gdf_file, best_nomin, best_result, adm_lev):
    """Attempt alternative strategies to match an administrative polygon
    when the direct lookup fails (alternative Nominatim keys, language-based fallbacks).
    """
    # Strategy 1: Alternative nominatim keys
    try:
        fallback_address = best_nomin.raw.get("address", {})
        for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"][
            "nominatim_keys"
        ]:
            if nomin_key_admin in fallback_address:
                df_gpd = get_polygon(
                    gdf_file[f"ADM_{adm_lev}"],
                    best_result["country"],
                    best_result["country_iso3"],
                    f"ADMIN_{adm_lev}",
                    fallback_address[nomin_key_admin],
                    adm_lev,
                )
                if df_gpd is not None:
                    return df_gpd

        # Strategy 2: Language fallbacks (with rate limiting)
        language = LANGUAGES.get(
            best_result["country"][0]
            if isinstance(best_result["country"], list)
            else best_result["country"]
        )
        for lang in [language, "fr", "es", "de"]:
            if lang:  # Skip None languages
                coords = (best_nomin.latitude, best_nomin.longitude)
                address = query_reverse_geocode(coords, lang)
                for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"][
                    "nominatim_keys"
                ]:
                    if nomin_key_admin in address:
                        df_gpd = get_polygon(
                            gdf_file[f"ADM_{adm_lev}"],
                            best_result["country"],
                            best_result["country_iso3"],
                            best_result["admin_field"],
                            address[nomin_key_admin],
                            adm_lev,
                        )
                        if df_gpd is not None:
                            return df_gpd
    except Exception as e:
        LOGGER.warning(
            "[try_fallback_strategies] %s. Falling back to country level.", e
        )
        return None


def try_nominatim_key_fallback(gdf_file, best_nomin, best_result, adm_lev):
    """
    Strategy 1 only: try alternative Nominatim keys.
    """
    try:
        fallback_address = best_nomin.raw.get("address", {})
        for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"][
            "nominatim_keys"
        ]:
            if nomin_key_admin in fallback_address:
                df_gpd = get_polygon(
                    gdf_file[f"ADM_{adm_lev}"],
                    best_result["country"],
                    best_result["country_iso3"],
                    f"ADMIN_{adm_lev}",
                    fallback_address[nomin_key_admin],
                    adm_lev,
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
            best_result["country"][0]
            if isinstance(best_result["country"], list)
            else best_result["country"]
        )

        coords = (best_nomin.latitude, best_nomin.longitude)

        for lang in [language, "fr", "es", "de"]:
            if not lang:
                continue

            address = query_reverse_geocode(coords, lang)
            if not address:
                continue

            for nomin_key_admin in LOCATION_LEVEL_MAPPING[f"admin{adm_lev}"][
                "nominatim_keys"
            ]:
                if nomin_key_admin in address:
                    df_gpd = get_polygon(
                        gdf_file[f"ADM_{adm_lev}"],
                        best_result["country"],
                        best_result["country_iso3"],
                        best_result["admin_field"],
                        address[nomin_key_admin],
                        adm_lev,
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
        geom = Point(best_nomin.longitude, best_nomin.latitude)
        # coords = best_nomin.raw['geojson']['coordinates']
        # geom_type = best_nomin.raw['geojson']['type'].strip().lower()

        # if geom_type == 'point':
        #     geom = Point(coords[0], coords[1])
        # elif geom_type == 'polygon':
        #     geom = Polygon(coords[0])
        # elif geom_type == 'multipolygon':
        #     geom = MultiPolygon([Polygon(p[0]) for p in coords])
        # else:
        #     return None

        df_gpd = get_polygon_for_geometry(
            geom, best_result["country"], gdf_file, level=best_result["admin_level"]
        )

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
        location=location,
    )


# def geocode_from_nominatim_output_optimized(gdf_file, location, best_nomin, best_result, countries, iso_countries, print_info=False):
def geocode_from_nominatim_output_optimized(row, gdf_file, print_info=False):
    """Match a Nominatim geocoding result to the best administrative boundary polygon,
    using fallbacks when necessary, and return the corresponding GeoDataFrame row."""
    try:
        location = row["location"]
        best_nomin = row["nom_result"]
        best_result = row["match_info"]
        countries = (
            row["country"] if isinstance(row["country"], list) else [row["country"]]
        )
        iso_countries = (
            row["country_iso3"]
            if isinstance(row["country_iso3"], list)
            else [row["country_iso3"]]
        )
        # print(f"[geocode] Processing location={location} country={countries} iso3={iso_countries}, best result={best_result}")

        if not best_result:
            step = "fallback_country_union"
            return fallback_country_union(
                gdf_file, location, countries, iso_countries
            )  # .assign(location=location)

        adm_lev = int(best_result["admin_level"])
        # print(adm_lev)
        while adm_lev > 0:
            df_gpd = None
            osm_flag = 0

            # print("Run get_polygon")
            if adm_lev <= 2:
                step = "get_polygon"
                df_gpd = get_polygon(
                    gdf_file[f"ADM_{adm_lev}"],
                    best_result["country"],
                    best_result["country_iso3"],
                    best_result["admin_field"],
                    best_result["name"],
                    adm_lev,
                )
            else:
                # force admin level to 2 if higher than 2
                adm_lev = 2
                best_result["admin_field"] = "ADMIN_2"
                best_result["admin_level"] = 2
                df_gpd = None

            # print("Try fallback stategies")
            # If not found → try fallback strategies
            if df_gpd is None:
                step = "try_fallback_strategies"
                df_gpd = try_fallback_strategies(
                    gdf_file, best_nomin, best_result, adm_lev
                )
                # df_gpd = try_nominatim_key_fallback(gdf_file, best_nomin, best_result, adm_lev)

            # print("Try geojson fallback")
            # If still not found → try geojson fallback
            if df_gpd is None:
                step = "try_geojson_fallback"
                df_gpd = try_geojson_fallback(
                    gdf_file, best_nomin, best_result, location
                )
                osm_flag = 1

            # Check that the geometry found is at the correct country
            # print(f"Force iso3 to {iso_countries}. Found {df_gpd}")
            if df_gpd is not None:
                df_gpd = df_gpd[df_gpd["iso3_code"].isin(iso_countries)]

            # If something was found → prepare and return
            # if df_gpd is not None:
            if df_gpd is not None and not df_gpd.empty:
                step = "prepare_result_df"
                return prepare_result_df(
                    df_gpd, best_result, location, osm_flag=osm_flag
                )

            # If we got here, nothing was found → decrease admin level
            adm_lev -= 1
            best_result["admin_field"] = f"ADMIN_{adm_lev}"

        # If loop finishes without returning anything
        return fallback_country_union(
            gdf_file, location, countries, iso_countries
        )  # .assign(location=location)

    except Exception as e:
        # print(step)
        LOGGER.warning(
            "[geocode_from_nomin_output_optimized] %s. Falling back to country level.",
            e,
        )
        return fallback_country_union(
            gdf_file, location, countries, iso_countries
        )  # .assign(location=location)


def geocode_nomin_geom(row, gdf_file, print_info=False):
    try:
        location = row["location"]
        best_nomin = row["nom_result"]
        best_result = row["match_info"]
        countries = (
            row["country"] if isinstance(row["country"], list) else [row["country"]]
        )
        iso_countries = (
            row["country_iso3"]
            if isinstance(row["country_iso3"], list)
            else [row["country_iso3"]]
        )

        # --- Extract geometry from Nominatim raw output ---
        geom = None
        geometry_type = None

        if (
            best_nomin is not None
            and hasattr(best_nomin, "raw")
            and "geojson" in best_nomin.raw
        ):
            coords = best_nomin.raw["geojson"]["coordinates"]
            geom_type = best_nomin.raw["geojson"]["type"].strip().lower()

            if geom_type == "point":
                geom = Point(coords[0], coords[1])
                geometry_type = "point"
            elif geom_type == "polygon":
                geom = Polygon(coords[0])
                geometry_type = "polygon"
            elif geom_type == "multipolygon":
                geom = MultiPolygon([Polygon(p[0]) for p in coords])
                geometry_type = "multipolygon"
            else:
                LOGGER.warning(
                    "[geocode_nomin_geom] Unknown geometry type: %s", geom_type
                )

        # --- If no geometry from Nominatim → fall back to country union ---
        if geom is None:
            return gpd.GeoDataFrame(
                {
                    "geometry": [None],
                    "location": [location],
                    "iso3_code": [iso_countries[0] if iso_countries else None],
                    "ADMIN_0": [countries[0] if countries else None],
                    "ADMIN_1": [None],
                    "ADMIN_2": [None],
                    "admin_level": [None],
                    "osm_flag": [None],
                    "geometry_type": ["no_geometry"],
                },
                crs="EPSG:4326",
            )

        # --- Build a minimal GeoDataFrame from the Nominatim geometry ---
        adm_lev = int(best_result["admin_level"]) if best_result else 0
        adm_lev = min(adm_lev, 2)  # cap at ADM_2

        gdf_nomin = gpd.GeoDataFrame(
            {
                "geometry": [geom],
                "location": [location],
                "iso3_code": [
                    (
                        best_result["country_iso3"]
                        if best_result
                        else (iso_countries[0] if iso_countries else None)
                    )
                ],
                "ADMIN_0": [
                    best_result.get("country") if best_result else countries[0]
                ],
                "ADMIN_1": [
                    best_result.get("name") if best_result and adm_lev >= 1 else None
                ],
                "ADMIN_2": [
                    best_result.get("name") if best_result and adm_lev == 2 else None
                ],
                "admin_level": [adm_lev],
                "osm_flag": [1],
            },
            crs="EPSG:4326",
        )

        # --- Filter to expected countries ---
        gdf_nomin = gdf_nomin[gdf_nomin["iso3_code"].isin(iso_countries)]

        if gdf_nomin.empty:
            return gpd.GeoDataFrame(
                {
                    "geometry": [None],
                    "location": [location],
                    "iso3_code": [iso_countries[0] if iso_countries else None],
                    "ADMIN_0": [countries[0] if countries else None],
                    "ADMIN_1": [None],
                    "ADMIN_2": [None],
                    "admin_level": [None],
                    "osm_flag": [None],
                    "geometry_type": ["no_geometry"],
                },
                crs="EPSG:4326",
            )

        # --- Delegate final formatting to prepare_result_df, then tag geometry_type ---
        result = prepare_result_df(gdf_nomin, best_result, location, osm_flag=1)
        return result.assign(geometry_type=geometry_type)

    except Exception as e:
        LOGGER.warning("[geocode_from_nominatim_output_geom] %s.", e)
        return gpd.GeoDataFrame(
            {
                "geometry": [None],
                "location": [location],
                "iso3_code": [iso_countries[0] if iso_countries else None],
                "ADMIN_0": [countries[0] if countries else None],
                "ADMIN_1": [None],
                "ADMIN_2": [None],
                "admin_level": [None],
                "osm_flag": [None],
                "geometry_type": ["no_geometry"],
            },
            crs="EPSG:4326",
        )


# def run_parallel_geocode(nom_loc_dict, unique_locations_countries, unique_locations_countries_iso, gdf_file, print_info=False, max_workers=None):
def run_parallel_geocode(df_unique, gdf_file, print_info=False, max_workers=None):
    """Run geocoding for multiple locations in parallel using ThreadPoolExecutor,
    combining results into a single DataFrame."""
    results = []

    rows = df_unique.to_dict(orient="records")

    # run in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                geocode_from_nominatim_output_optimized, row, gdf_file, print_info
            ): (row["location"], row["country_iso3"])
            # for _, row in df_unique.iterrows()
            for row in rows
        }

        # for future in futures:
        for future in tqdm(
            futures, desc="Geocoding locations"
        ):  # Version with prints from the function called
            # location = futures[future]
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


def run_parallel_geocode_nomin(df_unique, gdf_file, print_info=False, max_workers=None):
    """Run geocoding for multiple locations in parallel using ThreadPoolExecutor,
    combining results into a single DataFrame."""
    results = []

    rows = df_unique.to_dict(orient="records")

    # run in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(geocode_nomin_geom, row, gdf_file, print_info): (
                row["location"],
                row["country"],
            )
            # for _, row in df_unique.iterrows()
            for row in rows
        }

        # for future in futures:
        for future in tqdm(
            futures, desc="Geocoding locations"
        ):  # Version with prints from the function called
            # location = futures[future]
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
def associate_locations_to_polygons(
    row,
    df_geo_individual_locs,
    gdf_file,
    split_lowest_levels=True,
    polygon_source="GAUL",
):
    """Associate one row of locations with administrative boundary polygons,
    merging geometries to the lowest (or multiple) admin levels and returning
    a GeoDataFrame row with enriched metadata."""
    locations = normalize_to_list(row.get("location"))
    countries = normalize_to_list(row.get("country_robust"))
    iso3_codes = [
        iso for iso in normalize_to_list(row.get("country_robust_iso3")) if iso
    ]

    if locations:  # check if list is non-empty
        location_mask = df_geo_individual_locs["location"].isin(locations)
    elif countries:
        location_mask = df_geo_individual_locs["location"].isin(countries)
    else:
        location_mask = pd.Series(False, index=df_geo_individual_locs.index)

    if iso3_codes:
        df_locations = df_geo_individual_locs.loc[
            location_mask & df_geo_individual_locs["iso3_code"].isin(iso3_codes)
        ]
    else:
        # If ISO3 is missing for this row, fall back to location-only matching.
        df_locations = df_geo_individual_locs.loc[location_mask]

    df_geo_output = pd.DataFrame()

    # If no matching found, return an empty file
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

    # Clean to have a single admin level per location
    max_level = df_locations.groupby("location")["finest_level"].transform("max")
    df_locations = df_locations[df_locations["finest_level"] == max_level].copy()
    df_locations.reset_index(drop=True, inplace=True)

    # Retrieve the lowest admin level
    lowest_level = df_locations["finest_level"].min()
    highest_level = df_locations["finest_level"].max()

    if split_lowest_levels:
        highest_level = df_locations["finest_level"].max()
    else:
        highest_level = lowest_level

    rows_to_append = []
    # Merge all the locs to the lewest admin levels
    for merge_level in range(lowest_level, highest_level + 1):
        layer_name = f"ADM_{merge_level}"
        df_location_subset = df_locations.loc[
            df_locations["finest_level"] >= merge_level
        ]
        merged_geometry = sanitize_and_merge_geometries(df_location_subset["geometry"])
        # merged_geometry, location_names = gather_to_lowest_admin(df_location_subset, gdf_file, merge_level)

        # flag_country_count = df_location_subset.loc[
        #     df_location_subset["flag_geocoding_country"] == 1, "location"
        # ].nunique()

        # # Count unique locations where the OSM flag == 1
        # flag_osm_count = df_location_subset.loc[
        #     df_location_subset["flag_geocoding_osm"] == 1, "location"
        # ].nunique()

        flag_country = int((df_location_subset["flag_geocoding_country"] == 1).any())

        flag_osm = int((df_location_subset["flag_geocoding_osm"] == 1).any())

        df_row_append = pd.DataFrame([row])
        df_row_append["geometry"] = merged_geometry
        df_row_append["locationLowestAdmin"] = layer_name
        df_row_append["flag_geocoding_country"] = flag_country
        df_row_append["flag_geocoding_osm"] = flag_osm
        df_row_append["locationOsm"] = [
            df_location_subset["locationOsm"].unique().tolist()
        ]
        # df_row_append["locationPolygon"] = [location_names]#[df_location_subset["locationPolygon"].unique().tolist()]
        df_row_append["locationPolygon"] = [
            df_location_subset["locationPolygon"].unique().tolist()
        ]

        # For the codes, take the list
        df_row_append["iso3_code"] = [df_location_subset["iso3_code"].unique().tolist()]
        if polygon_source == "GAUL":
            for code in ["gaul0_code", "gaul1_code", "gaul2_code"]:
                # df_row_append[code] = df_location_subset[code].unique().tolist()
                df_row_append[code] = [df_location_subset[code].unique().tolist()]

        # Remove the impact value if it's not the lowest admin level
        if merge_level != lowest_level:
            df_row_append["impactValue"] = np.nan
            df_row_append["impactUnit"] = np.nan
            df_row_append["impactValueApprox"] = np.nan

        rows_to_append.append(df_row_append)
    df_geo_output = pd.concat(rows_to_append, ignore_index=True)
    return df_geo_output


def run_parallel_associate(
    df_geo,
    df_geo_individual_locs,
    gdf_file,
    split_lowest_levels=True,
    polygon_source="GAUL",
    max_workers=None,
):
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
                polygon_source,
            ): i
            for i, row in enumerate(rows)
        }

        # for future in futures:
        for future in tqdm(
            futures, desc="Merging locations"
        ):  ### VERSION WITH TRACKING PRINT INFORMATIONS
            i = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    results.append(df)
            except Exception as e:
                row = rows[i]
                debug_subset = {
                    key: row.get(key, "MISSING")
                    for key in ["location", "country_robust", "country_robust_iso3"]
                }
                LOGGER.error("Error processing row %i: %s", i, e)
                LOGGER.error("Type of row: %s", type(row))
                LOGGER.error(
                    "Full row content:\n%s", pprint.pformat(debug_subset, indent=4)
                )
                LOGGER.error("Traceback:\n%s", traceback.format_exc())

    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()


def run_parallel_in_batches(
    df_geo, df_geo_individual_locs, gdf_file, batch_size=2000, **kwargs
):
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
        start = time.time()
        res = run_parallel_associate(
            df_batch, df_geo_individual_locs, gdf_file, **kwargs
        )
        print("Batch took", time.time() - start)
        if res is not None and not res.empty:
            results.append(res)
        # free memory between batches
        gc.collect()
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


##### Global function to perform the whole geocoding


def geocode_df_to_polygon_by_unique_loc(
    df,
    similarity_th=0.5,
    print_info=False,
    save_path=False,
    res_savename=False,
    polygon_source="GAUL",
    **kwargs,
):
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

    # Run nominatim for each loc
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
    if not res_savename : 
        nominatim_save_path = DATA_OUT_PROC / (f"nominatim_output_{dt.date.today().strftime('%d%m%y')}.csv")
    else : 
        nominatim_save_path = DATA_OUT_PROC / (f"nominatim_output_{res_savename}.csv")
    unique_loc.to_csv(nominatim_save_path, index=False)
    # atomic_gpkg_save(unique_loc, nominatim_save_path)
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
        geocode_unique_save_path = DATA_OUT_PROC / (f"geocode_unique_{dt.date.today().strftime('%d%m%y')}.gpkg")
    atomic_gpkg_save(
        df_geo_individual_locs, geocode_unique_save_path, layer_name="multipolygons"
    )
    LOGGER.info("Geocoded unique locations saved in %s", geocode_unique_save_path)

    # Gather the polygons to df_row for 2 split options
    for split_lowest_levels in [True, False]:
        start = time.time()
        max_workers = min(10, (os.cpu_count() or 1))
        df_geo_output = run_parallel_in_batches(
            df_geo,
            df_geo_individual_locs,
            gpd_files,
            split_lowest_levels=split_lowest_levels,
            polygon_source=polygon_source,
            max_workers=max_workers,
            batch_size=2000,
        )
        end = time.time()
        time_open = (end - start) / 60
        LOGGER.info("Time to gather all locations per rows %.2fmins", time_open)

        # Save the final df
        if save_path:
            suffix = "_geo_split_lowest" if split_lowest_levels else "_geo"
            res_savename_suffix = f"{res_savename}{suffix}"
            save_df_geo(df_geo_output, save_path, res_savename_suffix)
        if split_lowest_levels:
            df_geo_output_split = df_geo_output.copy()

    return df_geo_output_split, df_geo_output
