all: start_database config_venv install_requirements install_impulse

start_database: ../app/database/mongo.yml
	@echo "Starting database..."
	@docker-compose -f ../app/database/mongo.yml up -d

config_venv: 
	@echo "Starting virtual environment..."
	@cd .. && if [ ! -d ".venv" ]; then python3 -m venv .venv; fi

install_requirements: requirements.txt
	@echo "Installing requirements..."
	@. ../.venv/bin/activate; \
		pip install ipykernel -U --force-reinstall; \
		pip install -r requirements.txt --force-reinstall;

install_impulse: ../impulse_core/* ../pyproject.toml
	@. ../.venv/bin/activate; \
		cd .. && pip install --no-cache-dir --force-reinstall .;