check:
	ruff format
	ruff check --fix
	uv run pyright
	uv run pytest
