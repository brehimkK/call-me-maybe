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
    - InputParseError for file read errors, invalid input type,
      or malformed JSON
    """

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

    if raw is None:
        raise InputParseError("Failed to load input")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputParseError(
            f"Invalid JSON at line {e.lineno}, column {e.colno}"
        ) from e

    validate_structure(data)

    return ParsedInput(
        raw_text=data["prompt"],
        intent="",
        entities={},
        metadata={"functions": data["functions"]}
    )


def validate_structure(data: Any) -> None:
    if not isinstance(data, dict):
        raise InputParseError("Top-level JSON must be an object/dict")

    if "prompt" not in data:
        raise InputParseError("Missing prompt")

    if "functions" not in data:
        raise InputParseError("Missing functions")

    prompt = data["prompt"]
    functions = data["functions"]

    if not isinstance(prompt, str):
        raise InputParseError("prompt must be string")

    if not isinstance(functions, list):
        raise InputParseError("functions must be list")

    for fn in functions:
        if not isinstance(fn, dict):
            raise InputParseError("Each function must be an object/dict")
