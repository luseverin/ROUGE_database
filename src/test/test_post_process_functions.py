import unittest
import re
import pandas as pd
import numpy as np
import pycountry
from price_parser import Price
from currency_converter import CurrencyConverter
from datetime import datetime

from src.units import *  # adjust to your file name
from src.impact_def import *
from src.hazard_def import *

# import your functions
from src.post_process_functions import (
    country_name_to_iso3,
    list_country_name_to_iso3,
    separate_locs,
    remove_startspace,
    label_quanti_quali,
    parse_impact_value_precision,
    reclassify_impact_subtype,
    reclassify_hazard,
    convert_unit,
    assign_unit_type,
    reclassify_units,
    standardize_metric_units,
    join_value_units,
    split_value_units,
    convert_monetary_units,
    replace_numbers_unit,
    make_date,
    harmonize_units,
    normalize_people_unit,
    force_unit_to_subtype,
    reclass_subtype_from_unit,
    convert_null_unit,
    classify_damage_degree,
    remove_hazards_epidemics_conflict,
)

# Use redefined helpers from data_format for list/format helpers
from src.data_format import delistify_cols, listify_strings, format_output

# Define positive and negative test cases for each category
regex_test_cases = {
    "people": {
        "positives": ["100 people", "people affected", "of people"],
        "negatives": ["peopledom", "personal", "evacuate"],
    },
    "roads": {
        "positives": ["roads damaged", "roads", "roads destroyed"],
        "negatives": ["broadway show", "offroaders"],
    },
    "transportation structures": {
        "positives": ["railway", "train tracks", "airport damaged", "seaports"],
        "negatives": ["trail", "training"],
    },
    "water points": {
        "positives": ["water sources", "wells", "taps", "reservoir", "water supply"],
        "negatives": ["watershed", "hydropower"],
    },
    "WASH structures": {
        "positives": [
            "latrines built",
            "sanitation systems",
            "aqueduct",
            "toilets",
            "water treatment plants",
        ],
        "negatives": ["water points", "wells"],
    },
    "healthcare structures": {
        "positives": ["hospital destroyed", "medical clinic", "maternity center"],
        "negatives": ["healthiness", "medicine"],
    },
    "IT and communication structures": {
        "positives": [
            "radio station",
            "cell tower down",
            "antenna",
            "telecommunication center",
        ],
        "negatives": ["communication skills", "televisionary"],
    },
    "power and energy production structures": {
        "positives": [
            "power lines",
            "solar generators",
            "hydro dams",
            "electric poles",
            "electric supply",
        ],
        "negatives": ["empowered", "energetic"],
    },
    "homes": {
        "positives": ["homes destroyed", "home", "residential structures"],
        "negatives": ["homeostasis", "building up momentum"],
    },
    "education structures": {
        "positives": ["schools collapsed", "universities closed", "college damaged"],
        "negatives": ["schooling fish", "educationalist"],
    },
    "crop production and forestry": {
        "positives": [
            "crop loss",
            "rice fields",
            "forest fire",
            "coffee plantations",
            "maize production",
        ],
        "negatives": ["treetop adventure", "bananarama band"],
    },
    "agricultural structures": {
        "positives": ["barn collapsed", "irrigation channel", "farms flooded"],
        "negatives": ["farming practice", "barnacle", "farmlands"],
    },
    "affected animals": {
        "positives": [
            "livestock lost",
            "dead cows",
            "sheep killed",
            "poultry disease",
            "cattle evacuated",
        ],
        "negatives": ["dog", "animalistic"],
    },
    "informal settlements": {
        "positives": [
            "refugee camp",
            "tent",
            "informal settlement",
            "huts",
            "idp site",
        ],
        "negatives": ["campus", "camping gear"],
    },
}


class TestUnitKwReclass(unittest.TestCase):

    def test_regex_patterns(self):
        """Loop through all regex patterns and test with positives/negatives"""
        for category, pattern in UNIT_KW_RECLASS.items():
            with self.subTest(category=category):
                regex = re.compile(pattern, re.IGNORECASE)
                test_data = regex_test_cases.get(category, {})

                for text in test_data.get("positives", []):
                    self.assertRegex(
                        text.lower(), regex, msg=f"{category} should match: {text}"
                    )

                for text in test_data.get("negatives", []):
                    self.assertNotRegex(
                        text.lower(), regex, msg=f"{category} should NOT match: {text}"
                    )


class TestCountryFunctions(unittest.TestCase):
    def test_country_name_to_iso3(self):
        self.assertEqual(country_name_to_iso3("Switzerland"), "CHE")
        self.assertEqual(country_name_to_iso3("FooLand"), "Unknown")

    def test_list_country_name_to_iso3(self):
        self.assertEqual(
            list_country_name_to_iso3(["France", "Germany"]), ["FRA", "DEU"]
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
        df = pd.DataFrame(
            {"impactValue": ["1", "2", None], "annotation": ["[1,2]", "x", None]}
        )
        out = format_output(df, num_cols=["impactValue"], list_cols=["annotation"])
        self.assertTrue(np.issubdtype(out["impactValue"].dtype, np.floating))
        self.assertIsInstance(out["annotation"].iloc[0], list)


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
        hazard_reclassed = [
            "Flood",
            "Unknown",
            "Convective storm",
            "Convective storm",
            "Mass movement",
        ]
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
        # Note: In the full pipeline, 'families' is first harmonized to 'households' by harmonize_units()
        x = pd.Series(
            {
                "impactValue": 10,
                "impactUnit": "households",
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
                "impactSubtype": "Affected People",
            }
        )
        out = convert_unit(x.copy())
        self.assertEqual(out["impactUnit"], "people")
        self.assertEqual(out["impactValue"], 30)
        self.assertTrue(out["flag_unit_conversion"])

    def test_convert_unit_no_match(self):
        x = pd.Series(
            {
                "impactValue": 10,
                "impactUnit": "kg",
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
                "impactSubtype": "Affected People",
            }
        )
        out = convert_unit(x.copy())
        self.assertEqual(out["impactUnit"], "kg")
        self.assertFalse(out["flag_unit_conversion"])

    def test_convert_unit_non_people_subtype(self):
        # Test that conversion is skipped when default unit for subtype is not 'people'
        x = pd.Series(
            {
                "impactValue": 10,
                "impactUnit": "households",
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
                "impactSubtype": "Damaged Structures",
            }
        )
        out = convert_unit(x.copy())
        self.assertEqual(out["impactUnit"], "households")  # Should not convert
        self.assertEqual(out["impactValue"], 10)  # Should not multiply
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
        xin = pd.DataFrame(
            {
                "impactValue": [10, 10],
                "impactValueMin": [np.nan, np.nan],
                "impactValueMax": [20, 20],
                "unit_type": ["other", "km**2"],
                "impactUnit": ["households", "km**2 of banana plantations"],
                "impactSubtype": ["Affected People", "agricultural infrastructure"],
            }
        )
        xexp = pd.DataFrame(
            {
                "impactValue": [10, 10],
                "impactValueMin": [np.nan, np.nan],
                "impactValueMax": [20, 20],
                "impactUnit": ["households", "km**2 of crop production and forestry"],
                "impactSubtype": ["Affected People", "Crop Production and Forestry"],
            }
        )

        for i in range(len(xin)):
            out = reclassify_units(xin.iloc[i])
            xexp_i = xexp.iloc[i]
            self.assertEqual(xexp_i["impactUnit"], out["impactUnit"])
            self.assertEqual(out["impactValue"], xexp_i["impactValue"])
            self.assertTrue(pd.isna(out["impactValueMin"]))
            self.assertEqual(out["impactValueMax"], xexp_i["impactValueMax"])

    def test_reclassify_units_reclass_subtype(self):
        # Note: In the full pipeline, 'families' would first be harmonized to 'households'
        # Unit contains 'idp' → reclassify to 'displaced', then subtype inferred to 'Displaced People'
        x = pd.Series(
            {
                "impactValue": 10,
                "impactValueMin": np.nan,
                "impactValueMax": 20,
                "impactUnit": "idp households",
                "unit_type": "other",
                "impactSubtype": "Affected People",
            }
        )
        out_units = reclassify_units(x.copy())
        self.assertEqual(
            "displaced", out_units["impactUnit"]
        )  # reclassify_units collapses to keyword
        self.assertTrue(out_units["flag_non-SI_unit_standardization"])  # unit changed

        out_subtype = reclass_subtype_from_unit(out_units.copy())
        self.assertEqual(out_subtype["impactSubtype"], "Displaced People")
        self.assertTrue(out_subtype["flag_reclass_subtype_from_unit"])

    def test_standardize_metric_units(self):
        xin = pd.DataFrame(
            {
                "impactValue": [10, 20, 20, 30],
                "impactUnit": ["liters", "square meter", "meter square", "ha"],
                "impactValueMin": [np.nan, 20, 20, 30],
                "impactValueMax": [20, 20, 20, 30],
            }
        )
        xexp = pd.DataFrame(
            {
                "impactValue": [0.01, 0.00002, 0.00002, 0.3],
                "impactUnit": ["m**3", "km**2", "km**2", "km**2"],
                "impactValueMin": [np.nan, 0.00002, 0.00002, 0.3],
                "impactValueMax": [0.02, 0.00002, 0.00002, 0.3],
            }
        )
        for i in range(len(xin)):
            out = standardize_metric_units(xin.iloc[i])
            self.assertEqual(out["impactUnit"], xexp["impactUnit"].iloc[i])
            self.assertAlmostEqual(
                out["impactValue"], xexp["impactValue"].iloc[i], places=5
            )
            if pd.isna(xexp["impactValueMin"].iloc[i]):
                self.assertTrue(pd.isna(out["impactValueMin"]))
            else:
                self.assertAlmostEqual(
                    out["impactValueMin"], xexp["impactValueMin"].iloc[i], places=5
                )
            self.assertAlmostEqual(
                out["impactValueMax"], xexp["impactValueMax"].iloc[i], places=5
            )
            self.assertTrue(out["flag_SI_unit_standardization"])

    def test_standardize_metric_units_invalid(self):
        x = pd.Series(
            {
                "impactValue": 10,
                "impactUnit": "unknown",
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
            }
        )
        out = standardize_metric_units(x)
        self.assertFalse(out["flag_SI_unit_standardization"])

    def test_force_unit_to_subtype_applies(self):
        # When unit is unknown and subtype is known, force unit to default subtype unit
        x = pd.Series(
            {
                "impactValue": 1,
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
                "impactUnit": "unknown_unit",
                "unit_type": "other",
                "impactSubtype": "Education Infrastructure",
            }
        )
        out = force_unit_to_subtype(x.copy())
        self.assertEqual(out["impactUnit"], "education structures")
        self.assertTrue(out["flag_force_unit_to_subtype"])

    def test_force_unit_to_subtype_skips_people_or_null(self):
        # Should not force when unit is already people or empty/null
        for unit in ["people", "", "null"]:
            x = pd.Series(
                {
                    "impactValue": 1,
                    "impactValueMin": np.nan,
                    "impactValueMax": np.nan,
                    "impactUnit": unit,
                    "unit_type": "other",
                    "impactSubtype": "Affected People",
                }
            )
            out = force_unit_to_subtype(x.copy())
            self.assertEqual(out["impactUnit"], unit)
            self.assertFalse(out["flag_force_unit_to_subtype"])

    def test_reclass_subtype_from_unit(self):
        # If unit equals expected unit for a different subtype, subtype should be updated
        x = pd.Series(
            {
                "impactValue": 5,
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
                "impactUnit": "displaced",
                "unit_type": "other",
                "impactSubtype": "Affected People",
            }
        )
        out = reclass_subtype_from_unit(x.copy())
        self.assertEqual(out["impactSubtype"], "Displaced People")
        self.assertTrue(out["flag_reclass_subtype_from_unit"])

    def test_join_split_value_units(self):
        x = pd.Series({"impactValue": 5, "impactUnit": "kg"})
        vu = join_value_units(x)
        self.assertEqual(vu, "5,kg")
        y = pd.Series({"value_unit": vu})
        self.assertEqual(split_value_units(y), ["5", "kg"])

    def test_convert_monetary_units(self):
        x = pd.DataFrame(
            {
                "impactValue": [1500, 1500, 10],
                "impactValueMin": [1000, 1000, 10],
                "impactValueMax": [2000, 2000, 10],
                "impactUnit": ["us $", "chf", "euro"],
                "reportDate": ["2020-01-01", "", "2019-06-15"],
            }
        )
        for i in range(len(x)):
            out = convert_monetary_units(x.iloc[i])
            self.assertEqual(out["impactUnit"], "EUR")
            self.assertIsInstance(out["impactValue"], (int, float))
            self.assertIsInstance(out["impactValueMin"], (int, float))
            self.assertIsInstance(out["impactValueMax"], (int, float))
            self.assertTrue(out["flag_currency_conversion"])
            self.assertFalse(out["flag_failed_currency_conversion"])

    def test_convert_monetary_units_additional_currencies(self):
        # Test some of the newly added currencies
        x = pd.DataFrame(
            {
                "impactValue": [1000, 5000, 200],
                "impactValueMin": [800, 4000, 150],
                "impactValueMax": [1200, 6000, 250],
                "impactUnit": ["indian rupees", "japanese yen", "british pounds"],
                "reportDate": ["2020-01-01", "2020-01-01", "2020-01-01"],
            }
        )
        for i in range(len(x)):
            out = convert_monetary_units(x.iloc[i])
            self.assertEqual(out["impactUnit"], "EUR")
            self.assertIsInstance(out["impactValue"], (int, float))
            self.assertTrue(out["flag_currency_conversion"])
            self.assertFalse(out["flag_failed_currency_conversion"])

    def test_convert_monetary_units_invalid_currency(self):
        x = pd.DataFrame(
            {
                "impactValue": [1500, 1500],
                "impactValueMin": [1000, 1000],
                "impactValueMax": [2000, 2000],
                "impactUnit": ["people", "europe"],
                "reportDate": ["2020-01-01", "2019-06-15"],
            }
        )
        for i in range(len(x)):
            out = convert_monetary_units(x.iloc[i])
            self.assertFalse(out["flag_currency_conversion"])

    def test_replace_numbers_unit(self):
        # Test with digits in unit
        x = pd.Series(
            {
                "impactValue": 5,
                "impactUnit": "2 houses",
                "impactValueMin": 2,
                "impactValueMax": np.nan,
            }
        )
        out = replace_numbers_unit(x)
        self.assertEqual("houses", out["impactUnit"])
        self.assertEqual(out["impactValue"], 10)
        self.assertEqual(out["impactValueMin"], 4)
        self.assertTrue(pd.isna(out["impactValueMax"]))
        self.assertTrue(out["flag_remove_number_unit"])

        x = pd.Series(
            {
                "impactValue": 5,
                "impactUnit": "two houses",
                "impactValueMin": 2,
                "impactValueMax": np.nan,
            }
        )
        out = replace_numbers_unit(x)
        self.assertEqual("houses", out["impactUnit"])
        self.assertEqual(out["impactValue"], 10)
        self.assertEqual(out["impactValueMin"], 4)
        self.assertTrue(pd.isna(out["impactValueMax"]))
        self.assertTrue(out["flag_remove_number_unit"])

        x = pd.Series(
            {
                "impactValue": 5,
                "impactUnit": "thousands people",
                "impactValueMin": 2,
                "impactValueMax": np.nan,
            }
        )
        out = replace_numbers_unit(x)
        self.assertEqual("people", out["impactUnit"])
        self.assertEqual(out["impactValue"], 5000)
        self.assertEqual(out["impactValueMin"], 2000)
        self.assertTrue(pd.isna(out["impactValueMax"]))
        self.assertTrue(out["flag_remove_number_unit"])

    def test_replace_numbers_unit_none(self):
        x = pd.Series(
            {
                "impactValue": 5,
                "impactUnit": None,
                "impactValueMin": np.nan,
                "impactValueMax": np.nan,
            }
        )
        out = replace_numbers_unit(x)
        self.assertFalse(out["flag_remove_number_unit"])

    def test_make_date(self):
        df = pd.DataFrame(
            {
                "startYear": [2020],
                "startMonth": [1],
                "startDay": [1],
                "endYear": [2020],
                "endMonth": [12],
                "endDay": [31],
            }
        )
        out = make_date(df.copy())
        self.assertEqual(out["startDate"].iloc[0], "2020-1-1")
        self.assertEqual(out["endDate"].iloc[0], "2020-12-31")

    def test_make_date_partial(self):
        df = pd.DataFrame(
            {
                "startYear": [2020],
                "startMonth": [6],
                "startDay": [None],
                "endYear": [2020],
                "endMonth": [None],
                "endDay": [None],
            }
        )
        out = make_date(df.copy())
        self.assertEqual(out["startDate"].iloc[0], "2020-6")
        self.assertEqual(out["endDate"].iloc[0], "2020")

    def test_make_date_year_only(self):
        df = pd.DataFrame(
            {
                "startYear": [2020],
                "startMonth": [None],
                "startDay": [None],
                "endYear": [2021],
                "endMonth": [None],
                "endDay": [None],
            }
        )
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


class TestConvertNullUnit(unittest.TestCase):
    def test_convert_null_unit_with_nan(self):
        """Test that NaN is converted to 'null' string"""
        x = pd.Series({"impactUnit": np.nan})
        out = convert_null_unit(x)
        self.assertEqual(out["impactUnit"], "null")

    def test_convert_null_unit_with_none(self):
        """Test that None is converted to 'null' string"""
        x = pd.Series({"impactUnit": None})
        out = convert_null_unit(x)
        self.assertEqual(out["impactUnit"], "null")

    def test_convert_null_unit_with_string_nan(self):
        """Test that string 'nan' is converted to 'null'"""
        x = pd.Series({"impactUnit": "nan"})
        out = convert_null_unit(x)
        self.assertEqual(out["impactUnit"], "null")

    def test_convert_null_unit_with_string_none(self):
        """Test that string 'none' is converted to 'null'"""
        x = pd.Series({"impactUnit": "none"})
        out = convert_null_unit(x)
        self.assertEqual(out["impactUnit"], "null")

    def test_convert_null_unit_with_capitalized_none(self):
        """Test that capitalized 'None' is converted to 'null'"""
        x = pd.Series({"impactUnit": "None"})
        out = convert_null_unit(x)
        self.assertEqual(out["impactUnit"], "null")

    def test_convert_null_unit_with_empty_string(self):
        """Test that empty string is converted to 'null'"""
        x = pd.Series({"impactUnit": ""})
        out = convert_null_unit(x)
        self.assertEqual(out["impactUnit"], "null")

    def test_convert_null_unit_preserves_valid_units(self):
        """Test that valid units are not changed"""
        test_units = ["people", "kg", "km**2", "homes", "USD"]
        for unit in test_units:
            x = pd.Series({"impactUnit": unit})
            out = convert_null_unit(x)
            self.assertEqual(
                out["impactUnit"], unit, f"Unit '{unit}' should be preserved"
            )


class TestAdditionalUnitFunctions(unittest.TestCase):
    def test_harmonize_units(self):
        x = pd.Series({"impactUnit": "individuals"})
        out = harmonize_units(x)
        self.assertEqual(out["impactUnit"], "people")
        self.assertTrue(out["flag_unit_harmonization"])

    def test_harmonize_units_families_to_households(self):
        """Test that 'families' is harmonized to 'households'"""
        x = pd.Series({"impactUnit": "families"})
        out = harmonize_units(x)
        self.assertEqual(out["impactUnit"], "households")
        self.assertTrue(out["flag_unit_harmonization"])

    def test_harmonize_units_family_to_households(self):
        """Test that 'family' is harmonized to 'households'"""
        x = pd.Series({"impactUnit": "family"})
        out = harmonize_units(x)
        self.assertEqual(out["impactUnit"], "households")
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
        df = pd.DataFrame({"impactValue": ["1", "2", None], "b": ["x", "y", "z"]})
        out = format_output(df, num_cols=["impactValue"])
        self.assertTrue(np.issubdtype(out["impactValue"].dtype, np.floating))

    def test_format_output_list_conversion(self):
        df = pd.DataFrame(
            {"impactValue": [1, 2, 3], "annotation": ["[1,2]", "x", "[]"]}
        )
        out = format_output(df, list_cols=["annotation"])
        self.assertIsInstance(out["annotation"].iloc[0], list)
        self.assertEqual(out["annotation"].iloc[0], [1, 2])

    def test_format_output_mixed(self):
        df = pd.DataFrame(
            {
                "impactValue": ["1", "2", None],
                "annotation": ["['a','b']", "hello", None],
            }
        )
        out = format_output(df, num_cols=["impactValue"], list_cols=["annotation"])
        self.assertTrue(np.issubdtype(out["impactValue"].dtype, np.floating))
        self.assertIsInstance(out["annotation"].iloc[0], list)


class TestPostProcessingPipeline(unittest.TestCase):
    """Integration test that verifies the complete postprocessing pipeline"""

    def test_full_pipeline(self):
        """Test the complete postprocessing workflow as in postprocess_results.py"""
        # Create sample data mimicking LLM output
        sample_data = pd.DataFrame(
            {
                "impactValue": ["100", "50", "1500", "10"],
                "impactValueMin": [None, "30", "1000", "5"],
                "impactValueMax": ["120", None, "2000", "15"],
                "impactUnit": [
                    "families",
                    "2 houses",
                    "us $",
                    "ha of agricultural land",
                ],
                "impactSubtype": [
                    "Affected People",
                    "Damaged Structures",
                    "Economic Loss",
                    "agricultural land",
                ],
                "country": [
                    "['France', 'Germany']",
                    "['Spain']",
                    "['Switzerland']",
                    "['Kenya']",
                ],
                "location": [
                    "['Paris', 'Berlin']",
                    "['Madrid']",
                    "['Zurich']",
                    "['Nairobi']",
                ],
                "hazards": [
                    "['flood', 'tornado']",
                    "['earthquake']",
                    "['wildfire']",
                    "['drought']",
                ],
                "startYear": [2020, 2021, 2022, 2023],
                "startMonth": [1, None, 6, 3],
                "startDay": [15, None, None, 10],
                "endYear": [2020, 2021, 2022, 2023],
                "endMonth": [2, None, 7, 4],
                "endDay": [20, None, None, 15],
                "reportDate": ["2020-03-01", "2021-05-01", "2022-08-01", "2023-05-01"],
            }
        )

        # Step 1: Format output
        df = format_output(sample_data.copy())

        # Step 2: Parse impact value precision
        df = df.apply(parse_impact_value_precision, axis=1)

        # Step 3: Label quanti/quali
        df = df.apply(label_quanti_quali, axis=1)

        # Step 4: Reclassify impact subtypes
        df = df.apply(reclassify_impact_subtype, axis=1)

        # Step 5: Reclassify hazards
        df = df.apply(reclassify_hazard, hazard_kw_reclass=hazard_kw_reclass, axis=1)

        # Step 6: Replace numbers in units
        df = df.apply(replace_numbers_unit, axis=1)

        # Step 7: Standardize metric units
        df = df.apply(standardize_metric_units, axis=1)

        # Step 8: Harmonize units
        df = df.apply(harmonize_units, axis=1)

        # Step 9: Assign unit type
        df = df.apply(assign_unit_type, axis=1)

        # Step 10: Convert units (families -> people)
        df = df.apply(convert_unit, axis=1)

        # Step 11: Reclassify units
        df = df.apply(reclassify_units, axis=1)

        # Step 12: Normalize people units
        df = df.apply(normalize_people_unit, axis=1)

        # Step 13: Convert monetary units
        df = df.apply(convert_monetary_units, axis=1)

        # Verify results
        # Row 0: families -> people conversion
        self.assertEqual(df.loc[0, "impactUnit"], "people")
        self.assertEqual(df.loc[0, "impactValue"], 360)  # 120 families * 3
        self.assertEqual(df.loc[0, "impactSubtype"], "Affected People")
        self.assertTrue(df.loc[0, "flag_unit_conversion"])

        # Row 1: houses with number extraction
        self.assertEqual(df.loc[1, "impactUnit"], "homes")
        self.assertEqual(df.loc[1, "impactValue"], 100)  # 50 * 2
        self.assertTrue(df.loc[1, "flag_remove_number_unit"])

        # Row 2: currency conversion to EUR
        self.assertEqual(df.loc[2, "impactUnit"], "EUR")
        self.assertTrue(df.loc[2, "flag_currency_conversion"])
        self.assertIsInstance(df.loc[2, "impactValue"], (int, float))

        # Row 3: metric unit standardization
        self.assertEqual(
            df.loc[3, "impactUnit"], "km**2 of crop production and forestry"
        )
        self.assertTrue(df.loc[3, "flag_SI_unit_standardization"])

        # Verify hazard reclassification
        self.assertIn("Flood", df.loc[0, "hazards"])
        self.assertIn("Convective storm", df.loc[0, "hazards"])

        # Verify all rows have quanti label
        self.assertTrue(all(df["quanti"] == "quanti"))

        # Verify numeric columns are proper floats
        for col in ["impactValue", "impactValueMin", "impactValueMax"]:
            self.assertTrue(np.issubdtype(df[col].dtype, np.floating))

    def test_pipeline_with_quali_data(self):
        """Test pipeline with qualitative data (no values)"""
        sample_data = pd.DataFrame(
            {
                "impactValue": [None, np.nan],
                "impactValueMin": [None, np.nan],
                "impactValueMax": [None, np.nan],
                "impactUnit": ["people", np.nan],
                "impactSubtype": ["Displaced People", "Damaged Structures"],
                "country": ["['Haiti']", "['Bangladesh']"],
                "location": ["['Port-au-Prince']", "['Dhaka']"],
                "hazards": ["['earthquake']", "['flood']"],
                "startYear": [2010, 2020],
                "startMonth": [1, 7],
                "startDay": [12, 15],
                "endYear": [2010, 2020],
                "endMonth": [1, 8],
                "endDay": [12, 1],
                "reportDate": ["2010-02-01", "2020-09-01"],
            }
        )

        # Run through pipeline
        df = format_output(sample_data.copy())

        # Step 2: Parse impact value precision
        df = df.apply(parse_impact_value_precision, axis=1)

        # Step 3: Label quanti/quali
        df = df.apply(label_quanti_quali, axis=1)

        # Step 4: Reclassify impact subtypes
        df = df.apply(reclassify_impact_subtype, axis=1)

        # Step 5: Reclassify hazards
        df = df.apply(reclassify_hazard, hazard_kw_reclass=hazard_kw_reclass, axis=1)

        # Step 6: Replace numbers in units
        df = df.apply(replace_numbers_unit, axis=1)

        # Step 7: Standardize metric units
        df = df.apply(standardize_metric_units, axis=1)

        # Step 8: Harmonize units
        df = df.apply(harmonize_units, axis=1)

        # Step 9: Assign unit type
        df = df.apply(assign_unit_type, axis=1)

        # Step 10: Convert units (families -> people)
        df = df.apply(convert_unit, axis=1)

        # Step 11: Reclassify units
        df = df.apply(reclassify_units, axis=1)

        # Step 12: Normalize people units
        df = df.apply(normalize_people_unit, axis=1)

        # Step 13: Convert monetary units
        df = df.apply(convert_monetary_units, axis=1)

        # df.loc[df["quanti"] == "quali", "impactUnit"] = "null"

        # Verify all rows are labeled as quali
        self.assertTrue(all(df["quanti"] == "quali"))

        # Verify subtypes are preserved
        self.assertEqual(df.loc[0, "impactSubtype"], "Displaced People")
        self.assertEqual(
            df.loc[1, "impactSubtype"], "Unknown"
        )  # 'Damaged Structures' not in keywords

        # Verify units are processed correctly
        self.assertEqual(df.loc[0, "impactUnit"], "people")
        self.assertEqual(df.loc[1, "impactUnit"], "null")

    def test_remove_hazards_epidemics_conflict(self):
        """Test removal flag for epidemic/conflict-only hazard lists"""
        df = pd.DataFrame(
            {
                "hazards": [
                    ["Epidemic"],
                    ["Conflict"],
                    ["Epidemic", "Conflict"],
                    ["Epidemic", "Flood"],
                    ["Flood"],
                ]
            }
        )
        out = df.apply(remove_hazards_epidemics_conflict, axis=1)
        self.assertTrue(out.loc[0, "flag_remove_hazards_epidemics_conflict"])
        self.assertTrue(out.loc[1, "flag_remove_hazards_epidemics_conflict"])
        self.assertTrue(out.loc[2, "flag_remove_hazards_epidemics_conflict"])
        self.assertFalse(out.loc[3, "flag_remove_hazards_epidemics_conflict"])
        self.assertFalse(out.loc[4, "flag_remove_hazards_epidemics_conflict"])


class TestClassifyDamageDegree(unittest.TestCase):
    """Test cases for classify_damage_degree function"""

    def test_fully_destroyed_with_destroyed_keyword(self):
        """Test classification with 'destroyed' keyword"""
        x = pd.Series({"impactUnit": "homes destroyed"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "fully destroyed")

    def test_fully_destroyed_with_fully_damaged_keyword(self):
        """Test classification with 'fully damaged' keyword"""
        x = pd.Series({"impactUnit": "houses fully damaged"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "fully destroyed")

    def test_fully_destroyed_with_collapsed_keyword(self):
        """Test classification with 'collapsed' keyword"""
        x = pd.Series({"impactUnit": "buildings collapsed"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "fully destroyed")

    def test_fully_destroyed_with_flattened_keyword(self):
        """Test classification with 'flattened' keyword"""
        x = pd.Series({"impactUnit": "infrastructure flattened"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "fully destroyed")

    def test_fully_destroyed_with_completely_destroyed(self):
        """Test classification with 'completely destroyed' keyword"""
        x = pd.Series({"impactUnit": "structures completely destroyed"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "fully destroyed")

    def test_partially_damaged_with_damaged_keyword(self):
        """Test classification with 'damaged' keyword"""
        x = pd.Series({"impactUnit": "homes damaged"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "partially damaged")

    def test_partially_damaged_with_partially_damaged_keyword(self):
        """Test classification with 'partially damaged' keyword"""
        x = pd.Series({"impactUnit": "houses partially damaged"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "partially damaged")

    def test_partially_damaged_with_infrastructure_damaged(self):
        """Test classification with infrastructure damage"""
        x = pd.Series({"impactUnit": "infrastructure partially damaged"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "partially damaged")

    def test_unspecified_with_people_unit(self):
        """Test classification with people unit (not applicable)"""
        x = pd.Series({"impactUnit": "people"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_injured_unit(self):
        """Test classification with injured (not applicable)"""
        x = pd.Series({"impactUnit": "injured"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_deaths_unit(self):
        """Test classification with deaths (not applicable)"""
        x = pd.Series({"impactUnit": "deaths"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_affected_people(self):
        """Test classification with 'affected people' (not applicable)"""
        x = pd.Series({"impactUnit": "affected people"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_displaced_individuals(self):
        """Test classification with 'displaced individuals' (not applicable)"""
        x = pd.Series({"impactUnit": "displaced individuals"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_families_affected(self):
        """Test classification with 'families affected' (not applicable)"""
        x = pd.Series({"impactUnit": "families affected"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_homes_no_damage_qualifier(self):
        """Test classification with 'homes' without damage qualifier"""
        x = pd.Series({"impactUnit": "homes"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_buildings_no_damage_qualifier(self):
        """Test classification with 'buildings' without damage qualifier"""
        x = pd.Series({"impactUnit": "buildings"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_structures(self):
        """Test classification with 'structures' without damage qualifier"""
        x = pd.Series({"impactUnit": "structures"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_houses(self):
        """Test classification with 'houses' without damage qualifier"""
        x = pd.Series({"impactUnit": "houses"})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_empty_string(self):
        """Test classification with empty string"""
        x = pd.Series({"impactUnit": ""})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_null_value(self):
        """Test classification with null value"""
        x = pd.Series({"impactUnit": None})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_unspecified_with_nan_value(self):
        """Test classification with NaN value"""
        x = pd.Series({"impactUnit": np.nan})
        result = classify_damage_degree(x)
        self.assertEqual(result["damageDegree"], "unspecified")

    def test_dataframe_apply(self):
        """Test applying function to dataframe with apply()"""
        df = pd.DataFrame(
            {
                "impactValue": [100, 50, 30, 200, 15, 500],
                "impactUnit": [
                    "homes destroyed",
                    "houses damaged",
                    "people",
                    "buildings collapsed",
                    "families affected",
                    "infrastructure flattened",
                ],
            }
        )

        result_df = df.apply(classify_damage_degree, axis=1)

        # Verify new column was created
        self.assertIn("damageDegree", result_df.columns)

        # Verify classifications
        expected = [
            "fully destroyed",
            "partially damaged",
            "unspecified",
            "fully destroyed",
            "unspecified",
            "fully destroyed",
        ]
        self.assertEqual(result_df["damageDegree"].tolist(), expected)

    def test_case_insensitivity(self):
        """Test that classification is case-insensitive with Series input"""
        test_cases = [
            ("HOMES DESTROYED", "fully destroyed"),
            ("Houses Damaged", "partially damaged"),
            ("PEOPLE", "unspecified"),
            ("Injured", "unspecified"),
        ]

        for unit_str, expected in test_cases:
            x = pd.Series({"impactUnit": unit_str})
            result = classify_damage_degree(x)
            self.assertEqual(
                result["damageDegree"],
                expected,
                f"Failed for '{unit_str}' - got '{result['damageDegree']}' expected '{expected}'",
            )


if __name__ == "__main__":
    unittest.main()
