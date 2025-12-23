import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
import pandas as pd
import geopandas as gpd
import numpy as np
from unittest.mock import patch, MagicMock
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import shapely
from collections import defaultdict
import sys, os
import tempfile
import pprint
import traceback

from src.geocoding import (
    identify_robust_country,
    fallback_country_union,
    gather_to_lowest_admin,
    remove_admin_words,
    rotated_levenshtein_similarity,
    atomic_gpkg_save,
    save_df_geo,
    geocode_from_nominatim_output_optimized,
    fallback_country_union,
    prepare_result_df,
    run_parallel_geocode,
    associate_locations_to_polygons,
    run_parallel_associate,
    run_parallel_in_batches,
    geocode_df_to_polygon_by_unique_loc,
)
from src.geocoding_utils import (    
    clean_geometry,
    to_flat_multipolygon,
    sanitize_and_merge_geometries,
    remove_admin_words,
    rotated_levenshtein_similarity,
    country_to_iso
    )

class TestGeocodingUtils(unittest.TestCase):
    def test_clean_geometry_valid_polygon(self):
        poly = Polygon([(0,0), (1,0), (1,1), (0,1)])
        cleaned = clean_geometry(poly)
        self.assertTrue(cleaned.is_valid)
        self.assertEqual(cleaned.area, poly.area)

    def test_clean_geometry_none_or_empty(self):
        self.assertIsNone(clean_geometry(None))
        self.assertIsNone(clean_geometry(Polygon()))

    def test_to_flat_multipolygon(self):
        poly1 = Polygon([(0,0), (1,0), (1,1), (0,1)])
        poly2 = Polygon([(2,2), (3,2), (3,3), (2,3)])
        mp = MultiPolygon([poly1, poly2])
        result = to_flat_multipolygon([poly1, mp])
        self.assertIsInstance(result, MultiPolygon)
        self.assertEqual(len(result.geoms), 3)

    def test_sanitize_and_merge_geometries(self):
        poly1 = Polygon([(0,0), (1,0), (1,1), (0,1)])
        poly2 = Polygon([(1,1), (2,1), (2,2), (1,2)])
        merged = sanitize_and_merge_geometries([poly1, poly2, None])
        self.assertTrue(merged.is_valid)
        self.assertTrue(merged.area > 1.0)

    def test_remove_admin_words(self):
        loc = "New York City Municipality"
        cleaned = remove_admin_words(loc)
        self.assertEqual(cleaned, "New York")

    def test_rotated_levenshtein_similarity_simple(self):
        s1 = "New York City"
        s2 = "City New York"
        sim = rotated_levenshtein_similarity(s1, s2)
        self.assertAlmostEqual(sim, 1.0)

    def test_country_to_iso_basic(self):
        iso = country_to_iso("United States")
        self.assertEqual(iso, "USA")
        iso2 = country_to_iso(["United States", "France"])
        self.assertEqual(iso2, ["USA", "FRA"])

class TestGeocoding(unittest.TestCase):
    def test_identify_robust_country_basic(self):
        df = pd.DataFrame({
            "country": ["USA", None],
            "country_iso3": ["USA", None],
            "country_kw": ["United States", "Canada"],
            "country_iso3_kw": ["USA", "CAN"],
            "location": [["New York"], None]
        })
        keys, loc_to_country, loc_to_iso = identify_robust_country(df)
        # Should handle missing country & location correctly
        self.assertIn(("New York", "USA"), keys)
        self.assertIn(("Canada", "Canada"), keys)

    def test_fallback_country_union_empty(self):
        empty_result = fallback_country_union({}, [], [])
        # Should return a dataframe with expected columns
        expected_cols = [
            "finest_level", "locationOsm", "locationPolygon",
            "flag_geocoding_osm", "flag_geocoding_country", "geometry"
        ]
        self.assertListEqual(list(empty_result.columns), expected_cols)

    def test_gather_to_lowest_admin_basic(self):
        poly = Polygon([(0,0), (1,0), (1,1), (0,1)])
        df_locations = pd.DataFrame({
            "geometry": [poly],
            "finest_level": [1],
            "locationPolygon": ["TestLocation"],
            "ADMIN_0": ["USA"],
            "ADMIN_1": ["New York"],
            "ADMIN_2": ["Albany"]
        })
        gpd_files = {
            "ADM_1": pd.DataFrame({
                "ADMIN_0": ["USA"],
                "ADMIN_1": ["New York"],
                "geometry": [poly]
            }),
            "ADM_2": pd.DataFrame({
                "ADMIN_0": ["USA"],
                "ADMIN_1": ["New York"],
                "ADMIN_2": ["Albany"],
                "geometry": [poly]
            })
        }
        merged_geom, loc_names = gather_to_lowest_admin(df_locations, gpd_files, lowest_level=1)
        self.assertEqual(len(loc_names), 1)
        self.assertTrue(merged_geom.is_valid)

    def test_remove_admin_words_basic(self):
        loc = "Albany County Municipality"
        cleaned = remove_admin_words(loc)
        self.assertEqual(cleaned, "Albany")

    def test_rotated_levenshtein_similarity_basic(self):
        s1 = "New York City"
        s2 = "City New York"
        sim = rotated_levenshtein_similarity(s1, s2)
        self.assertAlmostEqual(sim, 1.0)
    
    def setUp(self):
        # Example row for location processing
        self.row = {"location": ["Place1"], "country": ["USA"], "country_kw": ["USA"], "impactValue": 10, "impactUnit": "USD"}
        self.df_geo = pd.DataFrame([self.row])
        
        # Individual locations with geometries
        self.df_geo_individual_locs = pd.DataFrame({
            "location": ["Place1"],
            "geometry": [Point(0,0)],
            "finest_level": [2],
            "flag_geocoding_country": [1],
            "flag_geocoding_osm": [0],
            "locationOsm": ["Place1"],
            "locationPolygon": ["Place1"],
            "iso3_code": ["USA"],
            "gaul0_code": [1],
            "gaul1_code": [10],
            "gaul2_code": [100]
        })
        
        # Mocked GAUL-like GeoDataFrames
        self.gdf_file = {
            "ADM_0": self.df_geo_individual_locs,
            "ADM_1": self.df_geo_individual_locs,
            "ADM_2": self.df_geo_individual_locs
        }

    # ------------------ GeoPackage saving ------------------ #
    def test_atomic_gpkg_save(self):
        gdf = gpd.GeoDataFrame(self.df_geo_individual_locs, geometry="geometry")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = os.path.join(tmpdir, "test.gpkg")
            result = atomic_gpkg_save(gdf, target_path, layer_name="multipolygons")
            self.assertTrue(result)
            self.assertTrue(os.path.exists(target_path))

    def test_save_df_geo(self):
        gdf = gpd.GeoDataFrame(self.df_geo_individual_locs, geometry="geometry")
        with tempfile.TemporaryDirectory() as tmpdir:
            save_df_geo(gdf, tmpdir, "test_savename", split_lowest_levels=True)
            files = os.listdir(tmpdir)
            self.assertTrue(any(f.endswith(".gpkg") for f in files))

    # ------------------ Location association ------------------ #
    def test_associate_locations_to_polygons_basic(self):
        df_out = associate_locations_to_polygons(self.row, self.df_geo_individual_locs, self.gdf_file)
        self.assertIsInstance(df_out, pd.DataFrame)
        self.assertIn("geometry", df_out.columns)
        self.assertIn("locationLowestAdmin", df_out.columns)
        self.assertEqual(df_out.iloc[0]["flag_geocoding_country"], 1)

    @patch("src.geocoding.associate_locations_to_polygons")
    def test_run_parallel_associate(self, mock_associate):
        mock_associate.return_value = self.df_geo_individual_locs
        df_out = run_parallel_associate(self.df_geo, self.df_geo_individual_locs, self.gdf_file, max_workers=1)
        self.assertIsInstance(df_out, pd.DataFrame)
        self.assertIn("geometry", df_out.columns)
        self.assertTrue(mock_associate.called)

    @patch("src.geocoding.run_parallel_associate")
    def test_run_parallel_in_batches(self, mock_parallel):
        mock_parallel.return_value = self.df_geo_individual_locs
        df_out = run_parallel_in_batches(self.df_geo, self.df_geo_individual_locs, self.gdf_file, batch_size=1, max_workers=1)
        self.assertIsInstance(df_out, pd.DataFrame)
        self.assertIn("geometry", df_out.columns)
        self.assertTrue(mock_parallel.called)

    # ------------------ Full geocoding pipeline ------------------ #
    @patch("src.geocoding.open_admin_gpd")
    @patch("src.geocoding.identify_robust_country")
    @patch("src.geocoding.run_parallel_geocode")
    @patch("src.geocoding.run_parallel_in_batches")
    @patch("src.geocoding.save_df_geo")
    @patch("src.geocoding.find_best_nomin")
    def test_geocode_df_to_polygon_by_unique_loc(
        self, mock_find_best, mock_save, mock_batches, mock_parallel_geo, mock_identify, mock_open_gpd
    ):
        # Setup mocks
        mock_open_gpd.return_value = self.gdf_file
        mock_identify.return_value = (
            [("Place1", "USA")],
            {("Place1", "USA"): ["USA"]},
            {("Place1", "USA"): ["USA"]}
        )
        mock_find_best.return_value = (MagicMock(), {"admin_level": 2, "name": "Place1", "admin_field": "ADMIN_2", "country": "USA", "country_iso": "USA"})
        mock_parallel_geo.return_value = self.df_geo_individual_locs
        mock_batches.return_value = self.df_geo_individual_locs

        df_split, df_full = geocode_df_to_polygon_by_unique_loc(self.df_geo, save_path=False, res_savename=False)
        self.assertIsInstance(df_split, pd.DataFrame)
        self.assertIsInstance(df_full, pd.DataFrame)
        self.assertTrue(mock_save.called == False) 

if __name__ == "__main__":
    unittest.main()