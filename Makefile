app: app/* docker-compose.yml pyproject.toml
	@echo "Building app..."
	@docker-compose up

database: docker-compose.yml pyproject.toml
	@echo "Building database..."
	@docker-compose up -d mongo mongo-express

shutdown:
	@echo "Shutting down application assets..."
	@docker-compose down

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
	@ rm -rf app/.next app/node_modules
	@ rm -rf .impulselogs