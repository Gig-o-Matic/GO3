#!/bin/sh

set -eou pipefail

exec /venv/bin/python manage.py runserver "0.0.0.0:${PORT-8080}"
