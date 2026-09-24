# 🍱 Mess Management System — Module-Wise Daily Task Plan

Day-by-day build plan, organized **module by module** in the locked development order (poc.md §31 + modularization plan §30). Days are sequential working days for one full-time developer (≈ 72 working days ≈ 3.5 months); two devs can run backend/frontend days of the same module in parallel.

Sources: `poc.md` (what) · `mess_management_modularization_plan.md` (boundaries & order) · `technical_architechture.md` (how).

## Module Map

| # | Module | Days | Depends On |
|---|---|---|---|
| 0 | Foundation | 1–4 | — |
| 1 | Authentication | 5–8 | Foundation |
| 2 | Business / Tenant | 9–10 | Auth |
| 3 | Users & Staff | 11–12 | Auth, Business |
| 4 | Customers | 13–18 | Auth, Business |
| 5 | Meals | 19–20 | Business |
| 6 | Plans | 21–23 | Business, Meals |
| 7 | Subscriptions ⭐ | 24–30 | Customer, Plan, Business |
| 8 | Payments | 31–36 | Subscription, Business |
| 9 | Deliveries + Skip/Pause | 37–46 | Subscription, Meal, Staff |
| 10 | Dashboard | 47–50 | Customers, Subs, Payments, Deliveries |
| 11 | Notifications | 51–54 | User, Business |
| 12 | Reports | 55–59 | all data modules |
| 13 | Settings | 60–61 | Business |
| 14 | Audit Trail | 62 | — |
| 15 | Customer Portal | 63–68 | all above |
| 16 | Seed Data & Demo | 69–72 | all above |

**Every module follows the same daily rhythm** (mod. plan §31): model → API contract → backend → backend tests → frontend API layer → UI → connect → workflow test → loading/error/empty states → commit.

**Standing rules for every day's work:** tenant scoping via `common/` base classes only; thin views; business logic in `services.py`; complex reads in `selectors.py`; cross-module writes only via services; `EXPIRING` never stored; Zustand for auth/business state only, TanStack Query for domain data; commit at end of each module, never mid-model.

---

## Module 0 — Foundation (Days 1–4)

| Day | Tasks | Done When |
|---|---|---|
| 1 | Repo scaffold: Django project (`config/settings/{base,local,production}.py`, `/api/v1/` router), `requirements/{base,local,production}.txt`, `.env.example` | `manage.py runserver` serves `/api/v1/health/` |
| 2 | React/Vite scaffold: `src/app/`, `layouts/` stubs, `services/apiClient.ts` skeleton, Tailwind theme, `components/ui/` empty kit | Vite dev server renders app shell |
| 3 | `docker-compose.yml` (postgres:15, redis:7, django:8000, web:5173), CORS, `djangorestframework-simplejwt` installed | `docker compose up` runs full stack fresh-clone |
| 4 | `common/`: `TimeStampedModel`, `TenantScopedModel`, `TenantScopedViewSet`, `IsSameBusiness` (404 not 403), `RoleBasedPermission`, pagination, unified error handler; CI skeleton (ruff + pytest, eslint + tsc + vitest) | CI green on hello-world PR; base classes importable |

## Module 1 — Authentication (Days 5–8)

| Day | Tasks | Done When |
|---|---|---|
| 5 | Custom `User` model (business FK, role enum: SUPER_ADMIN/OWNER/MANAGER/DELIVERY_STAFF/KITCHEN_STAFF/CUSTOMER, is_active) + migration; endpoints `POST /auth/login/`, `/auth/refresh/`, `/auth/logout/`, `GET /auth/me/` | Login returns tokens + user + business |
| 6 | First-owner bootstrap (management command); backend tests: auth flow, token expiry, bad credentials, inactive user | pytest auth suite green |
| 7 | Frontend: `authStore` (Zustand), apiClient interceptors (attach token; 401 → refresh once → retry → logout), `LoginPage` | Can log in and stay logged in across refresh |
| 8 | Protected route wrapper, role-based `routes.tsx` trees (Admin/Customer/Staff layouts); module DoD check + commit | Each role lands on its own layout |

## Module 2 — Business / Tenant (Days 9–10)

| Day | Tasks | Done When |
|---|---|---|
| 9 | `Business` model (name, phone, email, address, logo, status: ACTIVE/INACTIVE/SUSPENDED) + serializer + tenant-scoped viewset + isolation tests (Business B data → 404) | CRUD + 404 isolation tests green |
| 10 | Frontend business profile page + edit form; commit | Owner can view/edit own business |

## Module 3 — Users & Staff (Days 11–12)

| Day | Tasks | Done When |
|---|---|---|
| 11 | Staff CRUD in `accounts` (add/edit/activate/deactivate, assign role), role permission matrix enforced (poc §3), permission tests | Owner manages staff via API only |
| 12 | Staff management page (table, add/edit modal, role select, active toggle); commit | Staff user created via UI can log in |

## Module 4 — Customers (Days 13–18)

| Day | Tasks | Done When |
|---|---|---|
| 13 | `Customer` model (customer_code auto-gen, status: ACTIVE/INACTIVE/BLOCKED, address/location, notes) + migration + indexes `(business_id, name)`, `(business_id, phone)` | Migration clean, admin visible |
| 14 | Serializers + CRUD viewset on `TenantScopedViewSet` + status transitions | CRUD via API works |
| 15 | Search (name/phone/code/address), filters (status, active subscription, meal), sort, pagination via django-filter + `CustomerSelector`; backend tests | List endpoint matches poc §19 filter spec |
| 16 | Customer detail aggregate endpoint: profile + current subscription + payment/delivery/skip/pause histories via **other apps' selectors** (read-only) | One endpoint returns full profile |
| 17 | Frontend: `CustomersPage` — search-first table, filter chips, pagination | Search + filters usable on seeded rows |
| 18 | `CustomerForm` + `CustomerDetailsPage` (info + history tabs); loading/error/empty states; commit | DoD checklist passes |

## Module 5 — Meals (Days 19–20)

| Day | Tasks | Done When |
|---|---|---|
| 19 | `Meal` model (name, description, price, is_active) + CRUD + tests | API CRUD green |
| 20 | Frontend meals list + form + active/inactive toggle; commit | Owner manages meal types in UI |

## Module 6 — Plans (Days 21–23)

| Day | Tasks | Done When |
|---|---|---|
| 21 | `Plan` model (duration_days, price, meal FK, total_meals, skip_allowed, pause_allowed, is_active) + CRUD + tests | API CRUD green |
| 22 | Frontend plans list + form + Zod validation; commit | "Monthly Lunch ₹2500" creatable in UI |
| 23 | Buffer: seed reference data, manual e2e of customer→plan flow, responsive check | Sprint-1-equivalent workflow stable |

## Module 7 — Subscriptions ⭐ (Days 24–30)

| Day | Tasks | Done When |
|---|---|---|
| 24 | `Subscription` model (customer, plan, start/end, status, total/paid/pending, remaining_meals) + migration + index `(business_id, status, end_date)` + state-machine constant map (arch §6.4) | Model + transitions defined |
| 25 | `SubscriptionService.create_subscription()` (validate same business → PENDING) + endpoint + tests | POST creates PENDING sub |
| 26 | Action endpoints `pause/` `resume/` `cancel/` with legal-transition validation (transactions); tests incl. illegal transitions | Can't pause a CANCELLED sub |
| 27 | `renew/` action — new period calculation, extend end_date, reset counters + tests | Renew produces correct new dates |
| 28 | `SubscriptionSelector.get_expiring_subscriptions()` (EXPIRING computed at query time: `end_date ≤ today+3 AND ACTIVE`) + list filters + remaining-days/meals calc + tests | Expiry endpoint matches poc §21 query |
| 29 | Frontend: `SubscriptionsPage` + `SubscriptionCard` (poc §20 layout) + status filter incl. computed Expiring | List renders with live statuses |
| 30 | `SubscriptionForm` + action dialogs (pause/resume/cancel/renew with confirm) + all UI states; commit | Full lifecycle drivable from UI |

## Module 8 — Payments (Days 31–36)

| Day | Tasks | Done When |
|---|---|---|
| 31 | `Payment` model (amount, method enum, status, transaction_reference) + migration + index `(subscription_id)` | Migration clean |
| 32 | `PaymentService.record_payment()`: insert → recalc paid/pending → status rule (poc §26: PAID / PARTIAL / PENDING) + endpoint + tests | Amount math correct incl. partials |
| 33 | Activation chain: full payment → subscription ACTIVE → `DeliveryService.generate_delivery_schedule()` → `NotificationService.emit()` (stub) — all in one transaction, services-to-services + tests | Paying a PENDING sub activates it & schedules deliveries |
| 34 | Payment history + pending/partial summary endpoints + tests | poc §24 summary data available |
| 35 | Frontend: record-payment flow on PENDING subscription + payments history table | Payment recorded from UI |
| 36 | **Golden workflow e2e** (poc §34): Add Customer → Plan → Payment → ACTIVE; fix gaps; commit | Workflow passes end-to-end manually + in tests |

## Module 9 — Deliveries + Skip/Pause (Days 37–46)

| Day | Tasks | Done When |
|---|---|---|
| 37 | `Delivery` model (subscription, customer, delivery_date, meal_type, status enum, assigned_staff, notes) + migration + index `(business_id, delivery_date, status)` | Migration clean |
| 38 | `DeliveryService.generate_delivery_schedule()` — bulk insert for subscription period (called from Day 33 chain) + tests | Full schedule generated on activation |
| 39 | `DeliverySelector.get_today_deliveries()` + `GET /deliveries/today/` + `PATCH /deliveries/{id}/status/` (delivery staff: assigned-only, status + notes) + scoping tests | Staff sees/updates only assigned rows |
| 40 | `MealSkip` + `SubscriptionPause` models; skip flow flips that day's delivery to SKIPPED + tests | Skip recorded end-to-end |
| 41 | Configurable skip/pause rule (extend / meal credit / none) read from settings — not hard-coded (mod. plan §13); extension logic + tests | Different rules per business possible |
| 42 | Kitchen meal-count endpoint (today's counts per meal type, poc §23) + tests | Counts match delivery rows |
| 43 | Celery + Redis wired; Celery Beat nightly job: generate next-day deliveries (+ nightly expiry job); commit | Beat schedule runs in docker |
| 44 | Frontend: `TodayDeliveriesPage` — customer, phone, address, meal, status + big Mark Delivered / Not Delivered / Skip buttons + add note | Daily ops loop usable |
| 45 | `DeliveryHistoryPage` + filters; kitchen meal-counts view (StaffLayout) | Kitchen + staff screens done |
| 46 | Skip/pause admin UI; staff-scoping manual pass; all UI states; commit | Sprint-2-equivalent workflow: sub → payment → today list → delivered |

## Module 10 — Dashboard (Days 47–50)

| Day | Tasks | Done When |
|---|---|---|
| 47 | Dashboard aggregator endpoint — reads via other apps' **selectors only**, owns no data (poc §18 metrics) + tests vs seed data | All 8 KPIs returned correctly |
| 48 | `DashboardPage` + StatCard row | KPIs visible |
| 49 | ExpiryWidget (today/tomorrow/3-day/week/expired) + DeliveryWidget | Widgets live |
| 50 | PaymentWidget + MealSummaryWidget; commit | Dashboard matches poc §18 mock |

## Module 11 — Notifications (Days 51–54)

| Day | Tasks | Done When |
|---|---|---|
| 51 | `Notification` model + `NotificationService.emit()` — IN_APP channel now, provider interface leaves WhatsApp/SMS/Email pluggable | Events insert notifications |
| 52 | Wire emitters: PAYMENT_RECEIVED, SUBSCRIPTION_RENEWED, SUBSCRIPTION_EXPIRING/EXPIRED (nightly job), DELIVERY_UPDATE + tests | All event types fire |
| 53 | List-my-notifications + mark-read endpoints + tests | API green |
| 54 | Frontend bell + dropdown + unread count; commit | In-app notifications usable |

## Module 12 — Reports (Days 55–59)

| Day | Tasks | Done When |
|---|---|---|
| 55 | Customer + subscription report selectors + endpoints (read-only, live tables — no reporting store) | Two reports return correct aggregates |
| 56 | Revenue (daily/weekly/monthly) + payment + meal reports + tests | All poc §28 reports available |
| 57 | Frontend reports pages + Recharts revenue trend | Chart renders |
| 58 | Meal distribution + subscription status charts; date-range filters; CSV export | Filters + export work |
| 59 | Accuracy tests vs seeded data; commit | Report numbers reconcile |

## Module 13 — Settings (Days 60–61)

| Day | Tasks | Done When |
|---|---|---|
| 60 | Settings model (skip rules, min pause duration, max skip days, extension rule, delivery window, notification prefs) + endpoints + tests (Module 9 Day 41 logic consumes these) | Rules editable per business |
| 61 | Settings admin UI; commit | Owner edits settings from UI |

## Module 14 — Audit Trail (Day 62)

| Day | Tasks | Done When |
|---|---|---|
| 62 | `AuditLog` model (poc §29) written from services on state-changing actions + Django admin view; commit | Admin actions appear in log |

## Module 15 — Customer Portal (Days 63–68)

| Day | Tasks | Done When |
|---|---|---|
| 63 | Customer-role API scoping: strictly self-only reads + skip/pause-request/renew (portal never gets admin APIs — mod. plan §38) + permission tests | Customer token can't touch others' data |
| 64 | `CustomerLayout` + portal dashboard page (poc §25 mock) | Portal shell renders |
| 65 | My Subscription page — days remaining, Skip Meal / Pause / Renew buttons wired | Customer actions work |
| 66 | Portal payments + deliveries history pages | History visible to customer |
| 67 | Profile edit; staff layouts finalized (delivery/kitchen nav per poc §32) | All 4 role UIs complete |
| 68 | DRF throttling on auth + write-heavy endpoints; commit | Rate limits active |

## Module 16 — Seed Data & Demo (Days 69–72)

| Day | Tasks | Done When |
|---|---|---|
| 69 | Seed command (poc §30): 1 business, 3 staff, 20 customers, 5 plans, 20+ subs, 50+ payments, 100+ deliveries covering every status | `manage.py seed_demo` populates all statuses |
| 70 | Run the Rahul demo script (poc §39) end-to-end; fix gaps found | 12-step scenario passes |
| 71 | Verify poc §38 Definition of Done checklist (admin + customer); test DB backup/restore | DoD fully checked off |
| 72 | Final polish: responsive pass, docs update, tag MVP release | v0.1 tagged |

---

## Milestones

```text
Day 4   ✔ Foundation (docker compose up, CI green)
Day 12  ✔ Auth + Business + Staff usable
Day 23  ✔ Customers, Meals, Plans stable          (mod. plan Sprint 1 ✅)
Day 36  ✔ Golden workflow: customer→plan→sub→payment→ACTIVE
Day 46  ✔ Daily ops: today's deliveries, skip/pause (mod. plan Sprint 2 ✅)
Day 59  ✔ Dashboard, Notifications, Reports        (mod. plan Sprint 3 ✅)
Day 68  ✔ Portal, Settings, Audit
Day 72  ✔ MVP demo-ready (poc §38 DoD + §39 demo)  (mod. plan Sprint 4+ ✅)
```

## If You Fall Behind — Cut in This Order

Reports charts → CSV export → AuditLog UI (keep model writes) → notification event breadth (keep PAYMENT_RECEIVED + EXPIRING) → portal profile edit. **Never cut:** tenant isolation tests, subscription state machine, payment math tests, the golden workflow.

## Open Decisions (settle by Day 5)

1. First-business bootstrap: management command + Django Admin (recommended) vs signup endpoint.
2. Refresh token: httpOnly cookie (preferred, needs CSRF) vs memory-only.
3. Confirm TanStack Query adoption before Day 7 frontend work.
4. Pick staging deploy target by Day 37 (any VPS + Docker + managed Postgres).
