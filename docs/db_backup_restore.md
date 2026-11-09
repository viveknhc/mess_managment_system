# Database Backup & Restore Runbook

## Production (Neon) — automatic daily backup

The **Daily DB backup** GitHub Actions workflow (`.github/workflows/db-backup.yml`)
runs every night at 02:00 IST. It dumps the production database with `pg_dump`,
encrypts the dump with AES-256 (gpg) and keeps it as a workflow artifact for
**30 days**. Neon's own restore history is a second safety net.

**One-time setup** (GitHub → repo → Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `PROD_DATABASE_URL` | Neon connection string (`postgresql://…?sslmode=require`) |
| `BACKUP_PASSPHRASE` | A long random passphrase. **Keep a copy outside GitHub** (password manager): without it the backups can't be decrypted. |

Run it once by hand (Actions → Daily DB backup → Run workflow) and check the artifact appears.

**Restore** (test this once before you need it):

```bash
# 1. Download the artifact (Actions → run → Artifacts) and unzip it, or:
gh run download <run-id> -n messdeck_YYYYMMDD_HHMM

# 2. Decrypt
gpg --batch --passphrase "$BACKUP_PASSPHRASE" -d messdeck_YYYYMMDD_HHMM.dump.gpg > backup.dump

# 3. Restore into an EMPTY database (create a new Neon branch/database for this,
#    check the data, then point DATABASE_URL at it)
pg_restore --no-owner --no-privileges -d "$TARGET_DATABASE_URL" backup.dump
```

Use a `pg_restore` at least as new as the server (PostgreSQL 17 client for Neon).

## Backup

### Docker (PostgreSQL container)

```bash
# Full backup
docker compose exec db pg_dump -U mess_user mess_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose exec db pg_dump -U mess_user mess_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
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
docker compose exec -T db psql -U mess_user mess_db < backup_20240101_120000.sql

# Safe restore — drop and recreate DB first
docker compose exec db dropdb -U mess_user mess_db
docker compose exec db createdb -U mess_user mess_db
docker compose exec -T db psql -U mess_user mess_db < backup_20240101_120000.sql
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
