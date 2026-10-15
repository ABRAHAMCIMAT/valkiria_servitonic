.DEFAULT_GOAL := help
PY := python3
PIP := $(PY) -m pip

.PHONY: help install dev test test-unit test-int test-e2e cov lint fmt typecheck \
        security security-live ci docker-build up down logs clean poc-up poc-down poc-logs \
        gcp-init gcp-plan gcp-apply teams-app

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:  ## Instala dependencias de produccion
	$(PIP) install -r requirements.txt

dev:  ## Instala dependencias de desarrollo
	$(PIP) install -r requirements-dev.txt

test:  ## Ejecuta todas las pruebas
	pytest

test-unit:  ## Solo pruebas unitarias
	pytest -m unit

test-int:  ## Solo pruebas de integracion
	pytest -m integration

test-e2e:  ## Solo pruebas end-to-end
	pytest -m e2e

cov:  ## Pruebas con cobertura HTML
	pytest --cov=backend --cov-report=html --cov-report=term-missing
	@echo "Reporte: htmlcov/index.html"

lint:  ## Lint con ruff
	ruff check backend tests scripts

fmt:  ## Formatea el codigo
	ruff format backend tests scripts
	ruff check --fix backend tests scripts

typecheck:  ## Verificacion de tipos
	mypy backend

security:  ## Auditoria de seguridad
	bandit -r backend -ll -x backend/observability/langfuse_integration.py
	pip-audit -r requirements.txt

security-live:  ## Pruebas basicas contra BASE_URL desplegada
	$(PY) scripts/security_smoke.py --base-url "$(BASE_URL)" --allowed-origin "$(ALLOWED_ORIGIN)"

ci: lint typecheck test security  ## Puerta local equivalente al pipeline CI (sin Docker/Sonar)

docker-build:  ## Construye la imagen
	docker compose build

up:  ## Levanta el stack (Docker)
	docker compose up -d
	@echo "API: http://localhost:8000"

down:  ## Detiene el stack (Docker)
	docker compose down

local-up:  ## Despliega en local con un solo comando (venv + deps + server, modo demo)
	./scripts/deploy_local.sh

local-down:  ## Detiene el servidor levantado por local-up
	./scripts/deploy_local.sh --stop

poc-up:  ## Levanta PoC local ServiceTonic + Teams usando .env.poc
	./scripts/run_poc_local.sh up

poc-down:  ## Detiene PoC local
	./scripts/run_poc_local.sh down

poc-logs:  ## Sigue logs del PoC local
	./scripts/run_poc_local.sh logs

# --- Google Cloud (Fase 2). ENV=dev|prod; ver docs/DESPLIEGUE_GCP.md ---
ENV ?= dev
TF := terraform -chdir=infra/terraform

gcp-init:  ## Terraform init con el estado remoto del entorno (ENV=dev|prod)
	$(TF) init -reconfigure -backend-config=envs/$(ENV).backend.hcl

gcp-plan:  ## Terraform plan del entorno (ENV=dev|prod)
	$(TF) plan -var-file=envs/$(ENV).tfvars -out=$(ENV).tfplan

gcp-apply:  ## Aplica el plan generado por gcp-plan
	$(TF) apply $(ENV).tfplan

teams-app:  ## Empaqueta la app de Teams (requiere TEAMS_BOT_APP_ID, TEAMS_APP_DEVELOPER, TEAMS_APP_WEBSITE)
	./scripts/package_teams_app.sh

logs:  ## Sigue los logs
	docker compose logs -f api

clean:  ## Limpia artefactos
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
