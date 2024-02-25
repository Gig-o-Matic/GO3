FROM python:3.10-alpine as base

ENV PYTHONFAULTHANDLER=1 \
  PYTHONHASHSEED=random \
  PYTHONUNBUFFERED=1

WORKDIR /app

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_NO_CACHE_DIR=1 \
  POETRY_VERSION=1.5.1

RUN apk add --no-cache g++ gcc libffi-dev musl-dev postgresql-dev \
  && pip install "poetry==$POETRY_VERSION" \
  && python -m venv /venv

COPY pyproject.toml poetry.lock ./

RUN ash -c 'set -o pipefail && /venv/bin/pip install wheel \
  && poetry export -f requirements.txt --with=postgres \
    | /venv/bin/pip install -r /dev/stdin'

FROM base as final

RUN apk add --no-cache libffi libpq libstdc++

COPY --from=builder /venv /venv

COPY . .

CMD venv/bin/python manage.py runserver 0.0.0.0:$PORT
