import pytest
from app import main


def test_extract_json_from_code_fence():
    """
    Test extracting JSON from triple-backtick code fence.
    """
    txt = "Here you go:\n```json\n[\n  \"A\",\n  \"B\"\n]\n```"
    res = main._extract_json_from_text(txt)
    assert res == ["A", "B"]


def test_extract_json_embedded_object():
    """
    Test extracting JSON embedded in text.
    """
    txt = "Some text before {\"k\": [1,2,3]} and after"
    res = main._extract_json_from_text(txt)
    assert isinstance(res, dict)
    assert res["k"] == [1, 2, 3]


def test_extract_none_on_non_json():
    """
    Test extracting JSON embedded in text.
    """
    txt = "No json here, just text."
    res = main._extract_json_from_text(txt)
    assert res is None


def test_normalize_recurses_and_parses():
    """
    Test normalizing a state object, parsing JSON strings where possible.
    """
    state = {
        "interests": "I like design",
        "industries": "```json\n[\"A\", \"B\"]\n```",
        "nested": {
            "jobs": "[\"J1\", \"J2\"]"
        }
    }
    norm = main._normalize(state)
    assert isinstance(norm["industries"], list)
    assert norm["industries"] == ["A", "B"]
    assert isinstance(norm["nested"]["jobs"], list)
    assert norm["nested"]["jobs"] == ["J1", "J2"]
