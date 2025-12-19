import unittest
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

from src.accuracy import *


class TestVectorize(unittest.TestCase):
    def test_vectorize_single_value(self):
        """Test vectorizing a single value"""
        result = vectorize("a", ["a", "b", "c"])
        expected = np.array([1, 0, 0])
        np.testing.assert_array_equal(result, expected)

    def test_vectorize_list_values(self):
        """Test vectorizing a list of values"""
        result = vectorize(["a", "c"], ["a", "b", "c"])
        expected = np.array([1, 0, 1])
        np.testing.assert_array_equal(result, expected)

    def test_vectorize_no_match(self):
        """Test vectorizing when no values match"""
        result = vectorize("d", ["a", "b", "c"])
        expected = np.array([0, 0, 0])
        np.testing.assert_array_equal(result, expected)

    def test_vectorize_all_match(self):
        """Test vectorizing when all values match"""
        result = vectorize(["a", "b", "c"], ["a", "b", "c"])
        expected = np.array([1, 1, 1])
        np.testing.assert_array_equal(result, expected)

    def test_vectorize_empty_list(self):
        """Test vectorizing an empty list"""
        result = vectorize([], ["a", "b", "c"])
        expected = np.array([0, 0, 0])
        np.testing.assert_array_equal(result, expected)


class TestGetNanIds(unittest.TestCase):
    def test_get_nan_ids_mixed(self):
        """Test getting nan and non-nan ids with mixed data"""
        df = pd.DataFrame({"col": [1.0, np.nan, 3.0, np.nan]})
        not_nan_ids, nan_ids = get_nan_ids(df, "col")
        np.testing.assert_array_equal(not_nan_ids, np.array([0, 2]))
        np.testing.assert_array_equal(nan_ids, np.array([1, 3]))

    def test_get_nan_ids_all_nans(self):
        """Test getting nan ids when all values are nan"""
        df = pd.DataFrame({"col": [np.nan, np.nan, np.nan]})
        not_nan_ids, nan_ids = get_nan_ids(df, "col")
        self.assertEqual(len(not_nan_ids), 0)
        np.testing.assert_array_equal(nan_ids, np.array([0, 1, 2]))

    def test_get_nan_ids_no_nans(self):
        """Test getting nan ids when there are no nans"""
        df = pd.DataFrame({"col": [1.0, 2.0, 3.0]})
        not_nan_ids, nan_ids = get_nan_ids(df, "col")
        np.testing.assert_array_equal(not_nan_ids, np.array([0, 1, 2]))
        self.assertEqual(len(nan_ids), 0)


class TestSplitNansDf(unittest.TestCase):
    def test_split_nans_df_mixed(self):
        """Test splitting dataframe with mixed nan and non-nan values"""
        df = pd.DataFrame({
            "col": [1.0, np.nan, 3.0],
            "data": ["a", "b", "c"]
        })
        not_nan_df, nan_df = split_nans_df(df, "col")
        self.assertEqual(len(not_nan_df), 2)
        self.assertEqual(len(nan_df), 1)
        self.assertListEqual(not_nan_df["data"].tolist(), ["a", "c"])

    def test_split_nans_df_no_nans(self):
        """Test splitting dataframe with no nans"""
        df = pd.DataFrame({
            "col": [1.0, 2.0, 3.0],
            "data": ["a", "b", "c"]
        })
        not_nan_df, nan_df = split_nans_df(df, "col")
        self.assertEqual(len(not_nan_df), 3)
        self.assertEqual(len(nan_df), 0)


class TestSplitNans(unittest.TestCase):
    def test_split_nans_strict_both_with_nans(self):
        """Test strict policy when both dataframes have nans"""
        ext_df = pd.DataFrame({"col": [1.0, np.nan, 3.0]})
        lab_df = pd.DataFrame({"col": [2.0, np.nan, 4.0]})

        not_nan_ext, not_nan_lab, nan_ext, nan_lab = split_nans(ext_df, lab_df, "col", nan_policy="strict")

        self.assertEqual(len(not_nan_ext), 2)
        self.assertEqual(len(not_nan_lab), 2)
        self.assertEqual(len(nan_ext), 1)
        self.assertEqual(len(nan_lab), 1)

    def test_split_nans_loose_only_ext_nans(self):
        """Test loose policy when only extracted has nans"""
        ext_df = pd.DataFrame({"col": [1.0, np.nan, 3.0]})
        lab_df = pd.DataFrame({"col": [2.0, 4.0, 5.0]})

        not_nan_ext, not_nan_lab, nan_ext, nan_lab = split_nans(ext_df, lab_df, "col", nan_policy="loose")

        self.assertEqual(len(not_nan_ext), 2)
        self.assertEqual(len(not_nan_lab), 3)
        self.assertEqual(len(nan_ext), 1)
        self.assertEqual(len(nan_lab), 3)

    def test_split_nans_loose_only_lab_nans(self):
        """Test loose policy when only labelled has nans"""
        ext_df = pd.DataFrame({"col": [1.0, 2.0, 3.0]})
        lab_df = pd.DataFrame({"col": [2.0, np.nan, 4.0]})

        not_nan_ext, not_nan_lab, nan_ext, nan_lab = split_nans(ext_df, lab_df, "col", nan_policy="loose")

        self.assertEqual(len(not_nan_ext), 3)
        self.assertEqual(len(not_nan_lab), 2)
        self.assertEqual(len(nan_ext), 3)
        self.assertEqual(len(nan_lab), 1)

    def test_split_nans_no_nans(self):
        """Test when neither dataframe has nans"""
        ext_df = pd.DataFrame({"col": [1.0, 2.0, 3.0]})
        lab_df = pd.DataFrame({"col": [2.0, 3.0, 4.0]})

        not_nan_ext, not_nan_lab, nan_ext, nan_lab = split_nans(ext_df, lab_df, "col")

        self.assertEqual(len(not_nan_ext), 3)
        self.assertEqual(len(not_nan_lab), 3)
        self.assertEqual(len(nan_ext), 0)
        self.assertEqual(len(nan_lab), 0)


class TestIoU(unittest.TestCase):
    def test_iou_identical_polygons(self):
        """Test IoU of identical polygons"""
        poly = box(0, 0, 1, 1)
        result = IoU(poly, poly)
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_iou_non_overlapping(self):
        """Test IoU of non-overlapping polygons"""
        poly1 = box(0, 0, 1, 1)
        poly2 = box(2, 2, 3, 3)
        result = IoU(poly1, poly2)
        self.assertEqual(result, 0.0)

    def test_iou_partial_overlap(self):
        """Test IoU of partially overlapping polygons"""
        poly1 = box(0, 0, 2, 2)
        poly2 = box(1, 1, 3, 3)
        result = IoU(poly1, poly2)
        # Intersection area = 1x1 = 1
        # Union area = 4 + 4 - 1 = 7
        # IoU = 1/7 ≈ 0.1428
        self.assertAlmostEqual(result, 1/7, places=4)

    def test_iou_one_empty_geometry(self):
        """Test IoU with one empty geometry"""
        poly = box(0, 0, 1, 1)
        result = IoU(poly, None)
        self.assertEqual(result, 0)

    def test_iou_both_empty_geometries(self):
        """Test IoU with both empty geometries"""
        result = IoU(None, None)
        self.assertEqual(result, 0)

    def test_iou_subset(self):
        """Test IoU where one polygon is subset of another"""
        poly1 = box(0, 0, 2, 2)
        poly2 = box(0.5, 0.5, 1.5, 1.5)
        result = IoU(poly1, poly2)
        # Intersection area = 1x1 = 1
        # Union area = 4 + 1 - 1 = 4
        # IoU = 1/4 = 0.25
        self.assertAlmostEqual(result, 0.25, places=5)


class TestComputeIoU(unittest.TestCase):
    def setUp(self):
        """Set up test geodataframes"""
        self.gdf1 = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3)],
            crs="EPSG:4326"
        )
        self.gdf2 = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[box(0, 0, 1, 1), box(1.5, 1.5, 2.5, 2.5)],
            crs="EPSG:4326"
        )

    def test_compute_iou_shape(self):
        """Test that compute_iou returns correct shape"""
        result = compute_iou(self.gdf1, self.gdf2)
        self.assertEqual(result.shape, (2, 2))

    def test_compute_iou_identical_first(self):
        """Test IoU matrix with identical first geometry"""
        result = compute_iou(self.gdf1, self.gdf2)
        self.assertAlmostEqual(result[0, 0], 1.0, places=5)

    def test_compute_iou_non_overlapping(self):
        """Test IoU matrix with non-overlapping geometries"""
        result = compute_iou(self.gdf1, self.gdf2)
        self.assertEqual(result[1, 0], 0.0)


class TestScaledValueDiff(unittest.TestCase):
    def test_scaled_value_diff_single_value(self):
        """Test scaled difference with single values"""
        result = scaled_value_diff(10, 5)
        self.assertAlmostEqual(result, 0.5, places=5)

    def test_scaled_value_diff_arrays(self):
        """Test scaled difference with arrays"""
        v1 = np.array([10, 20, 30])
        v2 = np.array([5, 10, 15])
        result = scaled_value_diff(v1, v2)
        expected = np.array([0.5, 0.5, 0.5])
        np.testing.assert_array_almost_equal(result, expected)

    def test_scaled_value_diff_zero_division(self):
        """Test scaled difference with zero in v1"""
        result = scaled_value_diff(0, 5)
        self.assertTrue(np.isinf(result) or np.isnan(result))


class TestMaxValueDiff(unittest.TestCase):
    def test_max_value_diff_equal_values(self):
        """Test max value difference when values are equal"""
        result = max_value_diff([10, 10], [10, 10])
        np.testing.assert_array_equal(result, np.array([0.0, 0.0]))

    def test_max_value_diff_single_value(self):
        """Test max value difference with single value"""
        result = max_value_diff([10], [5])
        # scaled_diff(10,5) = (10-5)/10 = 0.5, scaled_diff(5,10) = (5-10)/5 = -1.0
        # max(abs(0.5), abs(-1.0)) = 1.0
        self.assertAlmostEqual(result[0], 1.0, places=5)


class TestCalcValueSim(unittest.TestCase):
    def test_calc_value_sim_identical(self):
        """Test value similarity with identical values"""
        result = calc_value_sim([10], [10])
        self.assertAlmostEqual(result[0], 1.0, places=5)

    def test_calc_value_sim_different(self):
        """Test value similarity with different values"""
        result = calc_value_sim([10], [5])
        self.assertTrue(0 <= result[0] <= 1)


class TestComputeWeightedSim(unittest.TestCase):
    def test_compute_weighted_sim_shape(self):
        """Test weighted similarity computation shape"""
        # Create a simple similarity matrix (2 extracted x 3 labelled x 2 features)
        dist_mat = np.array([
            [[0.8, 0.9], [0.7, 0.8], [0.6, 0.7]],
            [[0.9, 0.7], [0.8, 0.9], [0.7, 0.8]]
        ])
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 0.5, "col2": 0.5}

        result = compute_weighted_sim(dist_mat, similarity_cols, weights)
        self.assertEqual(result.shape, (2, 3))

    def test_compute_weighted_sim_values(self):
        """Test weighted similarity computation values"""
        # All same values, should average to same value
        dist_mat = np.ones((2, 3, 2)) * 0.8
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 0.5, "col2": 0.5}

        result = compute_weighted_sim(dist_mat, similarity_cols, weights)
        np.testing.assert_array_almost_equal(result, np.ones((2, 3)) * 0.8)

    def test_compute_weighted_sim_unequal_weights(self):
        """Test weighted similarity with unequal weights"""
        dist_mat = np.array([
            [[0.8, 0.2], [0.5, 0.5]],
            [[0.3, 0.7], [0.6, 0.4]]
        ])
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 0.7, "col2": 0.3}

        result = compute_weighted_sim(dist_mat, similarity_cols, weights)
        # (0.8*0.7 + 0.2*0.3) = 0.56 + 0.06 = 0.62
        expected_00 = (0.8 * 0.7 + 0.2 * 0.3) / 1.0
        self.assertAlmostEqual(result[0, 0], expected_00, places=5)

    def test_compute_weighted_sim_dimension_mismatch(self):
        """Test that dimension mismatch raises ValueError"""
        dist_mat = np.ones((2, 3, 2)) * 0.8
        similarity_cols = ["col1", "col2", "col3"]  # 3 cols but dist_mat has 2
        weights = {"col1": 0.5, "col2": 0.25, "col3": 0.25}

        with self.assertRaises(ValueError) as context:
            compute_weighted_sim(dist_mat, similarity_cols, weights)
        self.assertIn("dist_mat has 2 columns", str(context.exception))

    def test_compute_weighted_sim_missing_weights(self):
        """Test that missing weights raises ValueError"""
        dist_mat = np.ones((2, 3, 2)) * 0.8
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 0.5}  # Missing col2

        with self.assertRaises(ValueError) as context:
            compute_weighted_sim(dist_mat, similarity_cols, weights)
        self.assertIn("have no weights", str(context.exception))

    def test_compute_weighted_sim_with_nans(self):
        """Test weighted similarity computation with NaN values"""
        dist_mat = np.array([
            [[0.8, np.nan], [0.7, 0.8]],
            [[0.9, 0.7], [np.nan, 0.9]]
        ])
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 0.5, "col2": 0.5}

        result = compute_weighted_sim(dist_mat, similarity_cols, weights)
        # NaNs should be handled by np.nansum
        self.assertFalse(np.isnan(result[0, 0]))  # (0.8*0.5 + nan*0.5) / 1.0 = 0.8


class TestFindMatchSim(unittest.TestCase):
    def test_find_match_sim_unique_match(self):
        """Test finding best match with clear winner"""
        dist_mat = np.array([
            [[0.9, 0.5], [0.3, 0.4]],
            [[0.4, 0.3], [0.8, 0.9]]
        ])
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 0.5, "col2": 0.5}

        id_ext, id_lab = find_match_sim(dist_mat, similarity_cols, weights)
        self.assertEqual(len(id_ext), len(id_lab))

    def test_find_match_sim_calls_compute_weighted_sim(self):
        """Test that find_match_sim properly calls compute_weighted_sim with similarity_cols"""
        dist_mat = np.array([
            [[0.9, 0.5], [0.3, 0.4]],
            [[0.4, 0.3], [0.8, 0.9]]
        ])
        similarity_cols = ["col1", "col2"]
        weights = {"col1": 1.0, "col2": 1.0}

        # Should not raise an error about column mismatch
        id_ext, id_lab = find_match_sim(dist_mat, similarity_cols, weights)
        self.assertIsInstance(id_ext, np.ndarray)
        self.assertIsInstance(id_lab, np.ndarray)

    def test_find_match_sim_dimension_validation(self):
        """Test that dimension mismatch in find_match_sim raises error"""
        dist_mat = np.ones((2, 3, 2)) * 0.8
        similarity_cols = ["col1", "col2", "col3"]  # Mismatch: 3 vs 2
        weights = {"col1": 0.5, "col2": 0.25, "col3": 0.25}

        with self.assertRaises(ValueError):
            find_match_sim(dist_mat, similarity_cols, weights)


class TestFindMatchValue(unittest.TestCase):
    def test_find_match_value_single_match(self):
        """Test finding match by minimizing value difference"""
        ext_df = pd.DataFrame({"impactValue": [10.0, 20.0]}, index=[0, 1])
        lab_df = pd.DataFrame({"impactValue": [10.5, 20.5]}, index=[10, 11])

        # Match first with first, second with second
        id_match_ext = np.array([0, 1])
        id_match_lab = np.array([0, 1])

        result_ext, result_lab = find_match_value(ext_df, lab_df, id_match_ext, id_match_lab)

        np.testing.assert_array_equal(result_ext, np.array([0, 1]))
        np.testing.assert_array_equal(result_lab, np.array([0, 1]))

    def test_find_match_value_multiple_candidates(self):
        """Test finding match with multiple candidates"""
        ext_df = pd.DataFrame({"impactValue": [10.0]}, index=[0])
        lab_df = pd.DataFrame({"impactValue": [10.5, 11.0]}, index=[10, 11])

        id_match_ext = np.array([0, 0])
        id_match_lab = np.array([0, 1])

        result_ext, result_lab = find_match_value(ext_df, lab_df, id_match_ext, id_match_lab)

        # Should match with the closest value
        self.assertEqual(len(result_ext), 1)


class TestReindexMatch(unittest.TestCase):
    def test_reindex_match(self):
        """Test reindexing match back to original indices"""
        df = pd.DataFrame({
            "orig_index": [100, 101, 102, 103],
            "data": ["a", "b", "c", "d"]
        })
        id_match = np.array([0, 2, 3])

        result = reindex_match(id_match, df)
        expected = np.array([100, 102, 103])
        np.testing.assert_array_equal(result, expected)


class TestSplitNansSimMatrix(unittest.TestCase):
    def test_split_nans_sim_matrix_no_nans(self):
        """Test splitting sim matrix with no nans"""
        dist_mat = np.ones((3, 3, 2)) * 0.8
        nan_id_ext = []
        nan_id_lab = []

        mat_notna, mat_na = split_nans_sim_matrix(dist_mat, nan_id_ext, nan_id_lab)

        self.assertIsNotNone(mat_notna)
        self.assertIsNone(mat_na)

    def test_split_nans_sim_matrix_both_with_nans(self):
        """Test splitting sim matrix when both have nans"""
        dist_mat = np.ones((4, 4, 2)) * 0.8
        nan_id_ext = [0, 1]
        nan_id_lab = [0, 1]

        mat_notna, mat_na = split_nans_sim_matrix(dist_mat, nan_id_ext, nan_id_lab)

        self.assertIsNotNone(mat_notna)
        self.assertIsNotNone(mat_na)
        self.assertEqual(mat_notna.shape, (2, 2, 2))
        self.assertEqual(mat_na.shape, (2, 2, 2))


class TestMetricsFunctions(unittest.TestCase):
    def test_precision(self):
        """Test precision calculation"""
        result = precision(10, 15)
        self.assertAlmostEqual(result, 10/15, places=5)

    def test_precision_zero_denominator(self):
        """Test precision with zero denominator"""
        result = precision(10, 0)
        self.assertTrue(np.isnan(result))

    def test_recall(self):
        """Test recall calculation"""
        result = recall(10, 20)
        self.assertAlmostEqual(result, 10/20, places=5)

    def test_recall_zero_denominator(self):
        """Test recall with zero denominator"""
        result = recall(10, 0)
        self.assertTrue(np.isnan(result))

    def test_f1(self):
        """Test F1 score calculation"""
        p = 0.8
        r = 0.6
        result = f1(p, r)
        expected = 2 * p * r / (p + r)
        self.assertAlmostEqual(result, expected, places=5)

    def test_f1_zero_denominator(self):
        """Test F1 score with zero denominator"""
        result = f1(0, 0)
        self.assertTrue(np.isnan(result))

    def test_coverage(self):
        """Test coverage calculation"""
        result = coverage(10, 20)
        self.assertAlmostEqual(result, 50.0, places=5)

    def test_coverage_zero_denominator(self):
        """Test coverage with zero denominator"""
        result = coverage(10, 0)
        self.assertTrue(np.isnan(result))

    def test_false_negatives(self):
        """Test false negatives calculation"""
        result = false_negatives(20, 10)
        self.assertEqual(result, 10)

    def test_false_positives(self):
        """Test false positives calculation"""
        result = false_positives(20, 10)
        self.assertEqual(result, 10)

    def test_false_positives_negative(self):
        """Test false positives with more matches than extracted"""
        result = false_positives(10, 15)
        self.assertEqual(result, 0)


class TestBootstrapMetrics(unittest.TestCase):
    def test_precision_bt(self):
        """Test bootstrap precision"""
        result = precision_bt(10, 5)
        self.assertAlmostEqual(result, 10/15, places=5)

    def test_precision_bt_zero(self):
        """Test bootstrap precision with zero denominator"""
        result = precision_bt(0, 0)
        self.assertEqual(result, 0)

    def test_recall_bt(self):
        """Test bootstrap recall"""
        result = recall_bt(10, 5)
        self.assertAlmostEqual(result, 10/15, places=5)

    def test_recall_bt_zero(self):
        """Test bootstrap recall with zero denominator"""
        result = recall_bt(0, 0)
        self.assertEqual(result, 0)

    def test_f1_bt(self):
        """Test bootstrap F1 score"""
        result = f1_bt(10, 5, 5)
        # F1 = 2*TP / (2*TP + FP + FN) = 20 / 30 = 0.667
        self.assertAlmostEqual(result, 20/30, places=5)

    def test_f1_bt_zero(self):
        """Test bootstrap F1 score with zero values"""
        result = f1_bt(0, 0, 0)
        self.assertEqual(result, 0)

    def test_bootstrap_f1_output_format(self):
        """Test that bootstrap_f1 returns correct format"""
        result = bootstrap_f1(100, 50, 30, n_boot=100)

        self.assertIn("precision", result)
        self.assertIn("recall", result)
        self.assertIn("f1_score", result)

        for key in result:
            self.assertEqual(len(result[key]), 2)  # [lower, upper] bounds


class TestMakeMatchDict(unittest.TestCase):
    def test_make_match_dict(self):
        """Test creating match metrics dictionary"""
        metrics = {}
        result = make_match_dict(20, 30, 15, "quanti", metrics)

        self.assertEqual(result["nb labelled"], 30)
        self.assertEqual(result["nb extracted"], 20)
        self.assertEqual(result["true_positives"], 15)
        self.assertEqual(result["false_negatives"], 15)
        self.assertEqual(result["false_positives"], 5)
        self.assertAlmostEqual(result["precision"], 15/20, places=5)
        self.assertAlmostEqual(result["recall"], 15/30, places=5)
        self.assertEqual(result["quanti"], "quanti")


class TestTruePositives(unittest.TestCase):
    def test_true_positives(self):
        """Test counting true positives"""
        matched_df = pd.DataFrame({
            "lab_match_id_sim": [1, 1, 2, 2, 3]
        })
        result = true_positives(matched_df)
        self.assertEqual(result, 3)  # 3 unique labelled ids


class TestMatchRows(unittest.TestCase):
    """Test match_rows function with proper column tracking"""

    def setUp(self):
        """Set up test data for matching"""
        # Create simple test dataframes
        self.ext_df = pd.DataFrame({
            "orig_index": [0, 1],
            "hazards": [["flood"], ["storm"]],
            "iso3_code": [["USA"], ["USA"]],
            "impactValue": [100.0, 200.0],
            "impactSubtype": ["Affected People", "Affected People"]
        })

        self.lab_df = pd.DataFrame({
            "orig_index": [10, 11],
            "hazards": [["flood"], ["storm"]],
            "iso3_code": [["USA"], ["USA"]],
            "impactValue": [105.0, 195.0],
            "impactSubtype": ["Affected People", "Affected People"]
        })

        # Create vectorized dataframes
        unique_hazards = ["flood", "storm"]
        unique_iso3 = ["USA", "FRA"]
        unique_subtype = ["Affected People", "Deaths"]

        self.ext_vec = pd.DataFrame({
            "hazards": [self.vectorize_test(h, unique_hazards) for h in self.ext_df["hazards"]],
            "iso3_code": [self.vectorize_test(i, unique_iso3) for i in self.ext_df["iso3_code"]],
            "impactSubtype": [self.vectorize_test(s, unique_subtype) for s in self.ext_df["impactSubtype"]]
        })

        self.lab_vec = pd.DataFrame({
            "hazards": [self.vectorize_test(h, unique_hazards) for h in self.lab_df["hazards"]],
            "iso3_code": [self.vectorize_test(i, unique_iso3) for i in self.lab_df["iso3_code"]],
            "impactSubtype": [self.vectorize_test(s, unique_subtype) for s in self.lab_df["impactSubtype"]]
        })

        self.similarity_cols = ["hazards", "iso3_code", "impactSubtype"]
        self.matching_cols = ["hazards", "iso3_code", "impactSubtype"]

        self.weights = {
            "hazards": 1.0,
            "iso3_code": 1.0,
            "impactSubtype": 1.0,
            "geometry": 0,
            "impactValue": 0
        }

    def vectorize_test(self, cell_values, unique_values):
        """Helper to vectorize for tests"""
        cell_values = [cell_values] if not isinstance(cell_values, list) else cell_values
        vector = [1 if unique_value in cell_values else 0 for unique_value in unique_values]
        return np.array(vector)

    def test_match_rows_basic(self):
        """Test basic row matching"""
        reid_ext, reid_lab, accuracy_matrix = match_rows(
            self.ext_df, self.lab_df, self.ext_vec, self.lab_vec,
            self.matching_cols, self.similarity_cols, self.weights,
            geo_match=False, value_match=None
        )

        # Should return match indices and accuracy matrix
        self.assertEqual(len(reid_ext), len(reid_lab))
        self.assertIsNotNone(accuracy_matrix)
        # accuracy_matrix should have shape (n_matches, n_cols in similarity_cols)
        self.assertEqual(accuracy_matrix.shape[1], len(self.similarity_cols))

    def test_match_rows_with_value_match_pre(self):
        """Test match_rows with value_match='pre'"""
        reid_ext, reid_lab, accuracy_matrix = match_rows(
            self.ext_df, self.lab_df, self.ext_vec, self.lab_vec,
            self.matching_cols + ["impactValue"], self.similarity_cols, self.weights,
            geo_match=False, value_match="pre"
        )

        # accuracy_matrix should now include impactValue column
        # Shape should be (n_matches, n_similarity_cols + 1 for impactValue)
        self.assertEqual(accuracy_matrix.shape[1], len(self.similarity_cols) + 1)

    def test_match_rows_similarity_cols_subset_of_matching(self):
        """Test that similarity_cols is validated as subset of matching_cols"""
        # This should work fine
        reid_ext, reid_lab, accuracy_matrix = match_rows(
            self.ext_df, self.lab_df, self.ext_vec, self.lab_vec,
            self.matching_cols, self.similarity_cols, self.weights,
            geo_match=False, value_match=None
        )
        self.assertIsNotNone(accuracy_matrix)

    def test_match_rows_similarity_cols_not_subset(self):
        """Test that error is raised if similarity_cols has cols not in matching_cols"""
        invalid_similarity_cols = ["hazards", "iso3_code", "invalid_col"]

        with self.assertRaises(ValueError) as context:
            match_rows(
                self.ext_df, self.lab_df, self.ext_vec, self.lab_vec,
                self.matching_cols, invalid_similarity_cols, self.weights,
                geo_match=False, value_match=None
            )
        self.assertIn("must be in matching_cols", str(context.exception))

    def test_match_rows_dist_mat_column_tracking(self):
        """Test that dist_mat columns are properly tracked"""
        # When value_match='pre', impactValue should be added to dist_mat_cols
        reid_ext, reid_lab, accuracy_matrix = match_rows(
            self.ext_df, self.lab_df, self.ext_vec, self.lab_vec,
            self.matching_cols + ["impactValue"], self.similarity_cols, self.weights,
            geo_match=False, value_match="pre"
        )

        # Should return without error about dimension mismatch
        self.assertIsNotNone(accuracy_matrix)
        # Dimensions should be properly aligned
        self.assertEqual(len(reid_ext), len(reid_lab))



if __name__ == "__main__":
    unittest.main()
