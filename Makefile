install: impulse_core/* pyproject.toml
	@pip install .

tutorial: tutorial/* pyproject.toml
	@echo "Building tutorial..."
	@cd tutorial && make

shutdown-tutorial:
	@echo "Shutting down tutorial assets..."
	@docker kill tutorial-mongo-1 tutorial-mongo-express-1
	@rm -rf .venv

test:
	@echo "Running tests..."
	@pytest
	@mypy impulse_core