.PHONY: dev down restart logs db-shell migrate migrate-create seed etl test install lint help

COMPOSE_FILE := infra/docker-compose.yml
BACKEND_DIR  := backend
PYTHON       := .venv/Scripts/python
PYTEST       := .venv/Scripts/pytest
ALEMBIC      := .venv/Scripts/alembic

# ── Infraestructura Docker ────────────────────────────────────────────────────

dev:
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "DB en localhost:5432  |  Redis en localhost:6379"

down:
	docker compose -f $(COMPOSE_FILE) down

restart:
	docker compose -f $(COMPOSE_FILE) down && docker compose -f $(COMPOSE_FILE) up -d

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

db-shell:
	docker exec -it geodata_predik_db_dev psql -U admin -d geodata_predik_clone

# ── Backend Python ────────────────────────────────────────────────────────────

install:
	python -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements.txt

run:
	cd $(BACKEND_DIR) && ../$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	cd $(BACKEND_DIR) && ../$(ALEMBIC) upgrade head

migrate-down:
	cd $(BACKEND_DIR) && ../$(ALEMBIC) downgrade -1

migrate-create:
	@read -p "Nombre de la migración: " name; \
	cd $(BACKEND_DIR) && ../$(ALEMBIC) revision --autogenerate -m "$$name"

seed:
	$(PYTHON) $(BACKEND_DIR)/scripts/seed_dev.py

etl:
	$(PYTHON) $(BACKEND_DIR)/scripts/run_etl.py $(ETL_ARGS)

# ── Tests y calidad ───────────────────────────────────────────────────────────

test:
	cd $(BACKEND_DIR) && ../$(PYTEST) tests/ -v

test-cov:
	cd $(BACKEND_DIR) && ../$(PYTEST) tests/ -v --cov=app --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check $(BACKEND_DIR)/app $(BACKEND_DIR)/tests

# ── Ayuda ─────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Comandos disponibles:"
	@echo "  make dev           Levanta PostgreSQL+PostGIS y Redis en Docker"
	@echo "  make down          Detiene los contenedores"
	@echo "  make restart       Reinicia los contenedores"
	@echo "  make logs          Muestra logs en tiempo real"
	@echo "  make db-shell      Abre psql dentro del contenedor"
	@echo "  make install       Crea .venv e instala dependencias"
	@echo "  make run           Levanta la API FastAPI en modo desarrollo"
	@echo "  make migrate       Aplica todas las migraciones pendientes"
	@echo "  make migrate-down  Revierte la última migración"
	@echo "  make migrate-create Crea una nueva migración (pide nombre)"
	@echo "  make test          Corre la suite de tests"
	@echo "  make test-cov      Tests con reporte de cobertura"
	@echo "  make seed          Inserta org y usuario admin de desarrollo en la DB"
	@echo "  make etl           Corre ETL (ETL_ARGS='--source inegi_denue --estado 09 --max-records 500')"
	@echo "  make lint          Revisa estilo con ruff"
	@echo ""
