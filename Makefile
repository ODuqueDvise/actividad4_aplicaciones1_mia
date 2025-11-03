# Makefile para tareas comunes del proyecto mortalidad-colombia-2019
# Objetivos principales:
#  - venv: crea/actualiza el entorno virtual usando Python 3.12 (o el siguiente disponible).
#  - dev-install: instala dependencias y el paquete en modo editable.
#  - run: ejecuta la aplicación Dash con las dependencias ya instaladas.
#  - clean-venv: elimina por completo el entorno virtual.
#  - doctor: imprime información de la versión y arquitectura de Python utilizada.

SHELL := /bin/bash
PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
VENV := $(PROJECT_ROOT)/.venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTHON := $(VENV_BIN)/python
PYTHON_CANDIDATES := /opt/homebrew/bin/python3.12 python3.12 python3
PYTHON_BIN := $(firstword $(foreach p,$(PYTHON_CANDIDATES),$(shell command -v $(p) 2>/dev/null)))

ifeq ($(PYTHON_BIN),)
$(error No se encontró un intérprete de Python 3.12+; instala Python 3.12 (recomendado) o ajusta PYTHON_CANDIDATES)
endif

.PHONY: venv dev-install run clean-venv doctor ingest validate format lint typecheck test pre-commit

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo ">> Creando entorno virtual con $(PYTHON_BIN)"; \
		"$(PYTHON_BIN)" -m venv "$(VENV)"; \
	else \
		echo ">> Entorno virtual ya existe ($(VENV))"; \
	fi

dev-install: venv
	@if [ ! -d "$(VENV_BIN)" ]; then \
		echo ">> Entorno virtual no encontrado; ejecuta 'make venv'"; \
		exit 1; \
	fi
	@echo ">> Instalando/actualizando pip, setuptools y wheel"
	@"$(PIP)" install --upgrade pip setuptools wheel
	@echo ">> Instalando dependencias del proyecto"
	@"$(PIP)" install -r requirements.txt
	@echo ">> Instalando mortalidad-colombia-2019 en modo editable"
	@"$(PIP)" install -e .

run:
	@if [ ! -d "$(VENV_BIN)" ]; then \
		echo ">> Entorno virtual ausente; ejecutando 'make dev-install'"; \
		$(MAKE) --no-print-directory dev-install; \
	fi
	@if ! "$(PYTHON)" -c "import mortalidad" >/dev/null 2>&1; then \
		echo ">> Instalando paquete mortalidad (ejecutando 'make dev-install')"; \
		$(MAKE) --no-print-directory dev-install; \
	fi
	@echo ">> Iniciando aplicación Dash (http://localhost:8050)"
	@PYTHONPATH="$(PROJECT_ROOT)/src" "$(PYTHON)" -m mortalidad.app

ingest: dev-install
	@if [ ! -d "$(VENV_BIN)" ]; then \
		echo ">> Entorno virtual ausente; ejecutando 'make dev-install'"; \
		$(MAKE) --no-print-directory dev-install; \
	fi
	@echo ">> Ejecutando pipeline de ingestión"
	@PYTHONPATH="$(PROJECT_ROOT)/src" "$(PYTHON)" -m mortalidad.cli ingest

validate: dev-install
	@if [ ! -d "$(VENV_BIN)" ]; then \
		echo ">> Entorno virtual ausente; ejecutando 'make dev-install'"; \
		$(MAKE) --no-print-directory dev-install; \
	fi
	@echo ">> Validando dataset procesado"
	@PYTHONPATH="$(PROJECT_ROOT)/src" "$(PYTHON)" -m mortalidad.cli validate

format: venv
	@if [ ! -d "$(VENV_BIN)" ]; then \
		echo ">> Entorno virtual ausente; ejecuta 'make venv' o 'make dev-install' primero"; \
		exit 1; \
	fi
	@if ! "$(PYTHON)" -m isort --version >/dev/null 2>&1; then \
		echo ">> isort no está instalado en el entorno virtual; ejecuta 'make dev-install' con acceso a red"; \
		exit 1; \
	fi
	@if ! "$(PYTHON)" -m black --version >/dev/null 2>&1; then \
		echo ">> black no está instalado en el entorno virtual; ejecuta 'make dev-install' con acceso a red"; \
		exit 1; \
	fi
	@echo ">> Formateando con isort y black"
	@"$(PYTHON)" -m isort src tests
	@"$(PYTHON)" -m black src tests

lint: venv
	@if [ ! -d "$(VENV_BIN)" ]; then \
		echo ">> Entorno virtual ausente; ejecuta 'make venv' o 'make dev-install' primero"; \
		exit 1; \
	fi
	@if ! "$(PYTHON)" -m ruff --version >/dev/null 2>&1; then \
		echo ">> Ruff no está instalado en el entorno virtual; ejecuta 'make dev-install' con acceso a red"; \
		exit 1; \
	fi
	@echo ">> Ejecutando Ruff"
	@"$(PYTHON)" -m ruff check src tests

typecheck: dev-install
	@echo ">> Ejecutando mypy"
	@"$(PYTHON)" -m mypy src

test: dev-install
	@echo ">> Ejecutando pytest"
	@"$(PYTHON)" -m pytest

pre-commit: dev-install
	@echo ">> Instalando hooks de pre-commit"
	@"$(PYTHON)" -m pre_commit install

clean-venv:
	@if [ -d "$(VENV)" ]; then \
		echo ">> Eliminando entorno virtual $(VENV)"; \
		rm -rf "$(VENV)"; \
	else \
		echo ">> No se encontró entorno virtual que limpiar"; \
	fi

doctor:
	@echo ">> Diagnóstico del entorno"
	@echo "   Python candidato: $(PYTHON_BIN)"
	@"$(PYTHON_BIN)" -c 'import platform, sys; print(f"   Version: {platform.python_version()} ({platform.architecture()[0]})"); print(f"   Implementacion: {platform.python_implementation()}"); print(f"   Plataforma: {platform.system()} {platform.machine()}"); print(f"   Ruta executable: {sys.executable}")'
