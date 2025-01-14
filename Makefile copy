.PHONY: setup install-pyenv install-python install-poetry install-deps dev test

# Variables
PYTHON_VERSION := 3.12.1
POETRY_VERSION := 1.7.1

setup: install-pyenv install-python install-poetry install-deps

install-pyenv:
	@echo "Installing pyenv..."
	@if command -v pyenv >/dev/null 2>&1; then \
		echo "pyenv is already installed"; \
	else \
		curl https://pyenv.run | bash; \
		echo 'export PYENV_ROOT="$$HOME/.pyenv"' >> ~/.bashrc; \
		echo 'command -v pyenv >/dev/null || export PATH="$$PYENV_ROOT/bin:$$PATH"' >> ~/.bashrc; \
		echo 'eval "$$(pyenv init -)"' >> ~/.bashrc; \
		echo "Please restart your shell or run:"; \
		echo "source ~/.bashrc"; \
	fi

install-python:
	@echo "Installation de Python $(PYTHON_VERSION)..."
	@if pyenv versions | grep $(PYTHON_VERSION) >/dev/null 2>&1; then \
		echo "Python $(PYTHON_VERSION) est déjà installé"; \
	else \
		pyenv install $(PYTHON_VERSION); \
	fi
	@pyenv local $(PYTHON_VERSION)
	@python -m pip install --upgrade pip

# Usage: make install-python PYTHON_VERSION=3.12.1

install-poetry:
	@echo "Installing Poetry..."
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Poetry is already installed"; \
	else \
		curl -sSL https://install.python-poetry.org | python3 - --version $(POETRY_VERSION); \
		export PATH="/root/.local/bin:$PATH"; \
	fi

install-deps:
	@echo "Installing project dependencies..."
	@poetry install

dev:
	@echo "Starting development server..."
	@poetry run dev run --reload

test:
	@echo "Running tests..."
	@poetry run test run

docker-up:
	@echo "Starting Docker services..."
	@poetry run dev docker-up

docker-down:
	@echo "Stopping Docker services..."
	@poetry run dev docker-down

clean:
	@echo "Cleaning up..."
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make setup          - Install everything needed (pyenv, Python, Poetry, deps)"
	@echo "  make install-pyenv  - Install pyenv"
	@echo "  make install-python - Install Python $(PYTHON_VERSION)"
	@echo "  make install-poetry - Install Poetry"
	@echo "  make install-deps   - Install project dependencies"
	@echo "  make dev           - Start development server"
	@echo "  make test          - Run tests"
	@echo "  make docker-up     - Start Docker services"
	@echo "  make docker-down   - Stop Docker services"
	@echo "  make clean         - Clean up cache and temporary files" 