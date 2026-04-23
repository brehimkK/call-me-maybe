import json
import pytest

from src.call_me_maybe.normalizer import normalize
from src.call_me_maybe.models import ParsedInput
from src.call_me_maybe.errors import SchemaError


def _make_input(functions):
    return ParsedInput(metadata={"functions": functions})


def test_deterministic_output_across_order_variations():
    fn1 = {
        "name": "b_func",
        "description": "test",
        "parameters": {
            "y": {"type": "int", "required": False},
            "a": {"type": "str"},
        },
        "returns": {"type": "string"},
    }

    fn2 = {
        "name": "a_func",
        "description": "test",
        "parameters": {
            "b": {"type": "bool"},
            "a": {"type": "int"},
        },
        "returns": {"type": "string"},
    }

    input1 = _make_input([fn1, fn2])
    input2 = _make_input([fn2, fn1])

    out1 = normalize(input1)
    out2 = normalize(input2)

    assert json.dumps(out1.functions, sort_keys=True) == json.dumps(
        out2.functions, sort_keys=True
    )


def test_type_alias_normalization():
    fn = {
        "name": "test_fn",
        "parameters": {
            "a": {"type": "str"},
            "b": {"type": "int"},
            "c": {"type": "float"},
            "d": {"type": "bool"},
        },
        "returns": {"type": "double"},
    }

    result = normalize(_make_input([fn]))

    params = result.functions[0]["parameters"]

    assert params["a"]["type"] == "string"
    assert params["b"]["type"] == "integer"
    assert params["c"]["type"] == "number"
    assert params["d"]["type"] == "boolean"
    assert result.functions[0]["returns"]["type"] == "number"


def test_unsupported_type_raises_schema_error():
    fn = {
        "name": "bad_fn",
        "parameters": {
            "a": {"type": "datetime"},
        },
        "returns": {"type": "string"},
    }

    with pytest.raises(SchemaError) as e:
        normalize(_make_input([fn]))

    assert "datetime" in str(e.value)


def test_optional_fields_preserved():
    fn = {
        "name": "fn",
        "description": "keep me",
        "parameters": {
            "a": {
                "type": "int",
                "required": False,
                "default": 10,
                "enum": [1, 2, 3],
            }
        },
        "returns": {"type": "string"},
    }

    result = normalize(_make_input([fn]))
    param = result.functions[0]["parameters"]["a"]

    assert param["required"] is False
    assert param["default"] == 10
    assert param["enum"] == [1, 2, 3]
    assert param["type"] == "integer"
