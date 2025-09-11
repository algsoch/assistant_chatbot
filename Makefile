# Makefile for Vicky Chatbot Docker Management

.PHONY: help build run stop clean logs shell test

# Default target
help:
	@echo "Vicky Chatbot Docker Commands:"
	@echo "  build     - Build the Docker image"
	@echo "  run       - Run the application with docker-compose"
	@echo "  run-prod  - Run with nginx reverse proxy"
	@echo "  stop      - Stop all running containers"
	@echo "  restart   - Restart the application"
	@echo "  clean     - Remove containers and images"
	@echo "  logs      - View application logs"
	@echo "  shell     - Access container shell"
	@echo "  test      - Run tests in container"
	@echo "  push      - Build and push to registry"

# Build the Docker image
build:
	docker-compose build --no-cache

# Run the application in development mode
run:
	docker-compose up -d
	@echo "Application running at http://localhost:8000"

# Run with nginx reverse proxy for production
run-prod:
	docker-compose --profile production up -d
	@echo "Application running at http://localhost"

# Stop all containers
stop:
	docker-compose down

# Restart the application
restart: stop run

# Clean up containers and images
clean:
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f

# View logs
logs:
	docker-compose logs -f vicky-app

# Access container shell
shell:
	docker-compose exec vicky-app bash

# Run tests inside container
test:
	docker-compose exec vicky-app python -m pytest

# Build and push to registry (customize registry URL)
push:
	docker build -t vicky-chatbot:latest .
	# docker tag vicky-chatbot:latest your-registry/vicky-chatbot:latest
	# docker push your-registry/vicky-chatbot:latest

# Development: run with file watching
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Check application health
health:
	curl -f http://localhost:8000/api/info || echo "Application not responding"
