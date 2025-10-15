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
    make_date
)

# Define positive and negative test cases for each category
regex_test_cases = {
    'people': {
        "positives": ["100 people", "1 person", "50 individuals", "200 evacuees"],
        "negatives": ["peopledom", "personal", "evacuate"]
    },
    'roads': {
        "positives": ["the road", "bridges collapsed", "new highways", "motorway"],
        "negatives": ["broadway show", "offroaders"]
    },
    'transportation facilities': {
        "positives": ["railway", "train tracks", "airport damaged", "bus", "taxis"],
        "negatives": ["trail", "training", "airplane"]
    },
    'water, sanitation and hygiene facilities': {
        "positives": ["latrines built", "water shortage", "new aqueduct", "reservoir"],
        "negatives": ["watershed", "hydropower"]
    },
    'healthcare facilities': {
        "positives": ["hospital destroyed", "medical clinic", "maternity center"],
        "negatives": ["healthiness", "medicine"]
    },
    'IT and communication facilities': {
        "positives": ["radio station", "tv damaged", "cell tower down", "antenna"],
        "negatives": ["communication skills", "televisionary"]
    },
    'power and energy production infrastructure facilities': {
        "positives": ["power outage", "solar panels", "hydro dam", "generator"],
        "negatives": ["empowered", "energetic"]
    },
    'homes': {
        "positives": ["homes destroyed", "residential building", "houses", "residence"],
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
        "positives": ["refugee camp", "tents destroyed", "informal settlement"],
        "negatives": ["campus", "settlement agreement"]
    }
}


class TestUnitKwReclass(unittest.TestCase):

    def test_regex_patterns(self):
        """Loop through all regex patterns and test with positives/negatives"""
        for category, pattern in unit_kw_reclass.items():
            with self.subTest(category=category):
                regex = re.compile(pattern, re.IGNORECASE)
                test_data = regex_test_cases.get(category, {})

                for text in test_data.get("positives", []):
                    self.assertRegex(text.lower(), regex, msg=f"{category} should match: {text}")

                for text in test_data.get("negatives", []):
                    self.assertNotRegex(text.lower(), regex, msg=f"{category} should NOT match: {text}")

# Example dummy mappings for unit functions
#unit_converter = {"families": (5, "people")}
#unit_type_kw_reclass = {"mass": r"kg|kilogram", "area": r"hectare", "other": r".*"}
#unit_kw_reclass = {"people": r"people|families"}
#default_subtype_unit = {"Affected People": "people"}
#expected_unit_subtype = {"Affected People": "people"}
#std_unit_kw_reclass = {"kg": [r"kg", r"kilograms?"]}
#unit_mapping = {"kg": "kg"}


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

    def test_listify_strings(self):
        self.assertEqual(listify_strings("['a','b']"), ["a", "b"])
        self.assertEqual(listify_strings("hello"), ["hello"])
        self.assertEqual(listify_strings(["a", "b"]), ["a", "b"])
        self.assertEqual(listify_strings(None), [])

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

    def test_reclassify_impact_subtype(self):
        x = pd.Series({"impactSubtype": "families"})
        result = reclassify_impact_subtype(x, ["people"], {"people": r"families"})
        self.assertEqual(result, "people")

    def test_reclassify_hazard(self):
        x = pd.Series({"hazards": ["flood", "earth"]})
        hazard_kw_reclass = {"Flood": r"flood", "Earthquake": r"earth"}
        out = reclassify_hazard(x, hazard_kw_reclass)
        self.assertEqual(out, ["Flood", "Earthquake"])

    def test_convert_unit(self):
        x = pd.Series({"impactValue": 10, "impactUnit": "families"})
        out = convert_unit(x.copy(), unit_converter)
        self.assertEqual(out["impactUnit"], "people")
        self.assertEqual(out["impactValue"], 30)

    def test_assign_unit_type(self):
        x = pd.Series({"impactUnit": "kg"})
        self.assertEqual(assign_unit_type(x, unit_type_kw_reclass), "mass")

    def test_reclassify_units(self):
        x = pd.Series({"impactUnit": "families", "unit_type": "other", "impactSubtype": "Affected People"})
        out = reclassify_units(x.copy(), unit_kw_reclass, default_subtype_unit)
        self.assertIn("people", out)

    def test_standardize_metric_units(self):
        x = pd.Series({"impactValue": 10, "impactUnit": "kg"})
        out = standardize_metric_units(x, std_unit_kw_reclass, unit_mapping)
        self.assertEqual(out["impactUnit"], "kg")

    def test_join_split_value_units(self):
        x = pd.Series({"impactValue": 5, "impactUnit": "kg"})
        vu = join_value_units(x)
        self.assertEqual(vu, "5,kg")
        y = pd.Series({"value_unit": vu})
        self.assertEqual(split_value_units(y), ["5", "kg"])

    def test_convert_monetary_units(self):
        x = pd.Series({"impactValue": 1500, "impactUnit": "USD", "reportDate": "2020-01-01"})
        out = convert_monetary_units(x)
        self.assertEqual(out["impactUnit"], "EUR")

    def test_replace_numbers_unit(self):
        # For speed, test with digits not words to avoid loading spacy
        x = pd.Series({"impactValue": 5, "impactUnit": "2 houses"})
        out = replace_numbers_unit(x)
        self.assertTrue("houses" in out["impactUnit"])

    def test_make_date(self):
        df = pd.DataFrame({
            "startYear": [2020], "startMonth": [1], "startDay": [1],
            "endYear": [2020], "endMonth": [12], "endDay": [31]
        })
        out = make_date(df.copy())
        self.assertEqual(out["startDate"].iloc[0], "2020-1-1")
        self.assertEqual(out["endDate"].iloc[0], "2020-12-31")

if __name__ == "__main__":
    unittest.main()
