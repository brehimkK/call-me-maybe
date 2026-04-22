from typing import Any
from .models import ParsedInput, NormalizedSchema
from .errors import SchemaError


CANONICAL_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}

TYPE_ALIASES = {
    "str": "string",
    "string": "string",
    "float": "number",
    "double": "number",
    "number": "number",
    "int": "integer",
    "integer": "integer",
    "bool": "boolean",
    "boolean": "boolean",
    "list": "array",
    "array": "array",
    "dict": "object",
    "object": "object",
    "none": "null",
    "null": "null",
}


def normalize(parsed: ParsedInput) -> NormalizedSchema:
    try:
        if parsed.metadata is None:
            raise SchemaError("metadata is missing")

        functions = parsed.metadata.get("functions")

        if functions is None:
            raise SchemaError("there's no functions in metadata")

        if not isinstance(functions, list):
            raise SchemaError("functions must be a list")

        normalized_functions = []

        for i, fn in enumerate(functions):
            normalized_fn = _normalize_function(fn, i)
            normalized_functions.append(normalized_fn)

        normalized_functions.sort(key=lambda f: f["name"])

        return NormalizedSchema(functions=normalized_functions)

    except SchemaError as e:
        raise SchemaError(f"Normalization failed: {e}") from e
    

def _extract_functions(parsed: ParsedInput) -> list[dict[str, Any]]:
    ...


def _normalize_function(fn: dict[str, Any], index: int) -> dict[str, Any]:
    ...


def _normalize_parameters(parameters: Any, fn_name: str) -> dict[str, dict[str, Any]]:
    ...


def _normalize_type(type_value: Any, context: str) -> str:
    ...