# 🍱 Mess Management System — Dev Task Tracker

Granular, checkbox-style task tracker. Companion to `development_plan.md` (module-wise daily schedule — see that file for day numbers and milestones).

## How to Use

- Work **top to bottom** — tasks are ordered by dependency (matches the locked build order in poc.md §31 + mod. plan §30).
- Check off `[ ] → [x]` as you complete. Do not skip a task whose dependencies are unchecked.
- **Effort:** `S` = ≤ half day · `M` = ~1 day · `L` = 2 days
- **Priority:** `P0` = MVP-blocking (poc §34/§38) · `P1` = needed for full demo (poc §39) · `P2` = polish, cut first if behind
- **Every task inherits the standing rules:** tenant scoping via `common/` only, thin views, logic in services/selectors, backend tests before frontend, commit per task.

## Status Summary

| Module | Tasks | Done | P0 | P1 | P2 |
|---|---|---|---|---|---|
| 0 Foundation | 12 | 12 | 12 | – | – |
| 1 Auth | 10 | 10 | 8 | 2 | – |
| 2 Business | 6 | 1 | 5 | 1 | – |
| 3 Users & Staff | 6 | 0 | 4 | 2 | – |
| 4 Customers | 14 | 0 | 11 | 3 | – |
| 5 Meals | 5 | 0 | 4 | 1 | – |
| 6 Plans | 6 | 0 | 5 | 1 | – |
| 7 Subscriptions ⭐ | 16 | 0 | 14 | 2 | – |
| 8 Payments | 12 | 0 | 10 | 2 | – |
| 9 Deliveries/Skip-Pause | 16 | 0 | 13 | 3 | – |
| 10 Dashboard | 8 | 0 | 6 | 2 | – |
| 11 Notifications | 8 | 0 | 5 | 3 | – |
| 12 Reports | 9 | 0 | 4 | 3 | 2 |
| 13 Settings | 5 | 0 | 3 | 2 | – |
| 14 Audit | 3 | 0 | 2 | – | 1 |
| 15 Customer Portal | 11 | 0 | 8 | 3 | – |
| 16 Seed & Demo | 6 | 0 | 4 | 2 | – |
| **Total** | **153** | **23** | | | |

---

## Module 0 — Foundation

- [x] `F-01` **P0·S** Repo scaffold: monorepo `backend/` + `frontend/` + `docs/`, `.gitignore`, README
- [x] `F-02` **P0·S** Django project: `config/settings/{base,local,production}.py`, `.env.example`, env-var loading
- [x] `F-03` **P0·S** `/api/v1/` router + `/api/v1/health/` endpoint
- [x] `F-04` **P0·M** `requirements/{base,local,production}.txt`: Django, DRF, simplejwt, django-filter, psycopg, celery, redis
- [x] `F-05` **P0·S** React/Vite + TS scaffold: `src/app/`, `layouts/` stubs, Tailwind theme tokens
- [x] `F-06` **P0·M** `services/apiClient.ts` skeleton: baseURL from env, single Axios instance
- [x] `F-07` **P0·S** `docker-compose.yml`: postgres:15, redis:7, django:8000, web:5173
- [x] `F-08` **P0·S** CORS config (allow Vite origin), JWT lib installed & wired to DRF settings
- [x] `F-09` **P0·M** `common/models.py`: `TimeStampedModel`, `TenantScopedModel` (business FK)
- [x] `F-10` **P0·M** `common/viewsets.py` + `common/permissions.py`: `TenantScopedViewSet` (queryset filter + force business on create), `IsSameBusiness` (404 not 403), `RoleBasedPermission`
- [x] `F-11` **P0·M** `common/`: pagination envelope, unified exception handler (`{error:{code,message,fields}}`), constants
- [x] `F-12` **P0·M** CI skeleton: ruff + pytest, eslint + tsc + vitest; branch protection on `develop`

**Exit:** docker compose up fresh-clone works; CI green; base classes importable.

---

## Module 1 — Authentication

- [x] `A-01` **P0·M** Custom `User` model: business FK (nullable for super admin), role enum (SUPER_ADMIN/OWNER/MANAGER/DELIVERY_STAFF/KITCHEN_STAFF/CUSTOMER), is_active, phone
- [x] `A-02` **P0·S** Migration + Django admin registration
- [x] `A-03` **P0·M** `POST /auth/login/` — returns access, refresh, user, business
- [x] `A-04` **P0·S** `POST /auth/refresh/`, `POST /auth/logout/` (blacklist), `GET /auth/me/`
- [x] `A-05` **P0·S** DRF throttling on login endpoint
- [x] `A-06` **P0·M** First-owner bootstrap: management command `bootstrap_business` (business + owner in one tx)
- [x] `A-07` **P0·M** Backend tests: login ok/bad creds/inactive user, refresh rotation, logout blacklists, /me roles
- [x] `A-08` **P0·M** Frontend `authStore` (Zustand): access in memory, refresh in secure storage
- [x] `A-09` **P0·M** apiClient interceptors: attach Bearer; 401 → refresh once → retry → clear store → `/login`
- [x] `A-10` **P0·M** LoginPage, protected-route wrapper, role-based `routes.tsx` trees + AdminLayout/CustomerLayout/StaffLayout shells

**Decision needed before A-08:** refresh token in httpOnly cookie (preferred) vs memory — see development_plan.md §Open Decisions.

---

## Module 2 — Business / Tenant

- [x] `B-01` **P0·S** `Business` model: name, phone, email, address, logo, status (ACTIVE/INACTIVE/SUSPENDED), timestamps
- [ ] `B-02` **P0·S** Serializers + tenant-scoped viewset (owner-only write)
- [ ] `B-03` **P0·M** **Isolation tests:** user of Business B gets 404 on Business A objects — must cover TenantScopedViewSet + IsSameBusiness paths
- [ ] `B-04` **P1·S** Logo upload placeholder (local media now, S3-ready interface)
- [ ] `B-05` **P0·S** Frontend business profile page + edit form
- [ ] `B-06` **P0·S** businessStore (current business context in Zustand)

---

## Module 3 — Users & Staff

- [ ] `U-01` **P0·M** Staff CRUD endpoints in `accounts`: list/create/update/activate/deactivate, role assign
- [ ] `U-02` **P0·M** Role permission matrix enforced per poc §3 (map roles → viewset actions)
- [ ] `U-03` **P0·M** Tests: owner can manage staff; manager scoping; staff cannot access staff mgmt; isolation
- [ ] `U-04` **P1·S** Invite/onboard flow placeholder (create user + temp password for POC)
- [ ] `U-05` **P0·M** Frontend staff page: table, add/edit modal, role select, active toggle
- [ ] `U-06` **P1·S** Login-as-staff smoke check: each role lands on correct layout

---

## Module 4 — Customers

- [ ] `C-01` **P0·M** `Customer` model: customer_code (auto), business FK, user FK (nullable, portal link), name, phone, email, address, location, lat/lng, notes, status (ACTIVE/INACTIVE/BLOCKED)
- [ ] `C-02` **P0·S** Indexes: `(business_id, name)`, `(business_id, phone)`; migration
- [ ] `C-03` **P0·S** Serializers (create/update/list/detail) + Zod-equivalent validation rules
- [ ] `C-04` **P0·S** CRUD viewset on TenantScopedViewSet + status transitions
- [ ] `C-05` **P0·M** Search (name/phone/code/address) + filters (status, has-active-subscription, meal) + sort + pagination via django-filter + `CustomerSelector`
- [ ] `C-06` **P0·M** Tests: CRUD, search hit/miss, filters, pagination, isolation, customer_code uniqueness per business
- [ ] `C-07` **P0·M** Customer detail aggregate endpoint: profile + current subscription + payment/delivery/skip/pause histories — via other apps' **selectors** (read-only)
- [ ] `C-08` **P1·S** Soft-delete or deactivate semantics decided & implemented
- [ ] `C-09` **P0·M** Frontend `customersApi.ts` + types + validation
- [ ] `C-10` **P0·M** CustomersPage: search-first table, filter chips (status/subscription/meal), pagination
- [ ] `C-11` **P0·M** CustomerForm (modal/page) with loading/error states
- [ ] `C-12` **P0·M** CustomerDetailsPage: info card + tabbed history (subscriptions/payments/deliveries/skips/pauses)
- [ ] `C-13` **P1·S** Empty states + skeleton loaders
- [ ] `C-14` **P0·S** Module DoD check + commit

---

## Module 5 — Meals

- [ ] `M-01` **P0·S** `Meal` model: business FK, name, description, price (nullable), is_active
- [ ] `M-02` **P0·S** CRUD endpoints + tests (incl. is_active filtering)
- [ ] `M-03` **P0·S** mealsApi + types
- [ ] `M-04` **P0·S** Meals list page + form + active/inactive toggle
- [ ] `M-05` **P1·S** Seed defaults (Breakfast/Lunch/Dinner/Snacks) in bootstrap command

---

## Module 6 — Plans

- [ ] `P-01` **P0·M** `Plan` model: business FK, name, description, duration_days, price, meal FK, total_meals, skip_allowed, pause_allowed, is_active
- [ ] `P-02` **P0·S** Validation: total_meals vs duration consistency, price ≥ 0
- [ ] `P-03` **P0·S** CRUD endpoints + tests (isolation, deactivate does not break existing subs)
- [ ] `P-04` **P0·S** plansApi + types + validation
- [ ] `P-05` **P0·M** Plans list + form pages ("Monthly Lunch ₹2500" creatable)
- [ ] `P-06` **P1·S** Plan card UI with skip/pause badges

---

## Module 7 — Subscriptions ⭐

- [ ] `S-01` **P0·M** `Subscription` model: business/customer/plan FKs, start_date, end_date, status (PENDING/ACTIVE/PAUSED/EXPIRED/CANCELLED), total_amount, paid_amount, pending_amount, remaining_meals
- [ ] `S-02` **P0·S** Index `(business_id, status, end_date)`; migration
- [ ] `S-03` **P0·S** State-machine constant map: legal transitions table (arch §6.4) in `constants.py`
- [ ] `S-04` **P0·M** `SubscriptionService.create_subscription()`: validate customer & plan same business → PENDING; transaction
- [ ] `S-05` **P0·S** `POST /subscriptions/` + list/detail viewset with filters (status, customer, plan)
- [ ] `S-06` **P0·M** Action endpoints `pause/` `resume/` `cancel/` — validate transition legality, wrap in tx, return updated resource
- [ ] `S-07` **P0·M** `renew/` action: new period dates, counter resets, link to previous period
- [ ] `S-08` **P0·M** `SubscriptionSelector.get_expiring_subscriptions()`: `status=ACTIVE AND end_date <= today+3` — EXPIRING computed, never stored
- [ ] `S-09` **P0·S** Remaining-days / remaining-meals calculators (service or model helpers, single source)
- [ ] `S-10` **P0·L** Tests: every legal transition, every illegal transition rejected, renewal math, expiry query windows, isolation, concurrent pause race
- [ ] `S-11` **P0·M** subscriptionsApi + types + validation
- [ ] `S-12` **P0·M** SubscriptionsPage: list + status filter tabs (incl. computed "Expiring")
- [ ] `S-13` **P0·M** SubscriptionCard per poc §20: dates, days remaining, status badge, amount paid/pending
- [ ] `S-14` **P0·M** SubscriptionForm: customer + plan pickers (same-business only), dates, amount preview
- [ ] `S-15` **P0·M** Action dialogs: pause/resume/cancel/renew with confirm + reason input
- [ ] `S-16` **P1·S** RenewalDialog with new-period preview

---

## Module 8 — Payments

- [ ] `PAY-01` **P0·M** `Payment` model: business/customer/subscription FKs, amount, method (CASH/UPI/BANK_TRANSFER/CARD/ONLINE/OTHER), transaction_reference, payment_date, status (PENDING/PAID/FAILED/REFUNDED/PARTIAL), notes
- [ ] `PAY-02` **P0·S** Index `(subscription_id)`; migration
- [ ] `PAY-03` **P0·M** `PaymentService.record_payment()`: insert → recalc paid/pending → subscription status per poc §26 (PAID / PARTIAL / PENDING) — single tx
- [ ] `PAY-04` **P0·L** Activation chain: full payment → subscription ACTIVE → call `DeliveryService.generate_delivery_schedule()` → call `NotificationService.emit()` (stub) — services-to-services, no cross-model writes
- [ ] `PAY-05` **P0·M** Endpoints: `GET/POST /payments/`, `GET /payments/{id}/` (read-only after create; corrections = new payment)
- [ ] `PAY-06` **P0·M** Payment summary selector: today's collection, month, pending, partial, failed, refunded (poc §24)
- [ ] `PAY-07` **P0·L** Tests: amount math incl. overpay guard, partial flows, status flips, activation chain ordering, rollback on failure, isolation
- [ ] `PAY-08` **P0·M** paymentsApi + types + validation
- [ ] `PAY-09` **P0·M** Record-payment flow on PENDING subscription (form: amount, method, reference)
- [ ] `PAY-10` **P0·M** PaymentsPage: history table + status badges + per-customer filter
- [ ] `PAY-11` **P1·S** Payment summary cards (Today/Month/Pending)
- [ ] `PAY-12` **P0·M** **Golden workflow e2e** (poc §34): Add Customer → Plan → Payment → ACTIVE — manual + automated test

---

## Module 9 — Deliveries + Skip/Pause

- [ ] `D-01` **P0·M** `Delivery` model: business/customer/subscription FKs, delivery_date, meal_type, status (PENDING/OUT_FOR_DELIVERY/DELIVERED/NOT_DELIVERED/SKIPPED/CANCELLED), assigned_staff FK, delivered_at, notes
- [ ] `D-02` **P0·S** Index `(business_id, delivery_date, status)`; migration
- [ ] `D-03` **P0·M** `DeliveryService.generate_delivery_schedule()`: bulk insert PENDING rows for subscription period (idempotent — safe to re-run)
- [ ] `D-04` **P0·M** `DeliverySelector.get_today_deliveries()` + `GET /deliveries/today/`
- [ ] `D-05` **P0·M** `PATCH /deliveries/{id}/status/`: delivery staff restricted to assigned rows + status/notes only; transition validation
- [ ] `D-06` **P0·M** Delivery history endpoint with filters (date range, staff, status, customer)
- [ ] `D-07` **P0·M** `MealSkip` + `SubscriptionPause` models + migrations
- [ ] `D-08` **P0·M** Skip flow: skip request → that day's delivery → SKIPPED → rule applied
- [ ] `D-09` **P0·M** Configurable skip/pause rule per business (extend / meal credit / none) — read from settings app, no hard-coded branch per business
- [ ] `D-10` **P0·M** Pause flow: date-range pause → deliveries in range CANCELLED/SKIPPED → resume restores PENDING or extends end_date per rule
- [ ] `D-11` **P0·M** Kitchen counts endpoint: today's meal totals per meal type (poc §23)
- [ ] `D-12` **P0·L** Tests: schedule generation counts, staff scoping (cannot touch unassigned), status transitions, skip→rule paths ×3, pause/resume date math
- [ ] `D-13` **P0·M** Celery + Redis wired in settings; celery_app.py; worker + beat services in docker-compose
- [ ] `D-14` **P0·M** Celery Beat jobs: nightly next-day delivery generation; nightly expiry sweep (mark EXPIRED where end_date < today)
- [ ] `D-15` **P0·M** Frontend TodayDeliveriesPage: customer, phone, address, meal, status + big Mark Delivered / Not Delivered / Skip buttons + note input
- [ ] `D-16` **P1·M** DeliveryHistoryPage + filters; kitchen meal-counts view (StaffLayout); admin skip/pause UI

---

## Module 10 — Dashboard

- [ ] `DB-01` **P0·M** Aggregator endpoint (poc §18): active customers, new customers, today's meals, today's deliveries, expiring today, expiring this week, pending payments, today's revenue — via other apps' selectors, owns **no** data
- [ ] `DB-02` **P0·M** Tests vs seeded fixtures (exact numbers)
- [ ] `DB-03` **P0·S** dashboardApi + types
- [ ] `DB-04` **P0·M** DashboardPage + StatCard row
- [ ] `DB-05` **P0·M** ExpiryWidget: Today / Tomorrow / 3 Days / This Week / Expired
- [ ] `DB-06` **P0·M** DeliveryWidget (today's list preview + counts)
- [ ] `DB-07` **P1·M** PaymentWidget (pending/partial) + MealSummaryWidget
- [ ] `DB-08` **P1·S** Quick actions on dashboard: add customer, record payment (deep-links into forms)

---

## Module 11 — Notifications

- [ ] `N-01` **P0·M** `Notification` model: business/user FKs, type, title, message, is_read, sent_at
- [ ] `N-02` **P0·M** `NotificationService.emit()`: IN_APP channel now; channel interface abstracted for future WhatsApp/SMS/Email (mod. plan §14)
- [ ] `N-03` **P0·M** Wire emitters from services: PAYMENT_RECEIVED, SUBSCRIPTION_RENEWED, DELIVERY_UPDATE
- [ ] `N-04` **P0·M** Nightly Celery job: SUBSCRIPTION_EXPIRING (≤3d) + SUBSCRIPTION_EXPIRED
- [ ] `N-05` **P0·M** Endpoints: list mine, unread count, mark read (single + all)
- [ ] `N-06` **P0·M** Tests: events fire on correct triggers, no dupes, scoping
- [ ] `N-07` **P0·M** Frontend bell + dropdown + unread badge
- [ ] `N-08` **P1·S** Notification preferences stub in settings (per-type mute)

---

## Module 12 — Reports

- [ ] `R-01` **P0·M** Customer report selector + endpoint (total/active/inactive/new/cancelled/paused)
- [ ] `R-02` **P0·M** Subscription report (active/expiring/expired/renewed/cancelled)
- [ ] `R-03` **P0·M** Revenue report: daily/weekly/monthly series + pending (live tables via selectors — **no** reporting store)
- [ ] `R-04` **P0·M** Meal report (per type: delivered/skipped/not delivered)
- [ ] `R-05` **P1·M** Payment report detail + date-range params on all reports
- [ ] `R-06` **P0·M** Tests: aggregates reconcile against seeded data exactly
- [ ] `R-07` **P0·M** Reports pages with Recharts: revenue trend
- [ ] `R-08` **P1·M** Charts: meal distribution + subscription status breakdown; date-range filters
- [ ] `R-09` **P2·S** CSV export

---

## Module 13 — Settings

- [ ] `ST-01` **P0·M** BusinessSettings model: max skip days, min pause duration, skip rule (extend/credit/none), notification prefs, delivery time window
- [ ] `ST-02` **P0·M** Endpoints (owner-only write) + tests; consumed by D-09 logic
- [ ] `ST-03` **P0·S** Settings admin UI (grouped form)
- [ ] `ST-04` **P1·S** Business profile link + logo upload UI
- [ ] `ST-05` **P1·S** Validation UX: warn on rule changes affecting active subscriptions

---

## Module 14 — Audit Trail

- [ ] `AU-01` **P0·S** `AuditLog` model: business/user, action, entity_type, entity_id, description, created_at (poc §29)
- [ ] `AU-02` **P0·M** Write hooks from services on state-changing actions (subscription transitions, payments, delivery status, staff changes)
- [ ] `AU-03` **P2·S** Django admin view + simple filter; (frontend UI deferred)

---

## Module 15 — Customer Portal

- [ ] `PT-01` **P0·L** Customer-role API scoping: self-only reads (subscription/payments/deliveries), skip + pause-request + renew actions; **no admin APIs reachable** (mod. plan §38)
- [ ] `PT-02` **P0·M** Permission tests: customer token cannot list other customers, other subscriptions, staff pages
- [ ] `PT-03` **P0·M** CustomerLayout + portal dashboard (poc §25): greeting, current plan, days remaining, today's meal status
- [ ] `PT-04` **P0·M** My Subscription page + Skip Meal / Pause / Renew wired to portal-scoped endpoints
- [ ] `PT-05` **P0·M** Portal payments + delivery history pages
- [ ] `PT-06` **P1·M** Profile view/edit (limited fields)
- [ ] `PT-07` **P0·M** Staff layouts finalized: Delivery (Today's Deliveries, Completed) + Kitchen (Today's Meals, Summary) per poc §32
- [ ] `PT-08` **P0·S** Route guards re-verified for all 4 roles
- [ ] `PT-09` **P0·M** DRF throttling: auth + write-heavy + portal endpoints
- [ ] `PT-10` **P1·S** Mobile-responsive pass on portal + staff screens (primary use: phone)
- [ ] `PT-11` **P1·S** Error/toast polish across portal actions

---

## Module 16 — Seed Data & Demo

- [ ] `SD-01` **P0·L** Seed command (poc §30): 1 business, 3 staff, 20 customers, 5 plans, 20+ subscriptions, 50+ payments, 100+ deliveries — covering every status (active/expiring/expired/paused/pending/partial/skipped/not delivered)
- [ ] `SD-02` **P0·S** Reset command (flush + reseed) for demo runs
- [ ] `SD-03` **P0·M** **Rahul demo dry-run** (poc §39): all 12 steps pass; fix gaps found
- [ ] `SD-04` **P0·M** poc §38 Definition-of-DoD checklist verified (admin 14 items + customer 5 items)
- [ ] `SD-05` **P1·M** DB backup + restore rehearsal; document runbook
- [ ] `SD-06` **P2·S** Final responsive/docs pass; tag `v0.1.0-mvp`

---

## Definition of Done (per task)

A task is **done** when: code complete · tests written & green · CI green · tenant scoping verified (if touching tenant data) · no `TODO` left in touched code · commit message references task ID (e.g. `S-06: subscription pause/resume/cancel actions`).

## Hard Rules (never cut)

1. Tenant isolation tests (B-03, C-06, PT-02)
2. Subscription state machine + illegal-transition tests (S-10)
3. Payment math tests (PAY-07)
4. Golden workflow e2e (PAY-12)
5. Demo dry-run (SD-03) before calling MVP done
