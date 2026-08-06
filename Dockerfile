FROM python:3.13.12-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/

ENV WORKON_HOME=/opt/venv

ENV PYTHONFAULTHANDLER=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_HTTP_TIMEOUT=100 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=$WORKON_HOME/uv-cache \
    UV_PROJECT_ENVIRONMENT=$WORKON_HOME/app-4PlAip0Q \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG USER_NAME=app-data
ARG USER_ID=1000

WORKDIR /app

RUN useradd --home $WORKON_HOME --uid $USER_ID $USER_NAME

USER $USER_NAME

CMD ["uv", "run", "--no-sync", "bash"]

####################################
FROM base AS deploy-app

ARG USER_NAME=app-data

WORKDIR /app

USER root

RUN --mount=type=cache,target=$UV_CACHE_DIR \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=packages,target=/app/packages \
    uv sync --locked --no-install-project --no-dev

COPY . .

RUN --mount=type=cache,target=$UV_CACHE_DIR \
    ls -la . \
    && uv sync --locked --no-dev \
    && uv run --no-sync poe build

ENV UV_NO_CACHE=1

USER $USER_NAME

CMD ["uv", "run", "--no-sync", "poe", "start"]
