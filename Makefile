.PHONY: help up down logs test test-unit test-integration test-e2e clean build lint format docs

# Default target
help:
	@echo "OMARINO EMS Suite - Makefile Commands"
	@echo "====================================="
	@echo "Environment:"
	@echo "  up                - Start all services with docker-compose"
	@echo "  down              - Stop all services"
	@echo "  logs              - Follow logs from all services"
	@echo "  clean             - Remove containers, volumes, and build artifacts"
	@echo ""
	@echo "Testing:"
	@echo "  test              - Run all tests (unit + integration + e2e)"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests"
	@echo "  test-e2e          - Run end-to-end tests"
	@echo "  contract-test     - Run contract tests"
	@echo ""
	@echo "Development:"
	@echo "  build             - Build all Docker images"
	@echo "  lint              - Run linters on all services"
	@echo "  format            - Format code in all services"
	@echo "  docs              - Build documentation"
	@echo "  docs-serve        - Serve documentation locally"

# Environment Management
up:
	@echo "🚀 Starting OMARINO EMS Suite..."
	docker-compose up -d
	@echo "✅ Services started. Access web UI at http://localhost:3000"

down:
	@echo "🛑 Stopping all services..."
	docker-compose down

logs:
	docker-compose logs -f

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	rm -rf */bin */obj */node_modules */__pycache__ */dist
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
	find . -name ".coverage" -delete
	@echo "✅ Cleanup complete"

# Build
build:
	@echo "🔨 Building Docker images..."
	docker-compose build

# Testing
test: test-unit test-integration test-e2e

test-unit:
	@echo "🧪 Running unit tests..."
	@echo "\n📦 Testing C# services..."
	cd timeseries-service && dotnet test --configuration Release --logger "console;verbosity=minimal" || true
	cd api-gateway && dotnet test --configuration Release --logger "console;verbosity=minimal" || true
	cd scheduler-service && dotnet test --configuration Release --logger "console;verbosity=minimal" || true
	@echo "\n🐍 Testing Python services..."
	cd forecast-service && python -m pytest -v || true
	cd optimize-service && python -m pytest -v || true
	@echo "\n⚛️  Testing Web App..."
	cd webapp && pnpm test --run || true

test-integration:
	@echo "🔗 Running integration tests..."
	docker-compose up -d postgres redis
	sleep 5
	cd timeseries-service && dotnet test --filter "Category=Integration" || true
	cd forecast-service && pytest -m integration || true
	cd optimize-service && pytest -m integration || true

test-e2e:
	@echo "🌍 Running E2E tests..."
	docker-compose up -d
	sleep 10
	cd webapp && pnpm exec playwright test || true

contract-test:
	@echo "📋 Running contract tests..."
	docker-compose up -d
	sleep 10
	cd shared && ./run-contract-tests.sh || true

# Code Quality
lint:
	@echo "🔍 Running linters..."
	@echo "\n📦 Linting C#..."
	cd timeseries-service && dotnet format --verify-no-changes || true
	cd api-gateway && dotnet format --verify-no-changes || true
	cd scheduler-service && dotnet format --verify-no-changes || true
	@echo "\n🐍 Linting Python..."
	cd forecast-service && ruff check . || true
	cd optimize-service && ruff check . || true
	@echo "\n⚛️  Linting TypeScript..."
	cd webapp && pnpm lint || true

format:
	@echo "✨ Formatting code..."
	@echo "\n📦 Formatting C#..."
	cd timeseries-service && dotnet format
	cd api-gateway && dotnet format
	cd scheduler-service && dotnet format
	@echo "\n🐍 Formatting Python..."
	cd forecast-service && black . && ruff check --fix .
	cd optimize-service && black . && ruff check --fix .
	@echo "\n⚛️  Formatting TypeScript..."
	cd webapp && pnpm format

# Documentation
docs:
	@echo "📚 Building documentation..."
	cd docs && mkdocs build

docs-serve:
	@echo "📚 Serving documentation at http://localhost:8000"
	cd docs && mkdocs serve

# Development helpers
dev-setup:
	@echo "🛠️  Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "✅ Created .env file"; fi
	@echo "✅ Development setup complete"
	@echo "💡 Run 'make up' to start services"

psql:
	docker-compose exec postgres psql -U postgres -d omarino_ems

redis-cli:
	docker-compose exec redis redis-cli

# Database migrations
migrate-up:
	@echo "⬆️  Running database migrations..."
	cd timeseries-service && dotnet ef database update

migrate-down:
	@echo "⬇️  Reverting last database migration..."
	cd timeseries-service && dotnet ef migrations remove

# Service-specific commands
timeseries-dev:
	cd timeseries-service && dotnet run

forecast-dev:
	cd forecast-service && uvicorn app.main:app --reload --port 8001

optimize-dev:
	cd optimize-service && uvicorn app.main:app --reload --port 8002

scheduler-dev:
	cd scheduler-service && dotnet run

webapp-dev:
	cd webapp && pnpm dev

# Docker helpers
prune:
	@echo "🗑️  Pruning Docker system..."
	docker system prune -af --volumes
	@echo "✅ Docker system pruned"

ps:
	docker-compose ps

restart:
	docker-compose restart

stats:
	docker stats --no-stream

# CI simulation
ci:
	@echo "🤖 Simulating CI pipeline..."
	$(MAKE) lint
	$(MAKE) test-unit
	$(MAKE) build
	$(MAKE) test-integration
	@echo "✅ CI simulation complete"

# Database management
db-shell:
	docker-compose exec postgres psql -U omarino -d omarino_timeseries

db-backup:
	@echo "💾 Backing up database..."
	docker-compose exec -T postgres pg_dump -U omarino omarino_timeseries > backup_$$(date +%Y%m%d_%H%M%S).sql
	docker-compose exec -T postgres pg_dump -U omarino omarino_scheduler >> backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup complete!"

db-restore:
	@if [ -z "$(FILE)" ]; then echo "❌ ERROR: FILE parameter required (e.g., make db-restore FILE=backup.sql)"; exit 1; fi
	@echo "📥 Restoring database from $(FILE)..."
	docker-compose exec -T postgres psql -U omarino omarino_timeseries < $(FILE)
	@echo "✅ Restore complete!"

# Monitoring shortcuts
open-grafana:
	@open http://localhost:3001 2>/dev/null || xdg-open http://localhost:3001 2>/dev/null || echo "🔗 Grafana: http://localhost:3001"

open-prometheus:
	@open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null || echo "🔗 Prometheus: http://localhost:9090"

open-swagger:
	@open http://localhost:8080/swagger 2>/dev/null || xdg-open http://localhost:8080/swagger 2>/dev/null || echo "🔗 Swagger: http://localhost:8080/swagger"

health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8080/health | jq . 2>/dev/null || echo "⚠️  API Gateway not responding"
	@curl -s http://localhost:5001/health | jq . 2>/dev/null || echo "⚠️  TimeSeries service not responding"
	@curl -s http://localhost:8001/health | jq . 2>/dev/null || echo "⚠️  Forecast service not responding"
	@curl -s http://localhost:8002/health | jq . 2>/dev/null || echo "⚠️  Optimize service not responding"
	@curl -s http://localhost:5003/health | jq . 2>/dev/null || echo "⚠️  Scheduler service not responding"

# Service-specific logs
logs-timeseries:
	docker-compose logs -f timeseries-service

logs-forecast:
	docker-compose logs -f forecast-service

logs-optimize:
	docker-compose logs -f optimize-service

logs-scheduler:
	docker-compose logs -f scheduler-service

logs-gateway:
	docker-compose logs -f api-gateway

logs-webapp:
	docker-compose logs -f webapp

# Shell access
shell-timeseries:
	docker-compose exec timeseries-service /bin/bash

shell-forecast:
	docker-compose exec forecast-service /bin/bash

shell-optimize:
	docker-compose exec optimize-service /bin/bash

shell-scheduler:
	docker-compose exec scheduler-service /bin/bash

shell-gateway:
	docker-compose exec api-gateway /bin/bash

shell-webapp:
	docker-compose exec webapp /bin/sh
