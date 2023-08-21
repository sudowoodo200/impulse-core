tutorial: tutorial/* pyproject.toml
	@echo "Building tutorial..."
	@cd tutorial && make

shutdown-tutorial:
	@echo "Shutting down tutorial assets..."
	@docker kill tutorial-mongo-1 tutorial-mongo-express-1
	@rm -rf .venv
	@rm -rf tutorial/.mdblogs tutorial/.locallogs

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
	@ rm -rf dist .mypy_cache .pytest_cache impulse_core/__pycache__ 