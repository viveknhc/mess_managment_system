#!/usr/bin/env bash
# Starts an ISOLATED backend for Playwright E2E runs:
#   - its own throwaway SQLite DB (never touches backend/db.sqlite3)
#   - fresh demo data (seed_data) + a superadmin user
#   - login throttling off, port $E2E_API_PORT (default 8765)
# Launched automatically by playwright.config.ts → webServer.
set -euo pipefail

cd "$(dirname "$0")/../../backend"

PORT="${E2E_API_PORT:-8765}"
DB_FILE="${E2E_DB_FILE:-${TMPDIR:-/tmp}/mess-e2e.sqlite3}"

# Python: $PYTHON, else the project venv, else python3
if [[ -n "${PYTHON:-}" ]]; then PY="$PYTHON"
elif [[ -x .venv/bin/python ]]; then PY=".venv/bin/python"
else PY="python3"; fi

export DJANGO_SETTINGS_MODULE=config.settings.local
export DATABASE_URL="sqlite:///${DB_FILE}"
export DISABLE_THROTTLING=1

rm -f "$DB_FILE"
"$PY" manage.py migrate --noinput -v0
"$PY" manage.py seed_data > /dev/null
"$PY" manage.py shell -c "
from apps.accounts.models import User
User.objects.create_user(username='superadmin', password='superadmin123', role='SUPER_ADMIN', is_staff=True, is_superuser=True)
"
echo "E2E backend ready on :$PORT (db: $DB_FILE)"
exec "$PY" manage.py runserver "127.0.0.1:$PORT" --noreload
