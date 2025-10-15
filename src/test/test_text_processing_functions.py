import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
import spacy
from src.text_processing_functions import (
    detect_language, written_num, is_float_digit,
    replace_numbers, replace_commas_in_numbers, replace_count_suffixes,
    could_be_unit, standardize_metric_units,
    clean_text, fix_pdf_text,
    select_hazard_description, change_hazard,
    check_hazard_type_keyword, extract_entities, extract_causal_relationships
)

class TestTextProcessing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nlp = spacy.load("en_core_web_sm")

    # ---------------- Language & number detection ----------------
    def test_detect_language_normal(self):
        lang = detect_language("This is a simple sentence.")
        self.assertEqual(lang, "en")

    def test_detect_language_empty(self):
        lang = detect_language("")
        self.assertEqual(lang, "en")  # spaCy fastlang defaults to English on empty

    def test_written_num_valid(self):
        self.assertTrue(written_num("three"))

    def test_written_num_invalid(self):
        self.assertFalse(written_num("nonsenseword"))

    def test_is_float_digit_valid(self):
        self.assertTrue(is_float_digit("42.0"))

    def test_is_float_digit_invalid(self):
        self.assertFalse(is_float_digit("NaNword"))

    # ---------------- Replace numbers & formatting ----------------
    def test_replace_numbers_simple(self):
        self.assertIn("3", replace_numbers("three cats"))

    def test_replace_numbers_with_propn(self):
        # Should not replace "May" (PROPN)
        result = replace_numbers("I visited in May")
        self.assertIn("May", result)

    def test_replace_commas_in_numbers(self):
        self.assertEqual(replace_commas_in_numbers("1,000"), "1000")

    def test_replace_commas_no_change(self):
        self.assertEqual(replace_commas_in_numbers("word, word"), "word, word")

    def test_replace_count_suffixes_k(self):
        self.assertEqual(replace_count_suffixes("2k"), "2000.0")

    def test_replace_count_suffixes_m(self):
        self.assertEqual(replace_count_suffixes("1.5m"), "1500000.0")

    def test_replace_count_suffixes_no_suffix(self):
        self.assertEqual(replace_count_suffixes("100"), "100")

    # ---------------- Units ----------------
    def test_could_be_unit_true(self):
        self.assertTrue(could_be_unit("5 km"))

    def test_could_be_unit_false(self):
        self.assertFalse(could_be_unit("5 apples"))

    def test_standardize_metric_units_simple(self):
        result = standardize_metric_units("10 miles")
        converted = "kilometer "
        self.assertIn("16.09344 kilometer", result)

    def test_standardize_metric_units_no_units(self):
        text = "There are 5 apples"
        self.assertEqual(standardize_metric_units(text), text)

    def test_standardize_metric_units_multiple_matches(self):
        # "10 ton tonne" matches both ton and tonne -> ValueError
        with self.assertRaises(ValueError):
            standardize_metric_units("10 ton tonne")

    # ---------------- Text cleaning ----------------
    def test_clean_text_remove_numbers(self):
        result = clean_text("Text 123", remove_numbers=True)
        self.assertNotIn("123", result)

    def test_clean_text_remove_stopwords(self):
        result = clean_text("This is a test", remove_stopwords=True)
        self.assertNotIn("is", result.lower())

    def test_fix_pdf_text_normalization(self):
        raw = "Hello\x00 World \n"
        self.assertEqual(fix_pdf_text(raw), "hello world")

    def test_fix_pdf_text_empty(self):
        self.assertEqual(fix_pdf_text(""), "")

    # ---------------- Hazard description ----------------
    def test_select_hazard_description_normal(self):
        sentences = ["background details",
                     "other stuff",
                     "other stuff 2",
                     "other stuff 3",
                     "other stuff 4",
                     "other stuff 5",
                     "other stuff 6",
                     "other stuff 7",
                     "other stuff 8",
                     "other stuff 9",
                     "other stuff 10",
                     "other stuff 11",
                     "coordination and partnerships info",
                     "blabla",
                     "blabla 2"]
        selected = ["background details",
                     "other stuff",
                     "other stuff 2",
                     "other stuff 3",
                     "other stuff 4",
                     "other stuff 5",
                     "other stuff 6",
                     "other stuff 7",
                     "other stuff 8",
                     "other stuff 9",
                     "other stuff 10",
                     "other stuff 11",
                     "coordination and partnerships info",
                     "blabla"]#buffer of 1
        result = select_hazard_description(sentences)
        self.assertEqual(selected, result)

    def test_select_hazard_description_no_matches(self):
        sentences = ["random text", "other stuff"]
        result = select_hazard_description(sentences)
        self.assertEqual(result, sentences)  # returns full text if no match

    # ---------------- Hazards ----------------
    def test_change_hazard_simple(self):
        reports = [{"disasterTypeReclassified": "Flood"}]
        grouped = {"Flood": ["Flood", "Flash Flood"]}
        result = change_hazard(reports, grouped)
        self.assertEqual(result[0]["disasterTypeReclassified"], ["Flood"])

    def test_change_hazard_no_match(self):
        reports = [{"disasterTypeReclassified": "Alien Invasion"}]
        grouped = {"Flood": ["Flood"]}
        result = change_hazard(reports, grouped)
        self.assertEqual(result, [])  # no match -> removed

    def test_check_hazard_type_keyword_match(self):
        hazards = {"Flood": r"\bflood\b"}
        result = check_hazard_type_keyword("Big flood", hazards)
        self.assertIn("Flood", result)

    def test_check_hazard_type_keyword_no_match(self):
        hazards = {"Flood": r"\bflood\b"}
        result = check_hazard_type_keyword("Sunny day", hazards)
        self.assertEqual(result, [])

    # ---------------- Entities & causal relationships ----------------
    def test_extract_entities(self):
        ents = extract_entities("Barack Obama visited Paris.")
        self.assertTrue(any("Barack Obama" in ent for ent, _ in ents))

    def test_extract_entities_empty(self):
        ents = extract_entities("")
        self.assertEqual(ents, [])

    def test_extract_causal_relationships_simple(self):
        hazards = {"Flood": r"\bflood\b", "cholera": r"\bcholera\b"}
        sentence = "Flood caused cholera."
        rels = extract_causal_relationships(sentence, ["cause"], hazards)
        self.assertTrue(any("Flood" in rel for rel in rels))

    def test_extract_causal_relationships_no_relation(self):
        hazards = {"Flood": r"\bflood\b"}
        sentence = "Flood is dangerous."
        rels = extract_causal_relationships(sentence, ["cause"], hazards)
        self.assertEqual(rels, [])

if __name__ == "__main__":
    unittest.main()
