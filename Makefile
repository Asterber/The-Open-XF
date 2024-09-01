lint:
	poetry run ruff check .

lint_fix:
	poetry run ruff check . --fix

sort_imports:
	ruff check --select I --fix

format: sort_imports
	ruff format .

