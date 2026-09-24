# CLAUDE.md — Mess Management System

## Project Overview

SaaS-ready web application for mess/subscription-based food businesses. Replaces notebooks, WhatsApp, and spreadsheets with digital customer management, subscription tracking, payment recording, and daily delivery operations.

**Stack:** Django 5 + DRF (backend) · React 19 + Vite 8 + TypeScript 6 (frontend) · PostgreSQL 15 · Redis 7 · Celery

**Architecture:** Modular Monolith — one Django app, one React app, one PostgreSQL database, clearly separated business modules.

---

## Current Progress

**23 / 153 tasks complete (15%)**

| Module | Status | Tasks |
|--------|--------|-------|
| 0 Foundation | DONE | 12/12 |
| 1 Authentication | DONE | 10/10 |
| 2 Business / Tenant | In Progress | 1/6 |
| 3–16 (remaining) | Not Started | 0/130 |

**Progress tracker:** `docs/progress.html` (standalone HTML) and `docs/tasks.md` (checkbox tracker)

**Always update BOTH when completing tasks.**

---

## Directory Structure

```
mess management/
├── backend/                    # Django REST Framework
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py         # Shared settings
│   │   │   ├── local.py        # Dev/test overrides
│   │   │   └── production.py   # Production hardening
│   │   ├── urls.py             # Root URL router (/api/v1/)
│   │   ├── celery.py           # Celery app
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/           # User model, auth endpoints, bootstrap command
│   │   └── businesses/         # Business model, viewset
│   ├── common/                 # Shared base classes
│   │   ├── models.py           # TimeStampedModel, UUIDModel, TenantScopedModel
│   │   ├── viewsets.py         # TenantScopedViewSet
│   │   ├── permissions.py      # IsSameBusiness, RoleBasedPermission
│   │   ├── exceptions.py       # Unified error envelope
│   │   ├── pagination.py       # StandardPagination
│   │   └── constants.py        # Role, Status enums
│   ├── conftest.py             # Disables throttling in tests
│   ├── requirements/           # base.txt, local.txt, production.txt
│   └── manage.py
├── frontend/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── app/                # App.tsx, routes.tsx
│   │   ├── layouts/            # AdminLayout, CustomerLayout, StaffLayout
│   │   ├── features/           # Domain modules (auth/, customers/, etc.)
│   │   ├── components/         # Shared UI (ProtectedRoute, ui/)
│   │   ├── services/           # apiClient.ts (Axios + JWT interceptors)
│   │   ├── store/              # authStore.ts (Zustand)
│   │   ├── hooks/, utils/, types/, assets/
│   │   └── index.css           # Tailwind v4 + theme tokens
│   └── vite.config.ts          # Aliases, proxy, Tailwind plugin
├── docs/                       # Specifications & tracking
│   ├── poc.md                  # What we're building (features, roles, rules)
│   ├── system_design.md        # How each part works (HLD + LLD)
│   ├── technical_architechture.md  # Stack choices & architecture style
│   ├── mess_management_modularization_plan.md  # Module boundaries
│   ├── development_plan.md     # Day-by-day schedule
│   ├── tasks.md                # Checkbox task tracker (source of truth)
│   └── progress.html           # Visual progress dashboard
├── docker-compose.yml          # postgres:15, redis:7, django:8000, web:5173
├── .github/workflows/ci.yml   # CI: lint + test + coverage + build
└── CLAUDE.md                   # This file
```

---

## Development Rules (NEVER break these)

### Architecture Rules

1. **Tenant isolation via `common/` only** — Every tenant-scoped model extends `TenantScopedModel`. Every viewset extends `TenantScopedViewSet`. Never bypass.
2. **IsSameBusiness returns 404, not 403** — Never leak existence of other tenants' data.
3. **business_id is read-only in every serializer** — Clients cannot set it; `perform_create()` force-sets it from `request.user.business_id`.
4. **Thin views, fat services** — Views handle HTTP; business logic lives in `services.py`. Complex reads in `selectors.py`.
5. **Cross-module writes only via services** — Never import another app's model and write to it directly. Call its service.
6. **EXPIRING is never stored** — Always computed: `status=ACTIVE AND end_date <= today+3`. Single predicate definition.
7. **UUID PKs on all models** — Non-enumerable, safe for URL exposure.
8. **Money as NUMERIC(10,2)** — Never float. `DecimalField(max_digits=10, decimal_places=2)`.

### Code Rules

9. **Backend tests before frontend** — Write and pass backend tests before building the frontend for a module.
10. **Commit per module** — Never commit mid-model. Complete a module's DoD checklist first.
11. **Ruff format + check must pass** — Run `ruff format . && ruff check .` before committing.
12. **TypeScript must compile** — Run `npx tsc -b` before committing frontend changes.
13. **Coverage >= 70%** — CI enforces this. Current: ~87%.
14. **No `objects.all()` outside `common/`** — Always filter by business. Tenant bypass = bug.

### Frontend Rules

15. **Zustand for auth/business state only** — Domain data (customers, subscriptions, etc.) uses TanStack Query.
16. **Relative imports** — TypeScript 6 deprecates `baseUrl`/`paths`. Use relative imports. Vite `@` alias works at runtime.
17. **Feature modules own their components** — `CustomerForm` lives in `features/customers/`, not `components/`.
18. **Shared UI in `components/ui/`** — Button, Input, Modal, Table, Badge, etc.

### Testing Rules

19. **Throttling disabled in tests** — `conftest.py` clears `DEFAULT_THROTTLE_RATES`.
20. **Every module needs isolation tests** — User of Business B gets 404 on Business A data.
21. **Hard rules (NEVER cut):**
    - Tenant isolation tests
    - Subscription state machine + illegal-transition tests
    - Payment math tests
    - Golden workflow e2e (customer → plan → payment → ACTIVE)
    - Demo dry-run before calling MVP done

---

## API Conventions

- **Base URL:** `/api/v1/`
- **Auth:** JWT Bearer token in `Authorization` header
- **Pagination:** `{count, next, previous, results}`
- **Error envelope:** `{error: {code, message, fields}}`
- **Error codes:** `VALIDATION_ERROR`, `INVALID_TRANSITION`, `AUTH_INVALID`, `PERMISSION_DENIED`, `NOT_FOUND`, `RATE_LIMITED`, `SERVER_ERROR`
- **Filters:** `?status=&customer=&search=&ordering=` via django-filter

### Auth Endpoints

```
POST /api/v1/auth/login/      → {access, refresh, user: {id, username, name, role, business_id, business_name}}
POST /api/v1/auth/refresh/    → {access, refresh}
POST /api/v1/auth/logout/     → {detail: "Logged out."}  (send {refresh} in body)
GET  /api/v1/auth/me/         → {id, username, name, role, business_id, business_name}
```

---

## User Roles

| Role | Access |
|------|--------|
| SUPER_ADMIN | Platform-level (future SaaS) |
| OWNER | Full business access — dashboard, customers, plans, subscriptions, payments, deliveries, reports, staff, settings |
| MANAGER | Same as owner minus some settings |
| DELIVERY_STAFF | View assigned deliveries, mark delivered/not delivered, add notes |
| KITCHEN_STAFF | View today's meal counts |
| CUSTOMER | View own subscription/payments/deliveries, skip meal, pause, renew |

---

## Module Build Order (locked)

Must build in this order — each depends on the previous:

```
Foundation → Auth → Business → Users/Staff → Customers → Meals → Plans
→ Subscriptions → Payments → Deliveries → Dashboard → Notifications
→ Reports → Settings → Audit → Customer Portal → Seed & Demo
```

---

## Key Business Flows

### Golden Path: Customer → Plan → Payment → ACTIVE
```
POST /subscriptions/     → status=PENDING
POST /payments/          → recalc paid/pending → if fully paid:
                           subscription → ACTIVE
                           generate delivery schedule
                           emit notification
```

### Subscription State Machine
```
PENDING → ACTIVE (full payment)
PENDING → CANCELLED
ACTIVE → PAUSED → ACTIVE (resume)
ACTIVE → CANCELLED
ACTIVE → EXPIRED (end_date < today, nightly sweep)
EXPIRED → (new Subscription via renew, linked by renewed_from_id)
```

### Skip/Pause Rules (per-business configurable)
- Skip → extend subscription end_date, OR meal credit, OR no adjustment
- Pause → deliveries in range cancelled, resume restores them

---

## Management Commands

```bash
# Bootstrap first business + owner
python3 manage.py bootstrap_business \
  --business-name "Rahul's Mess" \
  --owner-username admin \
  --owner-password admin123 \
  --owner-name "Rahul Kumar" \
  --owner-email admin@example.com \
  --owner-phone "9876543210"
```

---

## Running Locally

```bash
# Backend
cd backend
pip install -r requirements/local.txt
python3 manage.py migrate
python3 manage.py runserver

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend && python3 -m pytest
cd frontend && npx tsc -b
```

---

## CI/CD

GitHub Actions on push to `main`/`develop` and PRs:
- **Backend Lint:** `ruff check . && ruff format --check .`
- **Backend Tests:** `pytest` with coverage (minimum 70%)
- **Frontend Lint:** `tsc -b && oxlint .`
- **Frontend Build:** `vite build`

---

## What's Next

Current: **Module 2 — Business / Tenant** (B-02 to B-06)
Then: Module 3 (Users & Staff) → Module 4 (Customers) → Module 5 (Meals) → Module 6 (Plans)

Sprint 1 goal: Auth + Business + Customers + Meals + Plans all working end-to-end.
