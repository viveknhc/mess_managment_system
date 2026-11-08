# Mess Manager

Web app for mess / tiffin businesses that run on monthly subscriptions. It replaces notebooks, WhatsApp and spreadsheets with customer records, meal plans, subscriptions, payment tracking and daily delivery lists. Owners, managers, delivery staff, kitchen staff and customers each get their own login. SaaS-ready: businesses sign up with a 30-day trial.

**Stack:** Django 5 + Django REST Framework · React 19 + Vite + TypeScript · SQLite locally (PostgreSQL in production)

## Run it locally

Needs Python 3.12+, Node.js 20.19+ (22 LTS recommended) and Git. No database server or Redis required.

```bash
git clone https://github.com/viveknhc/mess_managment_system.git
cd mess_managment_system/backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data      # demo data; prints login usernames/passwords
python manage.py runserver      # http://localhost:8000
```

In a second terminal:

```bash
cd mess_managment_system/frontend
npm install
npm run dev                     # open http://localhost:5173
```

**Full guide** with Windows commands, troubleshooting and optional extras: download and open [`docs/how-to-run.html`](docs/how-to-run.html) in your browser.

## Tests

```bash
cd backend && python -m pytest          # backend tests + coverage
cd frontend && npx tsc -b && npm run lint
```

## Deploy (free)

Frontend on Vercel, API on Render, Postgres on Neon — step-by-step in [`docs/deploy.md`](docs/deploy.md).
