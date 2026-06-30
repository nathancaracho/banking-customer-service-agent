.PHONY: help up down build restart logs status test test-agents test-backend test-identity \
       docs migrate shell-pg clean lint

help: ## Mostra todos os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Subir todos os serviços
	docker compose up -d

down: ## Parar todos os serviços
	docker compose down

build: ## Rebuild imagens Docker
	docker compose build

restart: ## Reiniciar todos os serviços
	docker compose restart

logs: ## Logs de todos os serviços (follow)
	docker compose logs -f

logs-agents: ## Logs do agents
	docker compose logs -f agents

logs-backend: ## Logs do backend
	docker compose logs -f backend

logs-identity: ## Logs do identity
	docker compose logs -f identity

status: ## Status dos serviços
	docker compose ps

test: test-agents test-backend test-identity ## Rodar todos os testes

test-agents: ## Testes do agents
	cd agents && uv run python -m pytest tests/ -v

test-backend: ## Testes do backend
	cd backend && uv run python -m pytest tests/ -v

test-identity: ## Testes do identity
	cd identity && uv run python -m pytest tests/ -v

docs: ## Servir documentação MkDocs (http://localhost:8080)
	cd docs && uv run mkdocs serve -a 127.0.0.1:8080

docs-build: ## Build da documentação
	cd docs && uv run mkdocs build

migrate: ## Rodar migrations do banco (agents, backend, identity)
	cd agents && uv run alembic upgrade head
	cd backend && uv run alembic upgrade head
	cd identity && uv run alembic upgrade head

shell-pg: ## Shell no PostgreSQL
	docker compose exec postgres psql -U app -d app

shell-pg-agents: ## Shell no schema agents
	docker compose exec postgres psql -U app -d app -c "SET search_path TO agents;"

shell-pg-backend: ## Shell no schema backend
	docker compose exec postgres psql -U app -d app -c "SET search_path TO backend;"

shell-pg-identity: ## Shell no schema identity
	docker compose exec postgres psql -U app -d app -c "SET search_path TO identity;"

shell-rabbitmq: ## Shell no RabbitMQ admin
	@echo "Acesse http://localhost:15672 (guest/guest)"

clean: ## Limpar volumes e caches
	docker compose down -v
	docker system prune -f

deps: ## Instalar dependências de todos os projetos
	cd agents && uv sync
	cd backend && uv sync
	cd identity && uv sync
	cd docs && uv sync

env: ## Copiar .env.example para .env (não sobrescreve)
	@test -f .env || cp .env.example .env && echo ".env criado. Edite com suas credenciais."

open-backend: ## Abrir Swagger do Backend
	@open http://localhost:8200/docs

open-identity: ## Abrir Swagger do Identity
	@open http://localhost:8100/docs

open-banking: ## Abrir Swagger da Banking API
	@open http://localhost:8300/docs

open-signoz: ## Abrir SigNoz
	@open http://localhost:3301

open-rabbitmq: ## Abrir RabbitMQ Admin
	@open http://localhost:15672
