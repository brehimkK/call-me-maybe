import json
from pathlib import Path

import pytest

from src.call_me_maybe.parser import load_input
from src.call_me_maybe.parser import InputParseError
from src.call_me_maybe.models import ParsedInput


def test_load_input_valid_from_json_string():
    raw = json.dumps(
        {
            "prompt": "What is the sum of 2 and 3?",
            "functions": [
                {
                    "name": "fn_add_numbers",
                    "description": "Add two numbers together and return their sum.",
                    "parameters": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "returns": {"type": "number"},
                }
            ],
        }
    )

    parsed = load_input(raw)

    assert isinstance(parsed, ParsedInput)
    assert parsed.raw_text == "What is the sum of 2 and 3?"
    assert parsed.metadata["functions"][0]["name"] == "fn_add_numbers"


def test_load_input_valid_from_file(tmp_path: Path):
    payload = {
        "prompt": "Greet john",
        "functions": [
            {
                "name": "fn_greet",
                "description": "Generate a greeting message for a person by name.",
                "parameters": {"name": {"type": "string"}},
                "returns": {"type": "string"},
            }
        ],
    }
    f = tmp_path / "input.json"
    f.write_text(json.dumps(payload), encoding="utf-8")

    parsed = load_input(f)

    assert isinstance(parsed, ParsedInput)
    assert parsed.raw_text == "Greet john"
    assert isinstance(parsed.metadata["functions"], list)
    assert parsed.metadata["functions"][0]["name"] == "fn_greet"


def test_load_input_malformed_json_raises():
    bad = '{"prompt": "hello", "functions": [}'

    with pytest.raises(InputParseError, match="Invalid JSON"):
        load_input(bad)


@pytest.mark.parametrize(
    "payload, expected_msg",
    [
        ({"functions": []}, "Missing prompt"),
        ({"prompt": "hello"}, "Missing functions"),
    ],
)
def test_load_input_missing_required_keys(payload, expected_msg):
    with pytest.raises(InputParseError, match=expected_msg):
        load_input(json.dumps(payload))


@pytest.mark.parametrize(
    "payload, expected_msg",
    [
        ([], "Top-level JSON must be an object/dict"),
        ({"prompt": "hello", "functions": "not-a-list"}, "functions must be list"),
        ({"prompt": 123, "functions": []}, "prompt must be string"),
        (
            {"prompt": "hello", "functions": [123]},
            "Each function must be an object/dict",
        ),
    ],
)
def test_load_input_wrong_types(payload, expected_msg):
    with pytest.raises(InputParseError, match=expected_msg):
        load_input(json.dumps(payload))


def test_load_input_stable_output_same_input_same_result():
    raw = json.dumps(
        {
            "prompt": "Reverse the string 'world'",
            "functions": [
                {
                    "name": "fn_reverse_string",
                    "description": "Reverse a string and return the reversed result.",
                    "parameters": {"s": {"type": "string"}},
                    "returns": {"type": "string"},
                }
            ],
        }
    )

    a = load_input(raw)
    b = load_input(raw)

    assert a == b