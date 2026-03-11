FROM python:3.13.11-slim-trixie AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PIPENV_HIDE_EMOJIS=true \
    PIPENV_NOSPIN=true \
    WORKON_HOME=/opt/venv \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG USER_NAME=app-data
ARG USER_ID=1000

WORKDIR /app

RUN pip install --no-cache-dir pipenv==2026.0.3 && useradd --home $WORKON_HOME --uid $USER_ID $USER_NAME

USER $USER_NAME

CMD ["pipenv", "shell"]

####################################
FROM base AS deploy-app

ARG USER_NAME=app-data
ARG ENVIRONMENT

COPY . /app

RUN ls -la /app

USER root
RUN pipenv install --deploy && pipenv run build

USER $USER_NAME

CMD ["pipenv", "run", "start"]
