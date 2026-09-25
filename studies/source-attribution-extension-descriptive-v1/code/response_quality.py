"""Author-approved rating usability policy, 2026-09-24; no API or pilot writes.

This is the prospective confirmation parser. The historical strict parser in
design.parse_rating remains unchanged. Integration into the future confirmation
runner must supply generation_complete from the provider's termination status;
a parseable JSON object alone never establishes completion.
"""

import json
import math
import re

from design import RATING_KEYS, duplicate_guard


POLICY = "rating-usability-v1"
EXPLANATION_KEYS = tuple(sorted(RATING_KEYS - {"strength_rating"}))


def _reject_constant(value):
    raise ValueError("Non-finite JSON constant")


def assess_response(text, *, generation_complete):
    """Extract only the designated rating and report schema deviations separately.

    Missing or invalid explanations and additional fields do not exclude a valid
    primary rating. Duplicate keys (including nested ones), malformed JSON,
    non-object JSON, invalid ratings, and incomplete generations do exclude it.
    One complete Markdown JSON fence is accepted, as in the pilot; surrounding
    prose and multiple objects are not repaired. Raw responses must be retained
    by the caller. No alternate rating or prose is used to replace the field.
    """
    if type(generation_complete) is not bool:
        raise TypeError("generation_complete must be an explicit boolean")
    result = {
        "policy": POLICY,
        "generation_complete": generation_complete,
        "rating_usable": False,
        "strength_rating": None,
        "json_object_readable": False,
        "rating_field_valid": None,
        "schema_conformant": False,
        "additional_fields": None,
        "missing_explanations": None,
        "invalid_explanations": None,
        "parse_issue": None,
        "unusable_reasons": [] if generation_complete else ["incomplete_generation"],
    }

    def unreadable(issue):
        result["parse_issue"] = issue
        result["unusable_reasons"].append(issue)
        return result

    if not isinstance(text, str):
        return unreadable("non_text_response")
    text = text.strip()
    if text.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.S)
        if not match:
            return unreadable("invalid_json_wrapper")
        text = match.group(1)
    try:
        data = json.loads(text, object_pairs_hook=duplicate_guard,
                          parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return unreadable("invalid_json_or_duplicate_keys")
    if not isinstance(data, dict):
        return unreadable("json_not_object")

    result["json_object_readable"] = True
    result["additional_fields"] = sorted(set(data) - RATING_KEYS)
    result["missing_explanations"] = [key for key in EXPLANATION_KEYS if key not in data]
    result["invalid_explanations"] = [
        key for key in EXPLANATION_KEYS if key in data
        and (not isinstance(data[key], str) or not data[key].strip())
    ]
    score = data.get("strength_rating")
    # Check bounds before math.isfinite so an enormous JSON integer cannot cause
    # an OverflowError during conversion to a C double.
    valid = (not isinstance(score, bool) and isinstance(score, (int, float))
             and 0 <= score <= 1 and math.isfinite(score))
    result["rating_field_valid"] = valid
    result["schema_conformant"] = bool(
        valid and not result["additional_fields"]
        and not result["missing_explanations"]
        and not result["invalid_explanations"]
    )
    if not valid:
        result["unusable_reasons"].append(
            "missing_strength_rating" if "strength_rating" not in data else "invalid_strength_rating"
        )
    elif generation_complete:
        result["rating_usable"] = True
        result["strength_rating"] = score
    return result
