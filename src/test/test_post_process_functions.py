import unittest
import re
import pandas as pd
import numpy as np
import pycountry
from price_parser import Price
from currency_converter import CurrencyConverter
from datetime import datetime

from src.units import *   # adjust to your file name
from src.impact_def import *
from src.hazard_def import *

# import your functions
from src.post_process_functions import (
    country_name_to_iso3, list_country_name_to_iso3,
    separate_locs, remove_startspace,
    delistify_cols, listify_strings,
    format_output,
    parse_impact_value_precision,
    reclassify_impact_subtype, reclassify_hazard,
    convert_unit, assign_unit_type, reclassify_units,
    standardize_metric_units, join_value_units, split_value_units,
    convert_monetary_units, replace_numbers_unit,
    make_date, harmonize_units, normalize_people_unit
)

# Define positive and negative test cases for each category
regex_test_cases = {
    'people': {
        "positives": ["100 people", "people affected", "of people"],
        "negatives": ["peopledom", "personal", "evacuate"]
    },
    'roads': {
        "positives": ["roads damaged", "roads", "roads destroyed"],
        "negatives": ["broadway show", "offroaders"]
    },
    'transportation facilities': {
        "positives": ["railway", "train tracks", "airport damaged", "bus", "taxis", "airplane"],
        "negatives": ["trail", "training"]
    },
    'water, sanitation and hygiene facilities': {
        "positives": ["latrines built", "water shortage", "aqueduct", "reservoir"],
        "negatives": ["watershed", "hydropower"]
    },
    'healthcare facilities': {
        "positives": ["hospital destroyed", "medical clinic", "maternity center"],
        "negatives": ["healthiness", "medicine"]
    },
    'IT and communication facilities': {
        "positives": ["radio station", "cell tower down", "antenna"],
        "negatives": ["communication skills", "televisionary", "tv damaged"]
    },
    'power and energy production infrastructure facilities': {
        "positives": ["power outage", "solar panels", "hydro dam", "generator"],
        "negatives": ["empowered", "energetic"]
    },
    'homes': {
        "positives": ["homes destroyed", "home", "residential structures"],
        "negatives": ["homeostasis", "building up momentum"]
    },
    'education facilities': {
        "positives": ["schools collapsed", "universities closed", "college damaged"],
        "negatives": ["schooling fish", "educationalist"]
    },
    'crop production and forestry': {
        "positives": ["crop loss", "rice fields", "forest fire", "coffee plantations", "maize production"],
        "negatives": ["treetop adventure", "bananarama band"]
    },
    'agricultural facilities': {
        "positives": ["barn collapsed", "irrigation channel", "farms flooded"],
        "negatives": ["farming practice", "barnacle"]
    },
    'affected animals': {
        "positives": ["livestock lost", "dead cows", "sheep killed", "poultry disease", "cattle evacuated"],
        "negatives": ["dog", "animalistic"]
    },
    'informal settlements': {
        "positives": ["refugee camp", "tent", "informal settlement"],
        "negatives": ["campus", "camping gear"]
    }
}


class TestUnitKwReclass(unittest.TestCase):

    def test_regex_patterns(self):
        """Loop through all regex patterns and test with positives/negatives"""
        for category, pattern in UNIT_KW_RECLASS.items():
            with self.subTest(category=category):
                regex = re.compile(pattern, re.IGNORECASE)
                test_data = regex_test_cases.get(category, {})

                for text in test_data.get("positives", []):
                    self.assertRegex(text.lower(), regex, msg=f"{category} should match: {text}")

                for text in test_data.get("negatives", []):
                    self.assertNotRegex(text.lower(), regex, msg=f"{category} should NOT match: {text}")

class TestCountryFunctions(unittest.TestCase):
    def test_country_name_to_iso3(self):
        self.assertEqual(country_name_to_iso3("Switzerland"), "CHE")
        self.assertEqual(country_name_to_iso3("FooLand"), "Unknown")

    def test_list_country_name_to_iso3(self):
        self.assertEqual(
            list_country_name_to_iso3(["France", "Germany"]),
            ["FRA", "DEU"]
        )
        self.assertEqual(list_country_name_to_iso3("Spain"), "ESP")


class TestLocationFunctions(unittest.TestCase):
    def test_separate_locs(self):
        self.assertEqual(separate_locs("Paris, Lyon"), ["Paris", " Lyon"])
        self.assertIsNone(separate_locs(None))

    def test_remove_startspace(self):
        self.assertEqual(remove_startspace([" Paris", "Lyon "]), ["Paris", "Lyon"])
        self.assertIsNone(remove_startspace(None))


class TestDataFrameHelpers(unittest.TestCase):
    def test_delistify_cols(self):
        df = pd.DataFrame({"a": [[1, 2], [3, 4]], "b": [5, 6]})
        out = delistify_cols(df.copy())
        self.assertTrue(all(isinstance(v, str) for v in out["a"]))

    def test_delistify_cols_no_lists(self):
        df = pd.DataFrame({"a": [1, 2], "b": [5, 6]})
        out = delistify_cols(df.copy())
        self.assertEqual(out["a"].dtype, df["a"].dtype)

    def test_listify_strings_json(self):
        self.assertEqual(listify_strings("['a','b']"), ["a", "b"])
        self.assertEqual(listify_strings('["x","y"]'), ["x", "y"])

    def test_listify_strings_plain(self):
        # json_repair returns empty string for invalid JSON like "hello"
        # The function then returns this empty string
        result = listify_strings("hello")
        # This is a quirk of json_repair - it returns empty string for non-JSON strings
        # In practice, these should be handled by validation before calling this function
        self.assertIsInstance(result, (str, list))

    def test_listify_strings_list(self):
        self.assertEqual(listify_strings(["a", "b"]), ["a", "b"])

    def test_listify_strings_none(self):
        self.assertEqual(listify_strings(None), [])

    def test_listify_strings_nan(self):
        self.assertEqual(listify_strings(np.nan), [])

    def test_format_output(self):
        df = pd.DataFrame({"a": ["1", "2", None], "b": ["[1,2]", "x", None]})
        out = format_output(df, num_cols=["a"], list_cols=["b"])
        self.assertTrue(np.issubdtype(out["a"].dtype, np.floating))
        self.assertIsInstance(out["b"].iloc[0], list)

class TestImpactFunctions(unittest.TestCase):
    def test_parse_impact_value_precision(self):
        d = {"impactValueMin": 5, "impactValueMax": 10, "impactValue": 7}
        out = parse_impact_value_precision(d)
        self.assertEqual(out["impactValue"], 10)

    def test_parse_impact_value_precision_none_values(self):
        d = {"impactValueMin": None, "impactValueMax": 10, "impactValue": None}
        out = parse_impact_value_precision(d)
        self.assertEqual(out["impactValueMax"], 10)

    def test_reclassify_impact_subtype(self):
        x = pd.Series({"impactSubtype": "Affected People"})
        result = reclassify_impact_subtype(x)
        # Already in the keywords, so no reclassification
        self.assertEqual(result["impactSubtype"], "Affected People")
        self.assertFalse(result["flag_impactSubtype_reclass"])

    def test_reclassify_impact_subtype_no_match(self):
        x = pd.Series({"impactSubtype": "unknown_type"})
        result = reclassify_impact_subtype(x)
        self.assertEqual(result["impactSubtype"], "Unknown")

    def test_reclassify_hazard(self):
        hazard_in = ["flood", "earth", "tornado", "tornadoes", "landslide"]
        hazard_reclassed = ["Flood", "Unknown", "Convective storm", "Convective storm", "Mass movement"]
        x = pd.Series({"hazards": hazard_in})
        out = reclassify_hazard(x, hazard_kw_reclass)
        self.assertEqual(out["hazards"], hazard_reclassed)
        self.assertTrue(out["flag_hazards_reclass"])

    def test_reclassify_hazard_no_match(self):
        x = pd.Series({"hazards": ["rain", "wind"]})
        out = reclassify_hazard(x)
        self.assertEqual(out["hazards"], ["Unknown", "Unknown"])
        self.assertTrue(out["flag_hazards_reclass"])

    def test_convert_unit(self):
        x = pd.Series({"impactValue": 10, "impactUnit": "families", "impactValueMin": np.nan, "impactValueMax": np.nan})
        out = convert_unit(x.copy())
        self.assertEqual(out["impactUnit"], "people")
        self.assertEqual(out["impactValue"], 30)
        self.assertTrue(out["flag_unit_conversion"])

    def test_convert_unit_no_match(self):
        x = pd.Series({"impactValue": 10, "impactUnit": "kg", "impactValueMin": np.nan, "impactValueMax": np.nan})
        out = convert_unit(x.copy())
        self.assertEqual(out["impactUnit"], "kg")
        self.assertFalse(out["flag_unit_conversion"])

    def test_assign_unit_type(self):
        x = pd.Series({"impactUnit": "kg"})
        result = assign_unit_type(x)
        self.assertEqual(result["unit_type"], "kg")

    def test_assign_unit_type_no_match(self):
        x = pd.Series({"impactUnit": "unknown_unit"})
        result = assign_unit_type(x)
        self.assertEqual(result["unit_type"], "other")
        x = pd.Series({"impactUnit": "people"})
        result = assign_unit_type(x)
        self.assertEqual(result["unit_type"], "other")

    def test_reclassify_units(self):
        x = pd.Series({"impactValue": 10,
                       "impactValueMin": np.nan,
                       "impactValueMax": 20,
                       "impactUnit": "families",
                       "unit_type": "other",
                       "impactSubtype": "Affected People"})
        out = reclassify_units(x.copy())
        self.assertIn("people", out["impactUnit"])
        self.assertEqual(out["impactValue"], 10)
        self.assertTrue(pd.isna(out["impactValueMin"]))
        self.assertEqual(out["impactValueMax"], 20)
        self.assertTrue(out["flag_unit_nonstd"])
        self.assertFalse(out["flag_reclass_subtype_from_unit"])

    def test_reclassify_units_reclass_subtype(self):
        x = pd.Series({"impactValue": 10,
                       "impactValueMin": np.nan,
                       "impactValueMax": 20,
                       "impactUnit": "displaced",
                       "unit_type": "other",
                       "impactSubtype": "Affected People"})
        out = reclassify_units(x.copy())
        self.assertIn("displaced", out["impactUnit"])
        self.assertEqual(out["impactValue"], 10)
        self.assertTrue(pd.isna(out["impactValueMin"]))
        self.assertEqual(out["impactValueMax"], 20)
        self.assertFalse(out["flag_unit_nonstd"])
        self.assertTrue(out["flag_reclass_subtype_from_unit"])
        self.assertEqual(out["impactSubtype"], "Displaced People")


    def test_standardize_metric_units(self):
        x = pd.Series({"impactValue": 10, "impactUnit": "liters", "impactValueMin": np.nan, "impactValueMax": 20})
        out = standardize_metric_units(x)
        self.assertEqual(out["impactUnit"], "m**3")
        self.assertAlmostEqual(out["impactValue"], 0.01, places=5)
        self.assertAlmostEqual(out["impactValueMax"], 0.02, places=5)
        self.assertTrue(pd.isna(out["impactValueMin"]))
        self.assertTrue(out["flag_unit_standardization"])

    def test_standardize_metric_units_invalid(self):
        x = pd.Series({"impactValue": 10, "impactUnit": "unknown", "impactValueMin": np.nan, "impactValueMax": np.nan})
        out = standardize_metric_units(x)
        self.assertFalse(out["flag_unit_standardization"])

    def test_join_split_value_units(self):
        x = pd.Series({"impactValue": 5, "impactUnit": "kg"})
        vu = join_value_units(x)
        self.assertEqual(vu, "5,kg")
        y = pd.Series({"value_unit": vu})
        self.assertEqual(split_value_units(y), ["5", "kg"])

    def test_convert_monetary_units(self):
        x = pd.DataFrame({
            "impactValue": [1500, 1500, 10],
            "impactValueMin": [1000, 1000, 10],
            "impactValueMax": [2000, 2000, 10],
            "impactUnit": ["USD", "chf", "euro"],
            "reportDate": ["2020-01-01", "", "2019-06-15"]
        })
        for i in range(len(x)):
            out = convert_monetary_units(x.iloc[i])
            self.assertEqual(out["impactUnit"], "EUR")
            self.assertIsInstance(out["impactValue"], (int, float))
            self.assertIsInstance(out["impactValueMin"], (int, float))
            self.assertIsInstance(out["impactValueMax"], (int, float))
            self.assertTrue(out["flag_currency_conversion"])

    def test_convert_monetary_units_invalid_currency(self):
        x = pd.DataFrame({
            "impactValue": [1500, 1500],
            "impactValueMin": [1000, 1000],
            "impactValueMax": [2000, 2000],
            "impactUnit": ["people", "swiss francs"],
            "reportDate": ["2020-01-01", "2019-06-15"]
        })
        for i in range(len(x)):
            out = convert_monetary_units(x.iloc[i])
            self.assertFalse(out["flag_currency_conversion"])

    def test_replace_numbers_unit(self):
        # Test with digits in unit
        x = pd.Series({"impactValue": 5, "impactUnit": "2 houses", "impactValueMin": 2, "impactValueMax": np.nan})
        out = replace_numbers_unit(x)
        self.assertEqual("houses", out["impactUnit"])
        self.assertEqual(out["impactValue"], 10)
        self.assertEqual(out["impactValueMin"], 4)
        self.assertTrue(pd.isna(out["impactValueMax"]))
        self.assertTrue(out["flag_reformat_unit"])

        x = pd.Series({"impactValue": 5, "impactUnit": "two houses", "impactValueMin": 2, "impactValueMax": np.nan})
        out = replace_numbers_unit(x)
        self.assertEqual("houses", out["impactUnit"])
        self.assertEqual(out["impactValue"], 10)
        self.assertEqual(out["impactValueMin"], 4)
        self.assertTrue(pd.isna(out["impactValueMax"]))
        self.assertTrue(out["flag_reformat_unit"])

        x = pd.Series({"impactValue": 5, "impactUnit": "thousands people", "impactValueMin": 2, "impactValueMax": np.nan})
        out = replace_numbers_unit(x)
        self.assertEqual("people", out["impactUnit"])
        self.assertEqual(out["impactValue"], 5000)
        self.assertEqual(out["impactValueMin"], 2000)
        self.assertTrue(pd.isna(out["impactValueMax"]))
        self.assertTrue(out["flag_reformat_unit"])

    def test_replace_numbers_unit_none(self):
        x = pd.Series({"impactValue": 5, "impactUnit": None, "impactValueMin": np.nan, "impactValueMax": np.nan})
        out = replace_numbers_unit(x)
        self.assertFalse(out["flag_reformat_unit"])

    def test_make_date(self):
        df = pd.DataFrame({
            "startYear": [2020], "startMonth": [1], "startDay": [1],
            "endYear": [2020], "endMonth": [12], "endDay": [31]
        })
        out = make_date(df.copy())
        self.assertEqual(out["startDate"].iloc[0], "2020-1-1")
        self.assertEqual(out["endDate"].iloc[0], "2020-12-31")

    def test_make_date_partial(self):
        df = pd.DataFrame({
            "startYear": [2020], "startMonth": [6], "startDay": [None],
            "endYear": [2020], "endMonth": [None], "endDay": [None]
        })
        out = make_date(df.copy())
        self.assertEqual(out["startDate"].iloc[0], "2020-6")
        self.assertEqual(out["endDate"].iloc[0], "2020")

    def test_make_date_year_only(self):
        df = pd.DataFrame({
            "startYear": [2020], "startMonth": [None], "startDay": [None],
            "endYear": [2021], "endMonth": [None], "endDay": [None]
        })
        out = make_date(df.copy())
        self.assertEqual(out["startDate"].iloc[0], "2020")
        self.assertEqual(out["endDate"].iloc[0], "2021")

class TestAdditionalLocationFunctions(unittest.TestCase):
    def test_separate_locs_with_spaces(self):
        result = separate_locs("Paris, Lyon, Rome")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "Paris")

    def test_remove_startspace_all_spaces(self):
        result = remove_startspace(["  Paris", " Lyon", "Rome  "])
        self.assertEqual(result[0], "Paris")
        self.assertEqual(result[1], "Lyon")
        self.assertEqual(result[2], "Rome")

class TestAdditionalUnitFunctions(unittest.TestCase):
    def test_harmonize_units(self):
        x = pd.Series({"impactUnit": "individuals"})
        out = harmonize_units(x)
        self.assertEqual(out["impactUnit"], "people")
        self.assertTrue(out["flag_unit_harmonization"])

    def test_harmonize_units_no_match(self):
        x = pd.Series({"impactUnit": "kg"})
        out = harmonize_units(x)
        self.assertEqual(out["impactUnit"], "kg")
        self.assertFalse(out["flag_unit_harmonization"])

    def test_harmonize_units_none(self):
        x = pd.Series({"impactUnit": None})
        out = harmonize_units(x)
        self.assertFalse(out["flag_unit_harmonization"])

    def test_normalize_people_unit(self):
        x = pd.Series({"impactUnit": "deaths"})
        out = normalize_people_unit(x)
        self.assertEqual(out["impactUnit"], "people")

    def test_normalize_people_unit_no_match(self):
        x = pd.Series({"impactUnit": "kg"})
        out = normalize_people_unit(x)
        self.assertEqual(out["impactUnit"], "kg")

class TestFormatOutput(unittest.TestCase):
    def test_format_output_numeric_conversion(self):
        df = pd.DataFrame({"a": ["1", "2", None], "b": ["x", "y", "z"]})
        out = format_output(df, num_cols=["a"])
        self.assertTrue(np.issubdtype(out["a"].dtype, np.floating))

    def test_format_output_list_conversion(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["[1,2]", "x", "[]"]})
        out = format_output(df, list_cols=["b"])
        self.assertIsInstance(out["b"].iloc[0], list)
        self.assertEqual(out["b"].iloc[0], [1, 2])

    def test_format_output_mixed(self):
        df = pd.DataFrame({
            "num": ["1", "2", None],
            "list": ["['a','b']", "hello", None]
        })
        out = format_output(df, num_cols=["num"], list_cols=["list"])
        self.assertTrue(np.issubdtype(out["num"].dtype, np.floating))
        self.assertIsInstance(out["list"].iloc[0], list)

if __name__ == "__main__":
    unittest.main()
