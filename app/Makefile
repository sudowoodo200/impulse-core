start: *
	@echo "Starting application..."
	@docker-compose up -d

database:
	@echo "Starting database..."
	@docker-compose up -d mongo mongo-express

shutdown: ./docker-compose.yml
	@echo "Shutting down database..."
	@docker-compose down
