FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && python -m pip install --no-cache-dir --upgrade pip setuptools \
    && curl -sSL https://install.python-poetry.org | python - \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $PYSETUP_PATH
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

WORKDIR /app
COPY . /app

ENV FILE_PATH_OF_STATIC_DATA=/app/static_data.json

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 CMD test -f /app/health && [ $(( $(date +%s) - $(date -r /app/health +%s) )) -lt 180 ] || exit 1

CMD ["python", "main.py"]