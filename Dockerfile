FROM python:3.12-slim

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installation de Poetry
RUN pip install poetry==1.7.1
ENV PATH="${PATH}:/root/.local/bin"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

# Configuration de Poetry et installation des dépendances
RUN poetry config virtualenvs.create false \
    && poetry config installer.max-workers 10

RUN poetry install --no-dev --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "uvicorn", "open_webui.app:app", "--host", "0.0.0.0", "--port", "8080"]
