import json
import pytest

from call_me_maybe.models import ParsedInput
from call_me_maybe.normalizer import normalize
from call_me_maybe.errors import SchemaError


def _to_bytes(schema) -> bytes:
    return json.dumps(
        schema.model_dump(),
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")


def test_stable_output_across_field_order_variations():
    parsed_a = ParsedInput(
        raw_text="sum two numbers",
        intent="",
        entities={},
        metadata={
            "functions": [
                {
                    "name": "fn_add_numbers",
                    "description": "Add two numbers",
                    "parameters": {
                        "b": {"type": "int", "required": False},
                        "a": {"type": "int"},
                    },
                    "returns": {"type": "int"},
                },
                {
                    "name": "fn_greet",
                    "description": "Greet a user",
                    "parameters": {
                        "name": {"type": "str"},
                    },
                    "returns": "string",
                },
            ]
        },
    )

    parsed_b = ParsedInput(
        raw_text="sum two numbers",
        intent="",
        entities={},
        metadata={
            "functions": [
                {
                    "returns": "string",
                    "parameters": {
                        "name": {"type": "string"},
                    },
                    "description": "Greet a user",
                    "name": "fn_greet",
                },
                {
                    "parameters": {
                        "a": {"type": "integer"},
                        "b": {"required": False, "type": "integer"},
                    },
                    "name": "fn_add_numbers",
                    "returns": {"type": "integer"},
                    "description": "Add two numbers",
                },
            ]
        },
    )

    norm_a = normalize(parsed_a)
    norm_b = normalize(parsed_b)

    assert _to_bytes(norm_a) == _to_bytes(norm_b)


def test_type_normalization_aliases():
    parsed = ParsedInput(
        raw_text="types",
        intent="",
        entities={},
        metadata={
            "functions": [
                {
                    "name": "fn_types",
                    "description": "normalize aliases",
                    "parameters": {
                        "s": {"type": "str"},
                        "i": {"type": "int"},
                        "n": {"type": "float"},
                        "b": {"type": "bool"},
                        "arr": {"type": "list"},
                        "obj": {"type": "dict"},
                    },
                    "returns": {"type": "string"},
                }
            ]
        },
    )

    norm = normalize(parsed)
    fn = norm.functions[0]

    by_name = {p.name: p.type for p in fn.parameters}
    assert by_name["s"] == "string"
    assert by_name["i"] == "integer"
    assert by_name["n"] == "number"
    assert by_name["b"] == "boolean"
    assert by_name["arr"] == "array"
    assert by_name["obj"] == "object"


def test_unsupported_type_rejected_with_offending_type_in_message():
    parsed = ParsedInput(
        raw_text="bad type",
        intent="",
        entities={},
        metadata={
            "functions": [
                {
                    "name": "fn_bad",
                    "description": "bad",
                    "parameters": {
                        "when": {"type": "datetime"},
                    },
                    "returns": {"type": "string"},
                }
            ]
        },
    )

    with pytest.raises(SchemaError, match="datetime"):
        normalize(parsed)


def test_optional_parameter_fields_preserved():
    parsed = ParsedInput(
        raw_text="optional fields",
        intent="",
        entities={},
        metadata={
            "functions": [
                {
                    "name": "fn_substitute",
                    "description": "Substitute with regex",
                    "parameters": {
                        "replacement": {
                            "type": "str",
                            "required": False,
                            "description": "Replacement token",
                            "default": "NUMBERS",
                            "enum": ["NUMBERS", "MASKED"],
                        }
                    },
                    "returns": {"type": "string"},
                }
            ]
        },
    )

    norm = normalize(parsed)
    p = norm.functions[0].parameters[0]

    assert p.name == "replacement"
    assert p.type == "string"
    assert p.required is False
    assert p.description == "Replacement token"
    assert p.default == "NUMBERS"
    assert p.enum == ["NUMBERS", "MASKED"]


def test_required_defaults_to_true():
    parsed = ParsedInput(
        raw_text="required default",
        intent="",
        entities={},
        metadata={
            "functions": [
                {
                    "name": "fn_greet",
                    "description": "Greet",
                    "parameters": {
                        "name": {"type": "str"}  # required omitted
                    },
                    "returns": {"type": "string"},
                }
            ]
        },
    )

    norm = normalize(parsed)
    param = norm.functions[0].parameters[0]
    assert param.required is True