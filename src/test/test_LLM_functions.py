import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
import pandas as pd
import json
from unittest.mock import patch, MagicMock
import sys, os
from types import SimpleNamespace
from src.LLM_functions import (
    extract_outer_json, add_key_value_pairs,
    build_messages, force_target_type, get_target_type,
    deduplicate_structured_responses, break_down_sent, break_down_text,
    extract_impact_value, is_extraction_finished, extract_json_block,
    get_model_response, get_model_response_retry, get_model_response_retry_continue,
    parse_none_str
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

    #def test_check_result_json_valid(self):
    #    result = check_result_json('{"key": "value"}')
    #    self.assertEqual(result, {"key": "value"})
#
    #def test_check_result_json_with_label(self):
    #    result = check_result_json('{"outer": {"inner": 42}}', label="outer")
    #    self.assertEqual(result, {"inner": 42})
#
    #def test_check_result_json_invalid(self):
    #    self.assertIsNone(check_result_json("invalid_json"))

    def test_build_messages_minimal(self):
        messages = build_messages("hello")
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "hello")

    def test_build_messages_with_prompts(self):
        messages = build_messages("hi", prompt_system="sys", prompt_assistant="asst")
        roles = [m["role"] for m in messages]
        self.assertIn("system", roles)
        self.assertIn("assistant", roles)

    def test_extract_json_block_object(self):
        text = 'here is {"a": 1, "b": 2} end'
        self.assertEqual(extract_json_block(text), '{"a": 1, "b": 2}')

    def test_extract_json_block_array(self):
        text = 'start [1, 2, 3] finish'
        self.assertEqual(extract_json_block(text), '[1, 2, 3]')

    def test_extract_json_block_mixed(self):
        text = 'start [1, 2, 3] {"key": "value"} end'
        self.assertEqual(extract_json_block(text), '[1, 2, 3]')

        text = 'start {"key": "value"} [1, 2, 3] end'
        self.assertEqual(extract_json_block(text), '{"key": "value"}')

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

    def test_get_model_response_success(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(total_tokens=10, completion_tokens=5),
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":1}'))]
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = response
        with patch('src.LLM_functions.CLIENT', mock_client):
            res = get_model_response([{"role": "user", "content": "hi"}], initial_wait=0)
            self.assertIs(res, response)

    def test_get_model_response_retry_on_429(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(total_tokens=1, completion_tokens=1),
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":2}'))]
        )
        mock_client = MagicMock()
        # first call raises a rate error, second returns response
        mock_client.chat.completions.create.side_effect = [Exception("429 Too Many Requests"), response]
        with patch('src.LLM_functions.CLIENT', mock_client):
            with patch('src.LLM_functions.time.sleep', return_value=None):
                res = get_model_response([{"role": "user", "content": "hi"}], max_retries=3, initial_wait=0)
                self.assertIs(res, response)

    def test_get_model_response_non_retryable_error(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("unexpected failure")
        with patch('src.LLM_functions.CLIENT', mock_client):
            res = get_model_response([{"role": "user", "content": "hi"}], initial_wait=0)
            self.assertIsNone(res)

    def test_get_model_response_retry_parsing_and_validation(self):
        # mock API response
        raw_json = '{"data": [1,2,3]}'
        response = SimpleNamespace(
            usage=SimpleNamespace(total_tokens=1, completion_tokens=1),
            choices=[SimpleNamespace(message=SimpleNamespace(content=raw_json))]
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = response

        # fake output_model that validates and returns an object with model_dump
        validated = MagicMock()
        validated.model_dump.return_value = {"validated": True}
        output_model = MagicMock()
        output_model.model_validate.return_value = validated

        with patch('src.LLM_functions.CLIENT', mock_client):
            resp, struct, nb_err = get_model_response_retry([{"role": "user", "content": "u"}], output_model)
            self.assertIs(resp, response)
            self.assertEqual(struct, {"validated": True})
            self.assertEqual(nb_err, 0)

    def test_get_model_response_retry_with_jsonrepair_fallback(self):
        # response content includes text around JSON
        raw_text = 'prefix {"x": 2} suffix'
        response = SimpleNamespace(
            usage=SimpleNamespace(total_tokens=1, completion_tokens=1),
            choices=[SimpleNamespace(message=SimpleNamespace(content=raw_text))]
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = response

        # make json_repair.loads fail to force fallback to extract_json_block + json.loads
        with patch('src.LLM_functions.CLIENT', mock_client):
            with patch('src.LLM_functions.json_repair.loads', side_effect=Exception("bad")):
                validated = MagicMock()
                validated.model_dump.return_value = {"ok": 1}
                output_model = MagicMock()
                output_model.model_validate.return_value = validated

                resp, struct, nb_err = get_model_response_retry([{"role": "user", "content": "u"}], output_model)
                self.assertIs(resp, response)
                self.assertEqual(struct, {"ok": 1})

    def test_parse_none_str_list(self):
        inp = [{"a": "None", "b": "value"}, {"c": "null", "d": "None"}]
        out = parse_none_str(inp)
        self.assertIsInstance(out, list)
        self.assertIsNone(out[0]["a"])
        self.assertEqual(out[0]["b"], "value")
        self.assertIsNone(out[1]["c"])

    def test_deduplicate_with_empty_prev(self):
        prev = []
        new = [
            {"impactSubtype": "flood", "impactValue": 10, "impactUnit": "ppl"},
            {"impactSubtype": "storm", "impactValue": 5, "impactUnit": "houses"},
        ]
        res = deduplicate_structured_responses(prev, new)
        self.assertEqual(len(res), 2)

    def test_get_target_type_root_key(self):
        class Dummy:
            __annotations__ = {"root": list[int]}
        self.assertEqual(get_target_type(Dummy), list)

class TestGetModelResponseRetryContinue(unittest.TestCase):

    def test_get_model_response_retry_continue_structure_and_valid_error_ext(self):
        # Prepare mock responses for two rounds
        resp1 = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='raw1'))])
        resp2 = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='raw2'))])
        struct1 = [
            {"impactSubtype": "flood", "impactValue": 10, "impactUnit": "ppl"}
        ]
        struct2 = [
            {"impactSubtype": "flood", "impactValue": 10, "impactUnit": "ppl"},
            {"impactSubtype": "storm", "impactValue": 5, "impactUnit": "houses"}
        ]
        # Side effects correspond to successive calls inside get_model_response_retry_continue
        mock_get = MagicMock()
        mock_get.side_effect = [
            (resp1, struct1, 1),  # first round: one item, 1 validation error
            (resp2, struct2, 2),  # second round: one new item (after dedupe), 2 validation errors
            (resp2, struct2, 2)   # additional rounds if needed
        ]
        with patch('src.LLM_functions.get_model_response_retry', mock_get):
            out, valid_errs = get_model_response_retry_continue("user prompt", MagicMock(), max_rounds=5)

        # Verify structure and contents
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 2)  # flood (first round) + storm (new in second round)
        subtypes = [e.get("impactSubtype") for e in out]
        self.assertIn("flood", subtypes)
        self.assertIn("storm", subtypes)
        # valid_errs should contain the validation error counts per extracted impact in order
        self.assertEqual(valid_errs, [1, 2])

if __name__ == "__main__":
    unittest.main()
