FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.1.2 \
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

COPY . .
RUN poetry build -f wheel \
    && poetry run pip install --no-cache-dir --no-deps dist/*.whl


FROM python:3.12-slim AS production

LABEL org.opencontainers.image.title="EnCoDaPy" \
    org.opencontainers.image.description="Energy Control and Data Preparation in Python" \
    org.opencontainers.image.source="https://github.com/gewv-tu-dresden/encodapy" \
    org.opencontainers.image.licenses="BSD-3-Clause"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$VENV_PATH/bin:$PATH"

WORKDIR /app

COPY --from=builder ${VENV_PATH} ${VENV_PATH}


HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 CMD test -f /app/health && [ $(( $(date +%s) - $(date -r /app/health +%s) )) -lt 180 ] || exit 1

CMD ["python", "-m", "encodapy.service.service_main"]
