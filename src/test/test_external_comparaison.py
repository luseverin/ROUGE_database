import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from shapely.geometry import Point, Polygon
import sys, os
from datetime import datetime, timedelta
from types import SimpleNamespace

from src.external_comparaison import (
    consolidate_impact_value,
    consolidate_startYear,
    add_location_admin_num,
    group_quanti_country_level,
    clean_group,
    clean_impact_values,
    ifrc_go_impact_source,
    mapping_impact_type,
    open_clean_ifrc_monty, 
    mapping_impact_type, 
    open_emdat, 
    choose_unique_disno, 
    matching_emdat
)

class TestExternalFunctions(unittest.TestCase):
    def test_consolidate_impact_value_priority(self):
        df = pd.DataFrame({
            "impactValue": [10, np.nan, np.nan],
            "impactValueMin": [np.nan, 5, np.nan],
            "impactValueMax": [np.nan, np.nan, 20],
        })

        result = consolidate_impact_value(df)
        self.assertListEqual(
            result["impactValue_final"].tolist(),
            [10, 5, 20]
        )

    def test_consolidate_impact_value_drop_all_nan(self):
        df = pd.DataFrame({
            "impactValue": [np.nan],
            "impactValueMin": [np.nan],
            "impactValueMax": [np.nan],
        })

        result = consolidate_impact_value(df)
        self.assertTrue(result.empty)
        
    def test_consolidate_startYear_missing(self):
        row = pd.Series({
            "startYear": np.nan,
            "reportDate": "2022-05-01"
        })

        year = consolidate_startYear(row)
        self.assertEqual(year, 2022)

    def test_consolidate_startYear_existing(self):
        row = pd.Series({
            "startYear": 2019,
            "reportDate": "2022-05-01"
        })

        year = consolidate_startYear(row)
        self.assertEqual(year, 2019)

    def test_add_location_admin_num(self):
        df = pd.DataFrame({
            "locationLowestAdmin": ["ADM_0", "ADM_1", "ADM_2"]
        })

        result = add_location_admin_num(df)
        self.assertListEqual(
            result["locationLowestAdminNum"].tolist(),
            [0.0, 1.0, 2.0]
        )

    @patch("src.external_comparaison.unary_union")
    def test_group_quanti_country_level_admin0(self, mock_unary_union):
        mock_unary_union.return_value = "UNION_GEOM"

        df = pd.DataFrame({
            "appealCode": ["A1", "A1"],
            "impactSubtype": ["Human Deaths", "Human Deaths"],
            "impactValue_final": [10, 5],
            "locationLowestAdminNum": [0, 0],
            "country": ["France", "France"],
            "geometry": [Point(0, 0), Point(1, 1)],
        })

        result = group_quanti_country_level(df)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["impactValue_final"], 10)  # max for ADM0
        self.assertEqual(result.iloc[0]["country"], "France")
        self.assertEqual(result.iloc[0]["geometry"], "UNION_GEOM")

    @patch("src.external_comparaison.unary_union")
    def test_group_quanti_country_level_admin0_polygon(self, mock_unary_union):
        mock_unary_union.return_value = "UNION_POLYGON"

        poly1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        poly2 = Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])

        df = pd.DataFrame({
            "appealCode": ["A1", "A1"],
            "impactSubtype": ["Human Deaths", "Human Deaths"],
            "impactValue_final": [10, 5],
            "locationLowestAdminNum": [0, 0],
            "country": ["France", "France"],
            "geometry": [poly1, poly2],
        })

        result = group_quanti_country_level(df)

        # basic assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["impactValue_final"], 10)
        self.assertEqual(result.iloc[0]["country"], "France")
        self.assertEqual(result.iloc[0]["geometry"], "UNION_POLYGON")

        # optional: ensure unary_union was called correctly
        mock_unary_union.assert_called_once()
        args, _ = mock_unary_union.call_args
        self.assertEqual(args[0], [poly1, poly2])

    def test_group_quanti_country_level_admin1_sum(self):
        df = pd.DataFrame({
            "appealCode": ["A1", "A1"],
            "impactSubtype": ["Affected People", "Affected People"],
            "impactValue_final": [100, 50],
            "locationLowestAdminNum": [1, 1],
            "country": ["Italy", "Italy"],
        })

        result = group_quanti_country_level(df, ADM_min=1)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["impactValue_final"], 150)

class TestIFRCGo(unittest.TestCase):
    def test_clean_group_pipeline(self):
        df = pd.DataFrame({
            "appealCode": ["A1"],
            "impactSubtype": ["Human Deaths"],
            "impactValue": [np.nan],
            "impactValueMin": [5],
            "impactValueMax": [10],
            "locationLowestAdmin": ["ADM_0"],
            "reportDate": ["2021-01-01"],
            "startYear": [np.nan],
            "country": ["Spain"],
        })

        result = clean_group(df)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["impactValue_final"], 5)
        self.assertEqual(result.iloc[0]["startYear"], 2021)

    def test_clean_impact_values_ifrc_go(self):
        row = pd.Series({
            "field_reports_num_dead": 12,
            "field_reports_gov_num_dead": np.nan,
            "field_reports_other_num_dead": np.nan,
        })

        result = clean_impact_values(row)

        self.assertEqual(result["Human Deaths"], 12)
        self.assertEqual(result["Human Deaths Source"], "report")

    def test_clean_impact_values_priority_order(self):
        row = pd.Series({
            "field_reports_num_affected": np.nan,
            "field_reports_gov_num_affected": 100,
            "field_reports_other_num_affected": 200,
        })

        result = clean_impact_values(row)

        self.assertEqual(result["Affected People"], 100)
        self.assertEqual(result["Affected People Source"], "gov")

class TestIFRCMonty(unittest.TestCase):
    @patch("src.external_comparaison.pd.read_csv")
    def test_open_clean_ifrc_monty_basic(self, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame({
            "id": ["ifrcevent-impact--123-xyz"],
            "impact_type": ["death"]
        })

        df_ifrc_go = pd.DataFrame({
            "id": [123],
            "appealCode": ["A1"]
        })

        result = open_clean_ifrc_monty(df_ifrc_go)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["appealCode"], "A1")
        self.assertEqual(result.iloc[0]["impact_type"], "Human Deaths")

class TestEmdatOpen(unittest.TestCase):
    @patch("src.external_comparaison.pd.read_excel")
    def test_open_emdat_dates(self, mock_read_excel):
        mock_read_excel.return_value = pd.DataFrame({
            "Disaster Type": ["Storm"],
            "Start Year": [2020],
            "Start Month": [None],
            "Start Day": [None],
            "End Year": [2020],
            "End Month": [None],
            "End Day": [None],
        })

        with patch("src.external_comparaison.hazard_mapping_emdat", {"Storm": "Storm"}):
            df = open_emdat("dummy.xlsx")

        self.assertIn("Start Date", df.columns)
        self.assertEqual(df.iloc[0]["Start Date"], pd.Timestamp("2020-01-01"))

class TestEmdatMatching(unittest.TestCase):
    def test_single_disno(self):
        df = pd.DataFrame({
            "DisNo.": ["2020-001"]
        })

        result = choose_unique_disno(df, "date_diff_mean")
        self.assertEqual(result, "2020-001")

    def test_multiple_disno_frequency_then_minimize(self):
        df = pd.DataFrame({
            "DisNo.": ["A", "A", "B", "B"],
            "date_diff_mean": [10, 2, 2, 20]
        })

        result = choose_unique_disno(df, "date_diff_mean")
        self.assertEqual(result, "A")

    @patch("src.external_comparaison.reclassify_hazard_emdat")
    @patch("src.external_comparaison.reverse_mapping")
    def test_matching_emdat_basic(
        self, mock_reverse_mapping, mock_reclassify
    ):
        mock_reverse_mapping.return_value = {}
        mock_reclassify.return_value = ["Storm"]

        df_llm = pd.DataFrame({
            "appealCode": ["A1"],
            "hazards": ["storm"],
            "country": [["France"]],
            "startYear": [2020],
            "startMonth": [1],
            "startDay": [1],
            "endYear": [2020],
            "endMonth": [1],
            "endDay": [10],
        })

        df_emdat = pd.DataFrame({
            "DisNo.": ["2020-001"],
            "Country": ["France"],
            "Disaster Type": ["Storm"],
            "Start Year": [2020],
            "Start Month": [1],
            "Start Day": [1],
            "End Year": [2020],
            "End Month": [1],
            "End Day": [10],
        })

        matched, candidates = matching_emdat(
            df_llm,
            df_emdat,
            date_diff_th=timedelta(days=30),
            column_minimize="date_diff_mean"
        )

        self.assertIn("chosen_DisNo", matched.columns)
        self.assertEqual(matched.iloc[0]["chosen_DisNo"], "2020-001")
        self.assertFalse(candidates.empty)

if __name__ == "__main__":
    unittest.main()
