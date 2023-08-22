app: app/* pyproject.toml
	@echo "Building tutorial..."
	@cd app && make start

database: app/* pyproject.toml
	@echo "Building database..."
	@cd app && make database

shutdown:
	@echo "Shutting down tutorial assets..."
	@cd app && make shutdown

test:
	@echo "Running tests..."
	@pytest
	@mypy impulse_core

build:
	@echo "Building package..."
	@poetry build

install: impulse_core/* pyproject.toml
	@pip install .

clean:
	@ echo "Cleaning up..."
	@ rm -rf .venv dist .mypy_cache .pytest_cache impulse_core/__pycache__ 
	@ rm -rf app/database/.mdblogs app/.web
	@ rm -rf .impulselogs