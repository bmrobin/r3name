check:
	ruff format
	ruff check --fix
	ty check
	uv run pytest
