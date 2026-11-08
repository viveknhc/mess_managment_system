#!/usr/bin/env bash
# Render build step (see render.yaml). Runs on every deploy.
set -o errexit

pip install -r requirements/production.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Platform admin from SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD (skipped if unset)
python manage.py ensure_superadmin

# Optional demo data: set SEED_DEMO=1 to load "Annapurna Mess" once (skipped if it already exists)
if [[ "${SEED_DEMO:-0}" == "1" ]]; then
  if python manage.py shell -c "from apps.businesses.models import Business; import sys; sys.exit(0 if Business.objects.filter(name='Annapurna Mess').exists() else 1)"; then
    echo "Demo data already present — skipping seed."
  else
    python manage.py seed_data
  fi
fi
