FROM python:3.11-alpine as base

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBUG=False

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_NO_CACHE_DIR=1 \
  POETRY_VERSION=1.5.1

RUN apk add --no-cache tini gcc musl-dev libffi-dev libpq-dev \
  && pip install "poetry==$POETRY_VERSION" \
  && python -m venv /venv

COPY pyproject.toml poetry.lock ./

RUN ash -c 'set -o pipefail && /venv/bin/pip install wheel \
  && poetry export -f requirements.txt --with=postgres \
    | /venv/bin/pip install -r /dev/stdin'

FROM base as final

RUN apk add --no-cache tini

COPY . .

COPY --from=builder /venv /venv

RUN /venv/bin/python manage.py collectstatic --noinput

RUN addgroup -g 1000 appuser; \
    adduser -u 1000 -G appuser -D -h /app appuser; \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000/tcp

ENTRYPOINT [ "tini", "--" ]
