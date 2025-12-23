import pandas as pd
import json
from collections import Counter
import numpy as np
import pandas as pd
import seaborn as sns
import spacy
import re
import pycountry
import copy as cp
from random import randrange, randint
import ast
import geopy as gpy
import itertools
import time
import datetime as dt
from rapidfuzz.distance import Levenshtein
from shapely.geometry import Polygon, Point, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
import shapely
import logging
from rapidfuzz import fuzz, process

import geopandas as gpd

import sys
import os

LOGGER = logging.getLogger("postprocessing")

unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern_country = '|'.join(map(re.escape, unique_country_names))

NONISO_REGIONS = [
    # Dummy region for numeric 0 (or empty string), sometimes used for oceans
    dict(name="", alpha_2="", alpha_3="", numeric="000"),
    dict(name="Akrotiri", alpha_2="XA", alpha_3="XXA", numeric="901"),
    dict(name="Baikonur", alpha_2="XB", alpha_3="XXB", numeric="902"),
    dict(name="Bajo Nuevo Bank", alpha_2="XJ", alpha_3="XXJ", numeric="903"),
    dict(name="Bir Tawil", alpha_2="XQ", alpha_3="XXQ", numeric="919"),
    dict(name="Brazilian I.", alpha_2="XE", alpha_3="XXE", numeric="909"),
    dict(name="Clipperton I.", alpha_2="XC", alpha_3="XXC", numeric="904"),
    dict(name="Coral Sea Is.", alpha_2="XO", alpha_3="XXO", numeric="905"),
    dict(name="Cyprus U.N. Buffer Zone", alpha_2="XU", alpha_3="XXU", numeric="906"),
    dict(name="Dhekelia", alpha_2="XD", alpha_3="XXD", numeric="907"),
    dict(name="Indian Ocean Ter.", alpha_2="XI", alpha_3="XXI", numeric="908"),
    # For Kosovo, we follow the iso3166 package and the statistical office of Canada:
    # https://www.statcan.gc.ca/eng/subjects/standard/sccai/2011/scountry-desc
    dict(name="Kosovo", alpha_2="XK", alpha_3="XKO", numeric="983"),
    dict(name="N. Cyprus", alpha_2="XY", alpha_3="XXY", numeric="910"),
    dict(name="Scarborough Reef", alpha_2="XS", alpha_3="XXS", numeric="912"),
    dict(name="Serranilla Bank", alpha_2="XR", alpha_3="XXR", numeric="913"),
    dict(name="Siachen Glacier", alpha_2="XH", alpha_3="XXH", numeric="914"),
    dict(name="Somaliland", alpha_2="XM", alpha_3="XXM", numeric="915"),
    dict(
        name="Southern Patagonian Ice Field", alpha_2="XN", alpha_3="XXN", numeric="918"
    ),
    dict(name="Spratly Is.", alpha_2="XP", alpha_3="XXP", numeric="916"),
    dict(name="USNB Guantanamo Bay", alpha_2="XG", alpha_3="XXG", numeric="917"),
]
"""Geopolitical areas that are not listed in the ISO 3166 standard, but might be relevant when
working, e.g. with Natural Earth shape files. The alpha-2, alpha-3 and numeric representations are
unofficial and for internal use only."""

LOCATION_LEVEL_MAPPING = {
    'admin2': {'admin_level': 2, 'nominatim_keys': ['city', 'town', 'village', 'municipality',
                                                    'city_district', 'district', 'borough', 'suburb', 'subdivision',
                                                    'hamlet', 'croft', 'isolated_dwelling']},
    'admin1': {'admin_level': 1, 'nominatim_keys': ['state', 'province', 'region', 'county', 'territory', 'department', 'governorate', 'autonomous_region', 'state_district', 'district', 'metropolitan_area', 'subregion', 'zone']},
    'admin0': {'admin_level': 0, 'nominatim_keys': ['country']}
}

LIST_ADMIN_WORDS = [
    "Regency", "Province", "State", "Department", "Region", "River",
    "Territory", "County", "District", "Municipality", "Prefecture",
    "Canton", "Commune", "Borough", "Parish", "Metropolitan Area",
    "Subregion", "Zone", "Subdivision", "Ward", "Township", "City",
    "Village", "Hamlet", "Municipality", "Governorate", "Autonomous Region",
    "County Borough", "Council Area", "Federal District", "Locality"
]

def fuzzy_country_match(query):
    """
    Perform fuzzy matching of a country name against ISO 3 country names.

    Uses fuzzy string matching to identify the closest matching country
    name from the pycountry database and returns both the matched country
    object and the similarity score.

    Parameters
    ----------
    query : str
        Country name or identifier to be matched.

    Returns
    -------
    tuple
        - pycountry.db.Country or None : Best matching country object.
        - int : Fuzzy matching score (0–100). Returns 0 if no match is found.
    """
    choices = {c.name: c for c in pycountry.countries}
    result = process.extractOne(
        query,
        choices.keys(),
        scorer=fuzz.WRatio
    )
    if result:
        best_name, score, _ = result
        return choices[best_name], score
    return None, 0

def country_to_iso(countries, representation="alpha3", fillvalue=None, fuzzy_threshold=60):
    """Determine ISO 3166 representation of countries

    Example
    -------
    >>> country_to_iso(840)
    'USA'
    >>> country_to_iso("United States", representation="alpha2")
    'US'
    >>> country_to_iso(["United States of America", "SU"], "numeric")
    [840, 810]

    Some geopolitical areas that are not covered by ISO 3166 are added in the "user-assigned"
    range of ISO 3166-compliant values:

    >>> country_to_iso(["XK", "Dhekelia"], "numeric")  # XK for Kosovo
    [983, 907]

    Parameters
    ----------
    countries : one of str, int, list of str, list of int
        Country identifiers: name, official name, alpha-2, alpha-3 or numeric ISO codes.
        Numeric representations may be specified as str or int.
    representation : str (one of "alpha3", "alpha2", "numeric", "name"), optional
        All countries are converted to this representation according to ISO 3166.
        Default: "alpha3".
    fillvalue : str or int or None, optional
        The value to assign if a country is not recognized by the given identifier. By default,
        a LookupError is raised. Default: None

    Returns
    -------
    iso_list : one of str, int, list of str, list of int
        ISO 3166 representation of countries. Will only return a list if the input is a list.
        Numeric representations are returned as integers.
    """
    return_single = np.isscalar(countries)
    countries = [countries] if return_single else countries

    if not re.match(r"(alpha[-_]?[23]|numeric|name)", representation):
        raise ValueError(f"Unknown ISO representation: {representation}")
    representation = re.sub(r"alpha-?([23])", r"alpha_\1", representation)

    iso_list = []
    for country in countries:

        # Check if the country is not already an ISO-CODE
        if isinstance(country, str):
            c_up = country.upper()
            if len(c_up) == 2:
                obj = pycountry.countries.get(alpha_2=c_up)
                if obj:
                    iso_list.append(getattr(obj, representation))
                    continue

            # alpha-3
            if len(c_up) == 3:
                obj = pycountry.countries.get(alpha_3=c_up)
                if obj:
                    iso_list.append(getattr(obj, representation))
                    continue

        # Numeric ISO codes (passed as int or numeric-string)
        if isinstance(country, (int, str)):
            try:
                num = int(country)
                if num in pycountry.countries.by_numeric:
                    iso_list.append(
                        getattr(pycountry.countries.by_numeric[num], representation)
                    )
                    continue
            except ValueError:
                pass

        # Otherwise look for the iso corresponding to the country name
        country = country if isinstance(country, str) else f"{int(country):03d}"
        try:
            match = pycountry.countries.lookup(country)
        except LookupError:
            try:
                match = pycountry.historic_countries.lookup(country)
            except LookupError:
                match = next(
                    filter(lambda c: country in c.values(), NONISO_REGIONS), None
                )
                if match is not None:
                    match = pycountry.db.Data(**match)
                elif fillvalue is not None:
                    match = pycountry.db.Data({representation: fillvalue})
                else:
                    # raise LookupError(
                    #     f"Unknown country identifier: {country}"
                    # ) from None
                    best, score = fuzzy_country_match(country)
                    if best and score >= fuzzy_threshold:
                        match = best
                    elif fillvalue is not None:
                        match = pycountry.db.Data({representation: fillvalue})
                    else:
                        # raise LookupError(
                        #     f"Unknown country identifier: {country}. "
                        #     f"Best fuzzy match={getattr(best,'name',None)}, score={score}"
                        # )
                        iso_list.append(None)
                        continue
        iso = getattr(match, representation)
        if representation == "numeric":
            iso = int(iso)
        iso_list.append(iso)

    return iso_list[0] if return_single else iso_list

#### Helpers functions

def get_country_languages_dict():
    """Build a dictionary mapping each country name to its primary language code."""
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

def remove_admin_words(location_str):
    """Remove predefined administrative words from a location string without affecting substrings."""
    # Create a regex pattern that matches whole words only, case-insensitive
    pattern = r'\b(?:' + '|'.join(re.escape(word) for word in LIST_ADMIN_WORDS) + r')\b'
    # Substitute matches with empty string
    location_str = re.sub(pattern, '', location_str, flags=re.IGNORECASE)
    # Remove extra spaces
    location_str = ' '.join(location_str.split())
    return location_str

def get_country_languages_dict():
    """Build a dictionary mapping each country name to its primary language code."""
    country_languages = {}
    for country in pycountry.countries:
        try:
            lang_code = langcodes.get(country.alpha_2).language
            if lang_code:
                country_languages[country.name] = lang_code
        except:
            continue
    return country_languages

def clean_geometry(geom):
    """Fix invalid geometries using buffer(0)."""
    if geom is None or geom.is_empty:
        return None
    try:
        cleaned = geom.buffer(0)
        return cleaned

    except Exception as e:
        LOGGER.error("[clean_geometry] Failed to buffer geometry: %s", e)
        return None
    return geom

def to_flat_multipolygon(geometries):
    """
    Flatten a list of geometries into a single MultiPolygon.

    Iterates through a list of Shapely geometries, converting all
    Polygon and MultiPolygon objects into a single flat MultiPolygon.
    GeometryCollections are recursively flattened. Returns None if
    no valid polygons are found.

    Parameters
    ----------
    geometries : list of shapely.geometry.base.BaseGeometry
        List of Shapely geometries to flatten.

    Returns
    -------
    shapely.geometry.MultiPolygon or None
        Flattened MultiPolygon containing all valid polygons, or None
        if no valid geometries are present.

    Raises
    ------
    ValueError
        If an unsupported geometry type is encountered.
    """
    flat_polys = []

    for geom in geometries:
        if geom is None or geom.is_empty:
            continue

        if isinstance(geom, Polygon):
            flat_polys.append(geom)

        elif isinstance(geom, MultiPolygon):
            flat_polys.extend(list(geom.geoms))

        elif isinstance(geom, GeometryCollection):
            for g in geom.geoms:
                if isinstance(g, Polygon):
                    flat_polys.append(g)
                elif isinstance(g, MultiPolygon):
                    flat_polys.extend(list(g.geoms))
        else:
            raise ValueError(f"Unsupported geometry type: {type(geom)}")

    if not flat_polys:
        return None

    return MultiPolygon(flat_polys)

def sanitize_and_merge_geometries(geometries):
    """
    Clean and flatten geometries, keeping all polygons without unioning.

    Performs the following steps:
    1. Cleans individual geometries using `clean_geometry`.
    2. Flattens MultiPolygon and GeometryCollection objects to individual
       Polygons.
    3. Deduplicates polygons based on normalized WKB.
    4. Returns a MultiPolygon of all unique polygons or None if empty.

    Parameters
    ----------
    geometries : list of shapely.geometry.base.BaseGeometry
        List of Shapely geometries to sanitize and merge.

    Returns
    -------
    shapely.geometry.MultiPolygon or None
        MultiPolygon of all unique polygons after cleaning and flattening,
        or None if no valid polygons exist.
    """
    polys = []

    for g in geometries:
        if g is None or g.is_empty:
            continue

        g2 = clean_geometry(g)
        if g2 is None or g2.is_empty:
            continue

        if isinstance(g2, Polygon):
            polys.append(g2)

        elif isinstance(g2, MultiPolygon):
            polys.extend(list(g2.geoms))

        elif isinstance(g2, GeometryCollection):
            for gg in g2.geoms:
                if isinstance(gg, Polygon):
                    polys.append(gg)
                elif isinstance(gg, MultiPolygon):
                    polys.extend(list(gg.geoms))

    if not polys:
        return None

    # ---- Deduplicate geometries ----
    unique = {}
    for p in polys:
        # normalize() ensures consistent vertex ordering
        key = p.normalize().wkb
        unique[key] = p

    return MultiPolygon(list(unique.values()))
    # return MultiPolygon(polys)

def get_continent(iso_code, world):
    """
    Retrieve the continent for a given ISO-3166 alpha-3 country code.

    Looks up the ISO code in a GeoDataFrame containing world geometry
    data and returns the corresponding continent name. Returns None if
    the ISO code is not found.

    Parameters
    ----------
    iso_code : str
        ISO-3166 alpha-3 country code.
    world : geopandas.GeoDataFrame
        GeoDataFrame containing at least the columns 'ISO_A3' and
        'CONTINENT'.

    Returns
    -------
    str or None
        Continent name corresponding to the ISO code, or None if not found.
    """
    try:
        return world[world['ISO_A3'] == iso_code]['CONTINENT'].values[0]
    except IndexError:
        return None

def split_continents(df_geom, world) :
    """
    Split a GeoDataFrame into multiple GeoDataFrames by continent.

    Adds a 'continent' column to each row based on the ISO-3166 alpha-3
    code and returns a dictionary mapping continent names to GeoDataFrames.

    Parameters
    ----------
    df_geom : geopandas.GeoDataFrame
        GeoDataFrame containing a column 'country_iso3' with country ISO codes.
    world : geopandas.GeoDataFrame
        World GeoDataFrame containing 'ADM0_ISO' and 'CONTINENT' columns.

    Returns
    -------
    dict
        Dictionary where keys are continent names and values are
        GeoDataFrames containing only the rows for that continent.
    """
    iso_to_continent = (
        world[["ADM0_ISO", "CONTINENT"]]
        .dropna()
        .drop_duplicates()
        .set_index("ADM0_ISO")["CONTINENT"]
        .to_dict()
    )

    df_geom["continent"] = df_geom["country_iso3"].apply(
        lambda iso_list: sorted(
            {iso_to_continent.get(iso) for iso in iso_list if iso in iso_to_continent}
        ) if isinstance(iso_list, list) else []
    )
    return df_geom