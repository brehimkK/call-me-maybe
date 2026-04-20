.PHONY: install run test lint

install:
	uv sync

run:
	uv run python -m call_me_maybe

test:
	uv run pytest

lint:
	uv run python -m py_compile src/call_me_maybe/*.py