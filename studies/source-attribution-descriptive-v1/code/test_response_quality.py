"""Synthetic acceptance-boundary checks; no scientific ratings or API calls."""

import json
import unittest

from design import parse_rating
from response_quality import assess_response


class ResponseQualityTests(unittest.TestCase):
    def setUp(self):
        self.complete = {
            "strength_rating": 0.5,
            "strongest_point": "synthetic strong point",
            "weakest_point": "synthetic weak point",
            "overall_assessment": "synthetic assessment",
        }

    def assess(self, value, complete=True):
        text = value if isinstance(value, str) else json.dumps(value)
        return assess_response(text, generation_complete=complete)

    def test_conformant_response_and_single_fence(self):
        text = json.dumps(self.complete)
        for wrapper in (text, "```json\n" + text + "\n```"):
            with self.subTest(wrapper=wrapper):
                result = self.assess(wrapper)
                self.assertTrue(result["rating_usable"])
                self.assertTrue(result["schema_conformant"])
                self.assertEqual(result["strength_rating"], 0.5)
                self.assertEqual(result["unusable_reasons"], [])

    def test_pilot_shaped_extra_fields_do_not_change_rating(self):
        # Only the extra key names come from the structural diagnostic; the
        # score and text are synthetic and do not reclassify the pilot data.
        for key in ("weakest_point_extended", "weakest_point_continued"):
            data = dict(self.complete, **{key: "synthetic continuation"})
            result = self.assess(data)
            self.assertTrue(result["rating_usable"])
            self.assertFalse(result["schema_conformant"])
            self.assertEqual(result["strength_rating"], 0.5)
            self.assertEqual(result["additional_fields"], [key])
            with self.assertRaises(ValueError):
                parse_rating(json.dumps(data))

    def test_missing_explanations_do_not_exclude_primary_rating(self):
        data = {"strength_rating": 0.5}
        result = self.assess(data)
        self.assertTrue(result["rating_usable"])
        self.assertFalse(result["schema_conformant"])
        self.assertEqual(result["missing_explanations"],
                         ["overall_assessment", "strongest_point", "weakest_point"])
        with self.assertRaises(ValueError):
            parse_rating(json.dumps(data))

    def test_invalid_explanations_are_separately_reported(self):
        for value in (None, 0, False, {}, [], "", "  "):
            with self.subTest(value=value):
                result = self.assess(dict(self.complete, weakest_point=value))
                self.assertTrue(result["rating_usable"])
                self.assertEqual(result["invalid_explanations"], ["weakest_point"])
                self.assertFalse(result["schema_conformant"])

    def test_alternate_rating_never_replaces_designated_field(self):
        result = self.assess({"strength_rating": 0.3, "strength_rating_final": 0.9})
        self.assertEqual(result["strength_rating"], 0.3)
        result = self.assess({"strength_rating_final": 0.9, "overall_assessment": "Rating is 0.9"})
        self.assertFalse(result["rating_usable"])
        self.assertIsNone(result["strength_rating"])
        self.assertIn("missing_strength_rating", result["unusable_reasons"])

    def test_invalid_numeric_values_cannot_be_used(self):
        values = (True, False, "0.5", None, [], {}, -0.1, 1.1, float("nan"),
                  float("inf"), -float("inf"), 10**400)
        for value in values:
            with self.subTest(value=str(value)[:30]):
                result = self.assess({"strength_rating": value})
                self.assertFalse(result["rating_usable"])
                self.assertIsNone(result["strength_rating"])
        for score in (0, 1, 0.0, 1.0):
            self.assertTrue(self.assess({"strength_rating": score})["rating_usable"])

    def test_duplicates_anywhere_are_rejected(self):
        texts = [
            '{"strength_rating":0.3,"strength_rating":0.9}',
            '{"strength_rating":0.5,"extra":{"x":1,"x":2}}',
            '{"strength_rating":0.5,"weakest_point":"a","weakest_point":"b"}',
        ]
        for text in texts:
            with self.subTest(text=text):
                self.assertFalse(self.assess(text)["rating_usable"])

    def test_malformed_multiple_or_nonobject_json_is_not_repaired(self):
        valid = '{"strength_rating":0.5}'
        invalid = [valid + valid, "Here is the answer: " + valid, valid + " trailing",
                   "[" + valid + "]", "0.5", "null", "{}", '{"strength_rating":',
                   "```json\n" + valid + "\n```\n```json\n" + valid + "\n```"]
        for text in invalid:
            with self.subTest(text=text):
                self.assertFalse(self.assess(text)["rating_usable"])

    def test_complete_json_in_truncated_generation_remains_unusable(self):
        result = self.assess(self.complete, complete=False)
        self.assertTrue(result["schema_conformant"])
        self.assertTrue(result["rating_field_valid"])
        self.assertFalse(result["rating_usable"])
        self.assertIsNone(result["strength_rating"])
        self.assertEqual(result["unusable_reasons"], ["incomplete_generation"])

    def test_completion_status_must_be_explicit_boolean(self):
        for value in (None, "STOP", 1, 0):
            with self.subTest(value=value), self.assertRaises(TypeError):
                assess_response(json.dumps(self.complete), generation_complete=value)
        with self.assertRaises(TypeError):
            assess_response(json.dumps(self.complete))
        self.assertFalse(assess_response(None, generation_complete=True)["rating_usable"])


if __name__ == "__main__":
    unittest.main()
