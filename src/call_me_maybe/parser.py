import json
from pathlib import Path
from typing import Any
from .models import ParsedInput
from .errors import InputParseError


def load_input(source: str | Path) -> ParsedInput:

    """
Loads input from a file path or JSON string.

Supports:
- Path: reads UTF-8 file content
- str: treated as file path if it exists, otherwise raw JSON string

Returns:
- ParsedInput built from decoded JSON

Raises:
- InputParseError for file read errors, invalid input type, or malformed JSON
"""
 
    raw = None

    if isinstance(source, Path):
        try:
            raw = source.read_text(encoding="utf-8")
        except Exception as e:
            raise InputParseError(f"Failed to read file: {source}") from e

    elif isinstance(source, str):
        p = Path(source)
        if p.exists():
            try:
                raw = p.read_text(encoding="utf-8")
            except Exception as e:
                raise InputParseError(f"Failed to read file: {source}") from e
        else:
            raw = source

    else:
        raise InputParseError("Invalid input type")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputParseError(
            f"Invalid JSON at line {e.lineno}, column {e.colno}"
        ) from e

    return ParsedInput(data)


def validate_structure(data: Any):
    if not isinstance(data, dict):
        raise InputParseError("Top-level JSON must be an object/dict")

    if "prompt" not in data:
        raise InputParseError("Missing prompt")

    if "functions" not in data:
        raise InputParseError("Missing functions")

    prompt = data["prompt"]

    if not isinstance(prompt, str):
        raise InputParseError("prompt must be string")

    functions = data["functions"]

    if not isinstance(functions, list):
        raise InputParseError("functions must be list")
    