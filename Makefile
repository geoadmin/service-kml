SHELL = /bin/bash

.DEFAULT_GOAL := help

SERVICE_NAME := service-kml

CURRENT_DIR := $(shell pwd)

# Docker metadata
GIT_HASH = `git rev-parse HEAD`
GIT_HASH_SHORT = `git rev-parse --short HEAD`
GIT_BRANCH = `git symbolic-ref HEAD --short 2>/dev/null`
GIT_DIRTY = `git status --porcelain`
GIT_TAG = `git describe --tags || echo "no version info"`
AUTHOR = $(USER)


# Test report configuration
TEST_REPORT_DIR ?= $(CURRENT_DIR)/tests/report
TEST_REPORT_FILE ?= nose2-junit.xml

# general targets timestamps
TIMESTAMPS = .timestamps
VOLUMES_MINIO = .volumes/minio
LOGS_DIR = $(PWD)/logs
REQUIREMENTS := $(TIMESTAMPS) $(VOLUMES_MINIO) $(LOGS_DIR) $(PIP_FILE) $(PIP_FILE_LOCK)


# Docker variables
DOCKER_REGISTRY = 974517877189.dkr.ecr.eu-central-1.amazonaws.com
DOCKER_IMG_LOCAL_TAG := $(DOCKER_REGISTRY)/$(SERVICE_NAME):local-$(USER)-$(GIT_HASH_SHORT)

# AWS variables
AWS_DEFAULT_REGION = eu-central-1

# Find all python files that are not inside a hidden directory (directory starting with .)
PYTHON_FILES := $(shell find ./* -type f -name "*.py" -print)

# PIPENV files
PIP_FILE = Pipfile
PIP_FILE_LOCK = Pipfile.lock

# default configuration
ENV_FILE ?= .env.default
HTTP_PORT ?= 5000
ROUTE_PREFIX ?= /api/kml

# Commands
PIPENV_RUN := pipenv run
PYTHON := $(PIPENV_RUN) python3
PIP := $(PIPENV_RUN) pip3
FLASK := $(PIPENV_RUN) flask
YAPF := $(PIPENV_RUN) yapf
ISORT := $(PIPENV_RUN) isort
NOSE := $(PIPENV_RUN) nose2
PYLINT := $(PIPENV_RUN) pylint



all: help


.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@echo -e " \033[1mSetup TARGETS\033[0m "
	@echo "- setup              Create the python virtual environment with developper tools and activate it"
	@echo "- ci                 Create the python virtual environment and install requirements based on the Pipfile.lock"
	@echo -e " \033[1mFORMATING, LINTING AND TESTING TOOLS TARGETS\033[0m "
	@echo "- format             Format the python source code"
	@echo "- lint               Lint the python source code"
	@echo "- format-lint        Format and lint the python source code"
	@echo "- test               Run the tests"
	@echo -e " \033[1mLOCAL SERVER TARGETS\033[0m "
	@echo "- serve              Run the project using the flask debug server. Port can be set by Env variable HTTP_PORT (default: 5000)"
	@echo "- gunicornserve      Run the project using the gunicorn WSGI server. Port can be set by Env variable DEBUG_HTTP_PORT (default: 5000)"
	@echo -e " \033[1mDocker TARGETS\033[0m "
	@echo "- dockerlogin        Login to the AWS ECR registery for pulling/pushing docker images"
	@echo "- dockerbuild        Build the project localy (with tag := $(DOCKER_IMG_LOCAL_TAG)) using the gunicorn WSGI server inside a container"
	@echo "- dockerpush         Build and push the project localy (with tag := $(DOCKER_IMG_LOCAL_TAG))"
	@echo "- dockerrun          Run the project using the gunicorn WSGI server inside a container (exposed port: 5000)"
	@echo -e " \033[1mCLEANING TARGETS\033[0m "
	@echo "- clean              Clean genereated files"
	@echo "- clean_venv         Clean python venv"
	@echo "- clean_logs         Clean logs"
	@echo "- clean_vol_minio    Clean $(VOLUMES_MINIO)"


# Build targets. Calling setup is all that is needed for the local files to be installed as needed.

.PHONY: setup
setup: $(REQUIREMENTS)
	pipenv install --dev
	pipenv shell


.PHONY: ci
ci: $(REQUIREMENTS)
	# Create virtual env with all packages for development using the Pipfile.lock
	pipenv sync --dev


# linting target, calls upon yapf to make sure your code is easier to read and respects some conventions.

.PHONY: format
format:
	$(YAPF) -p -i --style .style.yapf $(PYTHON_FILES)
	$(ISORT) $(PYTHON_FILES)


.PHONY: ci-check-format
ci-check-format: format
	@if [[ -n `git status --porcelain` ]]; then \
	 	>&2 echo "ERROR: the following files are not formatted correctly:"; \
		>&2 git status --porcelain; \
		exit 1; \
	fi


.PHONY: lint
lint:
	$(PYLINT) $(PYTHON_FILES)


.PHONY: format-lint
format-lint: format lint


# Test target

.PHONY: test
test:
	mkdir -p $(TEST_REPORT_DIR)
	ENV_FILE=.env.testing $(NOSE) -c tests/unittest.cfg --verbose --junit-xml-path $(TEST_REPORT_DIR)/$(TEST_REPORT_FILE) -s tests/


# Serve targets. Using these will run the application on your local machine. You can either serve with a wsgi front (like it would be within the container), or without.

.PHONY: serve
serve: clean_logs $(LOGS_DIR)
	ENV_FILE=$(ENV_FILE) LOGS_DIR=$(LOGS_DIR) FLASK_APP=service_launcher.py FLASK_DEBUG=1 $(FLASK) run --host=0.0.0.0 --port=$(HTTP_PORT)


.PHONY: gunicornserve
gunicornserve: clean_logs $(LOGS_DIR)
	mkdir -p /tmp/gunicorn_workers
	SCRIPT_NAME=$(ROUTE_PREFIX) ENV_FILE=$(ENV_FILE) LOGS_DIR=$(LOGS_DIR) $(PYTHON) wsgi.py


# Docker related functions.

.PHONY: dockerlogin
dockerlogin:
	aws --profile swisstopo-bgdi-builder ecr get-login-password --region $(AWS_DEFAULT_REGION) | docker login --username AWS --password-stdin $(DOCKER_REGISTRY)


.PHONY: dockerbuild
dockerbuild: $(VOLUMES_MINIO)
	docker build \
		--build-arg GIT_HASH="$(GIT_HASH)" \
		--build-arg GIT_BRANCH="$(GIT_BRANCH)" \
		--build-arg GIT_DIRTY="$(GIT_DIRTY)" \
		--build-arg VERSION="$(GIT_TAG)" \
		--build-arg HTTP_PORT="$(HTTP_PORT)" \
		--build-arg AUTHOR="$(AUTHOR)" -t $(DOCKER_IMG_LOCAL_TAG) .


.PHONY: dockerpush
dockerpush: dockerbuild
	docker push $(DOCKER_IMG_LOCAL_TAG)


.PHONY: dockerrun
dockerrun: clean_logs dockerbuild $(LOGS_DIR)
	docker run \
		-it --rm --net=host \
		--env-file=${PWD}/${ENV_FILE} \
		--env LOGS_DIR=/logs \
		--env SCRIPT_NAME=$(ROUTE_PREFIX) \
		--env GUNICORN_WORKER_TMP_DIR= \
		--mount type=bind,source="${LOGS_DIR}",target=/logs \
		$(DOCKER_IMG_LOCAL_TAG)


 # Clean targets

.PHONY: clean_logs
clean_logs:
	rm -rf $(LOGS_DIR)

.PHONY: clean_venv
clean_venv:
	pipenv --rm

.PHONY: clean_vol_minio
clean_volumes_minio:
	rm -rf $(VOLUMES_MINIO)


.PHONY: clean
clean: clean_venv clean_logs clean_vol_minio
	@# clean python cache files
	find . -name __pycache__ -type d -print0 | xargs -I {} -0 rm -rf "{}"
	rm -rf $(PYTHON_LOCAL_DIR)
	rm -rf $(TEST_REPORT_DIR)
	rm -rf $(TIMESTAMPS)


# Actual builds targets with dependencies

$(TIMESTAMPS):
	mkdir -p $(TIMESTAMPS)


$(VOLUMES_MINIO):
	mkdir -p $(VOLUMES_MINIO)


$(LOGS_DIR):
	mkdir -p -m=777 $(LOGS_DIR)
