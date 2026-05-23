.PHONY: clean check

clean:
	rm -rf dist/
	rm -rf **/*.egg-info


check: clean
	uv run ruff format
	uv run ruff check --fix
	uv run pyright
	uv run pytest
