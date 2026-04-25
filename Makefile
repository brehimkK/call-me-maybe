.PHONY: install run test lint debug clean

install:
	uv sync

run:
	uv run python -m call_me_maybe

test:
	uv run pytest

lint:
	uv run flake8 .
	uv run mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

debug:
	uv run python -m pdb -m call_me_maybe

clean:
	rm -rf __pycache__ .mypy_cache