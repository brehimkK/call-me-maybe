from typing import Any
from .models import ParsedInput, NormalizedSchema, FunctionParameter
from .errors import SchemaError


CANONICAL_TYPES = {"string", "number", "integer", "boolean", "array", "object"}

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
}

# The normalizer converts raw parsed data → strict, validated,
# -> structured schema:

# Validate structure
# Enforce rules
# Remove ambiguity
# Produce something safe for downstream use


def normalize(parsed: ParsedInput) -> NormalizedSchema:
    metadata = parsed.metadata

    if not parsed.metadata:
        raise SchemaError("no data provided")

    if not isinstance(metadata, dict):
        raise SchemaError("ParsedInput.metadata must be a dict")

    functions = metadata.get("functions")

    if functions is None or functions == "":
        raise SchemaError("ParsedInput.metadata['functions'] is required")

    if not isinstance(functions, list):
        raise SchemaError(
            "ParsedInput.metadata['functions'] must be a list"
        )

    normalized_functions = []

    for i, fn in enumerate(functions):
        normalized_fn = _normalize_function(fn, i)
        normalized_functions.append(normalized_fn)

    normalized_functions.sort(key=lambda f: f["name"])

    return NormalizedSchema(functions=normalized_functions)


def _normalize_function(fn: Any, index: int) -> dict[str, Any]:
    if not isinstance(fn, dict):
        raise SchemaError(f"Function at index {index} must be a dict")

    name = fn.get("name")

    if not isinstance(name, str) or not name.strip():
        raise SchemaError(f"Function at index {index} has invalid 'name'")
    name = name.strip()

    description = fn.get("description")

    if description is None:
        description = ""

    if not isinstance(description, str):
        raise SchemaError(f"Function '{name}' description must be a string")

    parameters = fn.get("parameters", {})
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise SchemaError(f"Function '{name}' parameters must be a dict")

    normalized_params = _normalize_parameters(parameters, name)

    returns = fn.get("returns")

    if returns is None:
        normalized_return = None

    elif isinstance(returns, dict):
        if "type" not in returns or returns["type"] is None:
            raise SchemaError(f"Function '{name}' missing returns.type")

        normalized_return = _normalize_type(
            returns["type"],
            f"Function '{name}' return"
        )

    elif isinstance(returns, str):
        normalized_return = _normalize_type(
            returns,
            f"Function '{name}' return"
        )

    else:
        raise SchemaError(f"Function '{name}' invalid returns")

    return {
        "name": name,
        "description": description,
        "parameters": normalized_params,
        "returns": normalized_return,
    }


def _normalize_parameters(
    parameters: Any, fn_name: str
) -> list[FunctionParameter]:

    keys = sorted(parameters.keys())

    result = []

    for param_name in keys:
        if not isinstance(param_name, str):
            raise SchemaError(
                f"Function '{fn_name}' parameter"
                f" {param_name} name must be a string"
            )

        if not isinstance(parameters[param_name], dict):
            raise SchemaError(
                f"Function '{fn_name}' parameter '{param_name}' must be a dict"
            )

        param_spec = parameters[param_name]

        if "type" not in param_spec:
            raise SchemaError(
                f"Function '{fn_name}' parameter '{param_name}' missing type"
            )

        if param_spec["type"] is None or param_spec["type"] == "":
            raise SchemaError(
                f"Function '{fn_name}' parameter '{param_name}' missing type"
            )

        normalized_type = _normalize_type(
            param_spec["type"],
            f"Function '{fn_name}' parameter '{param_name}'"
        )

        result.append(FunctionParameter(
            name=param_name,
            type=normalized_type
        ))
    return result


def _normalize_type(type_value: Any, context: str) -> str:
    if not isinstance(type_value, str):
        raise SchemaError(f"{context} type must be a string")

    key = type_value.strip().lower()
    if key == "":
        raise SchemaError(f"{context}: type must not be empty")

    normalized = TYPE_ALIASES.get(key)
    if normalized is None or normalized not in CANONICAL_TYPES:
        raise SchemaError(f"{context}: Unsupported type: {type_value}")
    return normalized
