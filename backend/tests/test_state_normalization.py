from app.utils.normalization import normalize_state


def test_code_fenced_json_parses():
    raw = {
        "skills": "Here are the skills:\n```json\n{\"hard_skills\": [\"Python\", \"SQL\"], \"soft_skills\": [\"communication\"]}\n```"
    }
    normalized = normalize_state(raw)
    assert isinstance(normalized["skills"], dict)
    assert "hard_skills" in normalized["skills"]


def test_plain_json_string_parses():
    raw = {"interests": '{"a": 1, "b": [2,3]}'}
    normalized = normalize_state(raw)
    assert isinstance(normalized["interests"], dict)
    assert normalized["interests"]["a"] == 1


def test_non_json_string_unchanged():
    raw = {"note": "I like gardening and reading."}
    normalized = normalize_state(raw)
    assert normalized["note"] == raw["note"]
