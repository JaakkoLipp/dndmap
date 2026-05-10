# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

ARG API_DIR=apps/api

RUN addgroup --system app && adduser --system --ingroup app app

COPY ${API_DIR}/ ./

RUN python -m pip install --upgrade pip \
    && if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    elif [ -f pyproject.toml ]; then \
      pip install .; \
    else \
      echo "Expected requirements.txt or pyproject.toml in ${API_DIR}" >&2; \
      exit 1; \
    fi

USER app

EXPOSE 8000

CMD uvicorn "${API_ASGI_APP:-app.main:app}" --host 0.0.0.0 --port 8000
