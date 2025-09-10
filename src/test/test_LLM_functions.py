import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
import pandas as pd
import json
from unittest.mock import patch, MagicMock
from src.LLM_functions import (
    extract_outer_json, add_key_value_pairs, check_result_json,
    build_messages, force_target_type, get_target_type,
    deduplicate_structured_responses, break_down_sent, break_down_text,
    extract_impact_value, is_extraction_finished
)


class TestLLMFunctions(unittest.TestCase):

    def test_extract_outer_json_valid(self):
        text = "prefix {\"key\": 123} suffix"
        self.assertEqual(extract_outer_json(text), '{"key": 123}')

    def test_extract_outer_json_invalid(self):
        self.assertIsNone(extract_outer_json("no json here"))

    def test_add_key_value_pairs_with_dict(self):
        data = [{"a": 1}, {"b": 2}]
        result = add_key_value_pairs(data, {"new": 99})
        for entry in result:
            self.assertIn("new", entry)
            self.assertEqual(entry["new"], 99)

    def test_add_key_value_pairs_with_list(self):
        data = [{"a": 1}, {"b": 2}]
        pairs = [{"c": 3}, {"d": 4}]
        result = add_key_value_pairs(data, pairs)
        self.assertEqual(result[0]["c"], 3)
        self.assertEqual(result[1]["d"], 4)

    def test_add_key_value_pairs_invalid_type(self):
        with self.assertRaises(TypeError):
            add_key_value_pairs([{"a": 1}], "not_a_dict")

    def test_check_result_json_valid(self):
        result = check_result_json('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_check_result_json_with_label(self):
        result = check_result_json('{"outer": {"inner": 42}}', label="outer")
        self.assertEqual(result, {"inner": 42})

    def test_check_result_json_invalid(self):
        self.assertIsNone(check_result_json("invalid_json"))

    def test_build_messages_minimal(self):
        messages = build_messages("hello")
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "hello")

    def test_build_messages_with_prompts(self):
        messages = build_messages("hi", prompt_system="sys", prompt_assistant="asst")
        roles = [m["role"] for m in messages]
        self.assertIn("system", roles)
        self.assertIn("assistant", roles)

    def test_force_target_type_list(self):
        class Dummy:
            __annotations__ = {"__root__": list[int]}
        self.assertEqual(force_target_type(Dummy, 5), [5])
        self.assertEqual(force_target_type(Dummy, [[1, 2], [3]]), [1, 2, 3])

    def test_force_target_type_dict(self):
        class Dummy:
            __annotations__ = {"__root__": dict}
        self.assertEqual(force_target_type(Dummy, [{"a": 1}]), {"a": 1})

    def test_force_target_type_passthrough(self):
        class Dummy:
            __annotations__ = {}
        resp = {"key": "value"}
        self.assertEqual(force_target_type(Dummy, resp), resp)

    def test_get_target_type_list(self):
        class Dummy:
            __annotations__ = {"__root__": list[int]}
        self.assertEqual(get_target_type(Dummy), list)

    def test_get_target_type_none(self):
        class Dummy:
            __annotations__ = {}
        self.assertIsNone(get_target_type(Dummy))

    def test_deduplicate_structured_responses(self):
        prev = [{"impactSubtype": "flood", "impactValue": 100, "impactUnit": "people"}]
        new = [
            {"impactSubtype": "flood", "impactValue": 100, "impactUnit": "people"},
            {"impactSubtype": "quake", "impactValue": 50, "impactUnit": "houses"},
        ]
        result = deduplicate_structured_responses(prev, new)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["impactSubtype"], "quake")

    def test_break_down_sent_short(self):
        sentences = ["short sentence"]
        self.assertEqual(break_down_sent(sentences, max_tokens=50), ["short sentence"])

    def test_break_down_sent_long(self):
        long_sentence = "x" * 120
        sentences = [long_sentence]
        result = break_down_sent(sentences, max_tokens=100)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(r, str) for r in result))

    def test_break_down_text_simple(self):
        sentences = ["a", "b", "c"]
        result = break_down_text(sentences, max_tokens=2)
        self.assertIsInstance(result, list)

    def test_extract_impact_value(self):
        df = pd.DataFrame([{"impactValue": 10, "impactValueMin": 5, "impactValueMax": 20}])
        self.assertEqual(extract_impact_value(df), 20)

    def test_is_extraction_finished_true(self):
        self.assertTrue(is_extraction_finished("This is __END__ now."))

    def test_is_extraction_finished_false(self):
        self.assertFalse(is_extraction_finished("Keep going"))

if __name__ == "__main__":
    unittest.main()
