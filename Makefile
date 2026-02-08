.PHONY: help install dev-up dev-down test clean init-db

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make init-db      - Initialize database tables"
	@echo "  make dev-up       - Start services with Docker Compose"
	@echo "  make dev-down     - Stop services"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean up temporary files"

install:
	pip install -r backend/requirements.txt
	pip install -r microservice/requirements.txt
	pip install -r scripts/requirements.txt

init-db:
	python -m backend.init_db

dev-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services are running!"
	@echo "Backend: http://localhost:8000"
	@echo "Microservice: http://localhost:8001"

dev-down:
	docker-compose down

test:
	pytest backend/tests/
	pytest microservice/tests/

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
