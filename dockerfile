# `python-base` sets up all our shared environment variables
FROM python:3.11-slim AS python-base

RUN apt-get update && apt-get upgrade -y \
    && python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install -U setuptools

# python
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # poetry
    # https://python-poetry.org/docs/configuration/#using-environment-variables
    POETRY_VERSION=1.7.1 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    # make poetry create the virtual environment in the project's root
    # it gets named `.venv`
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1 \
    \
    # paths
    # this is where our requirements + virtual environment will live
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"


# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


# `builder-base` stage is used to build deps + create our virtual environment
FROM python-base AS builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    # deps for installing poetry
    curl

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=$POETRY_HOME POETRY_VERSION=$POETRY_VERSION python3 -

# copy project requirement files here to ensure they will be cached. 
WORKDIR $PYSETUP_PATH
COPY pyproject.toml ./
COPY encodapy ./encodapy
# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --only main


# `production` image used for runtime
FROM python-base AS production


ENV FASTAPI_ENV=production
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

COPY service_main/main.py /app/main.py

WORKDIR /app
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 CMD if [ $(( `date +%s` - `date -r health "+%s"` )) -lt 180 ]; then exit 0; else exit 1; fi

CMD ["python3", "main.py"]