import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
import numpy as np
import pandas as pd
from unittest.mock import patch
from shapely.geometry import Polygon, Point, MultiPolygon

from src.geocoding import (
    normalize_to_list,
    identify_robust_country,
    identify_unique_location_country,
    identify_unique_locations_v2,
    identify_unique_locations_v3,
    find_closest_country,
    find_best_match,
    fallback_country_union,
    prepare_result_df,
    associate_locations_to_polygons,
)
from src.geocoding_utils import (
    _normalize_country_key,
    country_to_iso,
    country_list_to_iso3,
    get_iso2_from_iso3,
    singularize_word,
    rotated_levenshtein_similarity,
    remove_admin_words,
    clean_geometry,
    to_flat_multipolygon,
    sanitize_and_merge_geometries,
    get_continent,
    split_continents,
    fuzzy_country_match,
)


class TestCountryIsoMapping(unittest.TestCase):
    def test_country_to_iso_common_variants(self):
        expected = {
            "LAO PDR": "LAO",
            "Lao P.D.R.": "LAO",
            "DPRK": "PRK",
            "I. R. of Iran": "IRN",
            "St. Lucia": "LCA",
            "Congo, Dem. Rep.": "COD",
            "Congo, Rep.": "COG",
            "The Bahamas": "BHS",
            "The Gambia": "GMB",
            "Micronesia": "FSM",
            "Swaziland": "SWZ",
            "Palestine": "PSE",
            "Turkey": "TUR",
        }
        for name, iso in expected.items():
            self.assertEqual(country_to_iso(name, representation="alpha3"), iso)

    def test_country_to_iso_handles_null_like_inputs(self):
        self.assertIsNone(country_to_iso(None, representation="alpha3"))
        self.assertIsNone(country_to_iso("", representation="alpha3"))
        self.assertIsNone(country_to_iso("None", representation="alpha3"))

    def test_country_list_to_iso3_filters_none(self):
        values = country_list_to_iso3(["Micronesia", None, "", "Somaliland"])
        self.assertEqual(values, ["FSM", "XXM"])

    def test_country_to_iso_numeric_and_alpha2(self):
        self.assertEqual(country_to_iso("840", representation="alpha3"), "USA")
        self.assertEqual(country_to_iso("US", representation="alpha3"), "USA")

    def test_country_to_iso3_to_iso2_roundtrip(self):
        self.assertEqual(get_iso2_from_iso3("USA"), "US")
        self.assertEqual(get_iso2_from_iso3(["USA", "FRA"]), ["US", "FR"])

    def test_normalize_country_key(self):
        self.assertEqual(
            _normalize_country_key(" The Congo, Dem. Rep. "), "congo dem rep"
        )

    def test_fuzzy_country_match(self):
        best, score = fuzzy_country_match("Argentin")
        self.assertIsNotNone(best)
        self.assertGreater(score, 0)


class TestGeocodingUtilsGeometry(unittest.TestCase):
    def test_singularize_word(self):
        self.assertEqual(singularize_word("structures"), "structure")

    def test_rotated_levenshtein_similarity(self):
        self.assertAlmostEqual(
            rotated_levenshtein_similarity("new york city", "city new york"), 1.0
        )

    def test_remove_admin_words(self):
        self.assertEqual(remove_admin_words("New York City Municipality"), "new york")

    def test_clean_geometry(self):
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        cleaned = clean_geometry(bowtie)
        self.assertTrue(cleaned is None or cleaned.is_valid)

    def test_to_flat_multipolygon(self):
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        p2 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])
        out = to_flat_multipolygon([p1, MultiPolygon([p2])])
        self.assertIsInstance(out, MultiPolygon)
        self.assertEqual(len(out.geoms), 2)

    def test_sanitize_and_merge_geometries(self):
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        p2 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        out = sanitize_and_merge_geometries([p1, p2])
        self.assertIsInstance(out, MultiPolygon)
        self.assertGreaterEqual(len(out.geoms), 1)

    def test_get_continent_and_split_continents(self):
        world = pd.DataFrame(
            {
                "ISO_A3": ["USA"],
                "ADM0_ISO": ["USA"],
                "CONTINENT": ["North America"],
            }
        )
        self.assertEqual(get_continent("USA", world), "North America")

        df_geom = pd.DataFrame({"country_iso3": [["USA"]]})
        out = split_continents(df_geom, world)
        self.assertEqual(out.loc[0, "continent"], ["North America"])


class TestGeocodingRowHandling(unittest.TestCase):
    def test_normalize_to_list(self):
        self.assertEqual(normalize_to_list(None), [])
        self.assertEqual(normalize_to_list(np.nan), [])
        self.assertEqual(normalize_to_list(" none "), [])
        self.assertEqual(normalize_to_list("Micronesia"), ["Micronesia"])
        self.assertEqual(normalize_to_list(["A", None, "nan", "B"]), ["A", "B"])

    def test_identify_robust_country_merges_columns(self):
        df = pd.DataFrame(
            {
                "country": [["Micronesia"], None],
                "country_kw": [["Federated States of Micronesia"], ["Palestine"]],
            }
        )
        out = identify_robust_country(df, "country", "country_kw", "country_robust")
        self.assertIn("country_robust", out.columns)
        self.assertEqual(
            out.loc[0, "country_robust"],
            ["Federated States of Micronesia", "Micronesia"],
        )
        self.assertEqual(out.loc[1, "country_robust"], ["Palestine"])

    def test_associate_locations_to_polygons_handles_none_iso3(self):
        row = {
            "location": ["western FSM"],
            "country_robust": ["Micronesia"],
            "country_robust_iso3": None,
        }
        df_geo_individual_locs = pd.DataFrame(
            {
                "location": ["western FSM", "western FSM"],
                "iso3_code": ["FSM", "PLW"],
                "geometry": [np.nan, np.nan],
                "finest_level": [0, 0],
                "flag_geocoding_country": [0, 0],
                "flag_geocoding_osm": [0, 0],
                "locationOsm": ["western FSM", "western FSM"],
                "locationPolygon": ["FSM", "PLW"],
            }
        )

        out = associate_locations_to_polygons(row, df_geo_individual_locs, gdf_file={})
        self.assertIsInstance(out, pd.DataFrame)
        self.assertIn("geometry", out.columns)
        self.assertEqual(len(out), 1)

    def test_identify_unique_location_country(self):
        df = pd.DataFrame(
            {
                "country_robust": [["Micronesia"]],
                "country_robust_iso3": [["FSM"]],
                "country_robust_iso2": [["FM"]],
                "location": [["western FSM"]],
            }
        )
        out = identify_unique_location_country(df)
        self.assertIn("location", out.columns)
        self.assertIn("country_iso3", out.columns)
        self.assertEqual(out.loc[0, "country_iso3"], "FSM")

    def test_identify_unique_locations_v2_and_v3(self):
        df = pd.DataFrame(
            {
                "country_robust": [["France", "Italy"], ["France"]],
                "country_robust_iso3": [["FRA", "ITA"], ["FRA"]],
                "country_robust_iso2": [["FR", "IT"], ["FR"]],
                "location": [["Paris"], ["Paris"]],
            }
        )
        out_v2 = identify_unique_locations_v2(df)
        out_v3 = identify_unique_locations_v3(df)
        self.assertGreaterEqual(len(out_v2), 1)
        self.assertGreaterEqual(len(out_v3), 1)

    def test_find_closest_country(self):
        gdf = pd.DataFrame({"ADMIN_0": ["France", "Italy"]})
        self.assertEqual(find_closest_country("Frnace", gdf, threshold=0.4), "France")

    def test_find_best_match(self):
        address = {"city": "new york"}
        info, sim = find_best_match("new york", address, 0.5)
        self.assertGreaterEqual(sim, 0.5)
        self.assertIn("admin_level", info)

    def test_prepare_result_df(self):
        df = pd.DataFrame({"ADMIN_1": ["New York"], "geometry": [Point(0, 0)]})
        best = {"admin_level": 1, "name": "new york", "admin_field": "ADMIN_1"}
        out = prepare_result_df(df, best, "new york")
        self.assertIn("locationOsm", out.columns)
        self.assertEqual(out.loc[0, "location"], "new york")

    @patch("src.geocoding.get_polygon")
    def test_fallback_country_union(self, mock_get_polygon):
        poly_df = pd.DataFrame(
            {
                "geometry": [Point(0, 0).buffer(0.1)],
                "iso3_code": ["FSM"],
                "ADMIN_0": ["Micronesia"],
            }
        )
        mock_get_polygon.return_value = poly_df
        out = fallback_country_union(
            {"ADM_0": pd.DataFrame()}, "western FSM", ["Micronesia"], ["FSM"]
        )
        self.assertIn("location", out.columns)
        self.assertEqual(out.loc[out.index[0], "location"], "western FSM")


if __name__ == "__main__":
    unittest.main()
