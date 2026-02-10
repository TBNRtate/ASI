.PHONY: fmt lint type test

fmt:
	ruff format src tests

lint:
	ruff check src tests

type:
	mypy src

test:
	pytest -q
