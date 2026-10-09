# Database Backup & Restore Runbook

## Backup

### Docker (PostgreSQL container)

```bash
# Full backup
docker compose exec postgres pg_dump -U mess_user mess_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose exec postgres pg_dump -U mess_user mess_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Local (SQLite)

```bash
cp backend/db.sqlite3 backend/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
```

### Local (PostgreSQL)

```bash
pg_dump -U mess_user mess_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

## Restore

### Docker (PostgreSQL container)

```bash
# Full restore (destructive — drops existing data)
docker compose exec -T postgres psql -U mess_user mess_db < backup_20240101_120000.sql

# Safe restore — drop and recreate DB first
docker compose exec postgres dropdb -U mess_user mess_db
docker compose exec postgres createdb -U mess_user mess_db
docker compose exec -T postgres psql -U mess_user mess_db < backup_20240101_120000.sql
```

### Local (SQLite)

```bash
cp backend/db.sqlite3.backup_20240101_120000 backend/db.sqlite3
```

### Local (PostgreSQL)

```bash
psql -U mess_user mess_db < backup_20240101_120000.sql
```

## Django Management Commands

### Seed demo data

```bash
cd backend

# First-time seed (fails if data already exists)
python manage.py seed_data

# Flush everything and re-seed
python manage.py seed_data --reset

# Or use the reset wrapper (interactive confirmation)
python manage.py reset_data

# Non-interactive reset
python manage.py reset_data --yes
```

### Full database reset via Django

```bash
cd backend
python manage.py flush --no-input    # Clears all data, keeps schema
python manage.py migrate             # Ensure schema is up to date
python manage.py seed_data           # Re-seed demo data
```

## Post-Restore Verification

After any restore or reset, verify the system is healthy:

```bash
cd backend

# 1. Check migrations are applied
python manage.py showmigrations | grep '\[ \]'
# Expected: no unapplied migrations

# 2. Run the demo dry-run test
python -m pytest apps/accounts/tests/test_demo.py -v

# 3. Run the DoD checklist test
python -m pytest apps/accounts/tests/test_dod_checklist.py -v

# 4. Run full test suite
python -m pytest

# 5. Start the server and verify login
python manage.py runserver
# Login at http://localhost:8000/api/v1/auth/login/ with owner/owner123
```

## Seed Data Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Owner | owner | owner123 |
| Manager | manager | manager123 |
| Delivery Staff | delivery1 | delivery123 |
| Kitchen Staff | kitchen1 | kitchen123 |
| Customer Portal | customer1-5 | customer123 |
