# Makefile for Agent Orchestrator Docker Operations

.PHONY: help build start stop restart logs health test clean

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Agent Orchestrator - Docker Commands"
	@echo "====================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

build: ## Build all Docker images
	@echo "Building Docker images..."
	docker-compose build
	@echo "✅ Build complete"

start: ## Start all services
	@echo "Starting services..."
	docker-compose up -d
	@sleep 3
	@docker-compose ps
	@echo "✅ Services started"
	@echo ""
	@echo "Gateway: http://localhost:8585"

stop: ## Stop all services
	@echo "Stopping services..."
	docker-compose down
	@echo "✅ Services stopped"

restart: ## Restart all services
	@echo "Restarting services..."
	docker-compose restart
	@echo "✅ Services restarted"

logs: ## View logs from all services
	docker-compose logs -f

logs-gateway: ## View gateway logs
	docker-compose logs -f model-gateway

logs-orchestrator: ## View orchestrator logs
	docker-compose logs -f orchestrator

health: ## Check health of all services
	@./docker/docker-health.sh

test: ## Run interactive test
	@echo "Starting interactive test..."
	docker-compose --profile interactive up interactive-test

test-gateway: ## Run gateway tests
	docker-compose run --rm interactive-test python3 test_gateway.py

test-retry: ## Run retry logic tests
	docker-compose run --rm interactive-test python3 test_gateway_retry.py

test-fallback: ## Run fallback tests
	docker-compose run --rm interactive-test python3 test_gateway_fallback.py

shell-gateway: ## Open shell in gateway container
	docker-compose exec model-gateway /bin/bash

shell-orchestrator: ## Open shell in orchestrator container
	docker-compose exec orchestrator /bin/bash

clean: ## Remove all containers, volumes, and images
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --rmi all
	@echo "✅ Cleanup complete"

clean-logs: ## Remove log volumes
	docker volume rm model-gateway-logs 2>/dev/null || true
	@echo "✅ Logs cleaned"

rebuild: clean build ## Clean and rebuild all images
	@echo "✅ Rebuild complete"

prod-start: ## Start services in production mode
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "✅ Production services started"

prod-stop: ## Stop production services
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
	@echo "✅ Production services stopped"

ps: ## Show status of all containers
	docker-compose ps

stats: ## Show resource usage
	docker stats

env-check: ## Check environment variables
	@echo "Checking environment configuration..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		echo "Run: cp .env.docker .env"; \
		exit 1; \
	fi
	@echo "✅ .env file exists"
	@if grep -q "your-anthropic-api-key-here" .env 2>/dev/null; then \
		echo "⚠️  Warning: API keys need to be configured in .env"; \
	else \
		echo "✅ API keys appear to be configured"; \
	fi
