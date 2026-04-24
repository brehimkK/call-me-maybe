import json
from pathlib import Path
from .models import ParsedInput, NormalizedSchema
from .errors import InputParseError
from .normalizer import normalize
from typing import Any


# this function is about to make sure
# (name, description, and param are present)
def load_functions_definition(source: str | Path) -> list[dict[str, Any]]:
    raw = None

    if isinstance(source, Path):
        try:
            raw = source.read_text(encoding="utf-8")
        except Exception as e:
            raise InputParseError(f"Failed to read file: {source}") from e

    elif isinstance(source, str):
        p = Path(source)
        if p.exists() and p.is_file():
            try:
                raw = p.read_text(encoding="utf-8")
            except Exception as e:
                raise InputParseError(f"Failed to read file: {source}") from e
        else:
            raw = source
    else:
        raise InputParseError(f"Invalid input type: {type(source).__name__}")

    try:
        if raw is None:
            raise InputParseError("Failed to load input")

        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputParseError(
            f"Invalid JSON at line {e.lineno}, column {e.colno}"
        ) from e

    if not isinstance(data, list):
        raise InputParseError("Functions definition must be a list")

    for fn in data:
        if not isinstance(fn, dict):
            raise InputParseError("Each function must be a dict")
    return data


# this function parse the the prompt files
def load_prompts(source: str | Path) -> list[str]:
    raw = None

    if isinstance(source, Path):
        try:
            raw = source.read_text(encoding="utf-8")
        except Exception as e:
            raise InputParseError(f"Failed to read file: {source}") from e

    elif isinstance(source, str):
        p = Path(source)
        if p.exists() and p.is_file():
            try:
                raw = p.read_text(encoding="utf-8")
            except Exception as e:
                raise InputParseError(f"Failed to read file: {source}") from e
        else:
            raw = source
    else:
        raise InputParseError(f"Invalid input type: {type(source).__name__}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputParseError(
            f"Invalid JSON at line {e.lineno}, column {e.colno}"
        ) from e

    if not isinstance(data, list):
        raise InputParseError("Prompts must be a list")

    prompts = []

    for item in data:
        if not isinstance(item, dict):
            raise InputParseError("Each prompt must be a dict")

        if "prompt" not in item:
            raise InputParseError("Missing 'prompt' field")

        if not isinstance(item["prompt"], str):
            raise InputParseError("'prompt' must be string")

        prompts.append(item["prompt"])

    return prompts


def normalize_functions(data: list[dict[str, Any]]) -> NormalizedSchema:
    parsed = ParsedInput(
        metadata={"functions": data}
        )
    return normalize(parsed)
