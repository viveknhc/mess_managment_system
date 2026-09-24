🏗️ Mess Management System — Technical Architecture
Stack: Django + Django REST Framework (backend) · React + TypeScript (frontend) · PostgreSQL (database) Architecture style: Modular Monolith, SaaS-ready from day one Companion documents: mess_management_modularization_plan.md, poc.md

1. Purpose
This document translates the modularization plan and product spec into a concrete technical architecture: how the system is structured, how components talk to each other, how data flows through a request, and how the system is deployed and scaled. It is the reference for making implementation decisions consistently across modules.

2. Architecture Decision: Stack Validation
Before the diagrams, the stack choice itself, made explicit:

Requirement from the spec	Why Django + DRF + React satisfies it
Multi-tenant data isolation (Business A ≠ Business B)	Centralized queryset filtering + permission classes at the ORM layer, not per-view logic
CRUD-heavy domains (customers, plans, subscriptions, payments)	DRF ModelViewSet/serializers map almost directly onto the API design in the spec
Role-based access (Owner, Manager, Delivery, Kitchen, Customer)	DRF permission classes + Django's built-in auth/groups
Admin/ops visibility without building custom tooling	Django Admin, free, for internal support/debugging
Background work (expiry checks, notifications, future WhatsApp/SMS)	Celery integrates natively with Django
Small team, fast MVP, need to hire easily later	Django/DRF and React are both mainstream, well-documented, large hiring pool
Future SaaS scaling, possible service extraction	Modular monolith with clean app boundaries → extractable later (Section 13)
Where this stack is not ideal: true real-time features (live GPS tracking, live delivery-staff location) don't fit a synchronous WSGI request/response cycle well. That's explicitly a future feature in your spec — when it's needed, it's added as a narrow ASGI (Django Channels) or a small standalone WebSocket service, not a reason to change the core stack now.

Alternatives considered:

Option	Verdict for this project
FastAPI + React	Async-native, faster raw throughput, but no built-in admin, weaker batteries-included auth/permissions — you'd rebuild what Django gives free. Better fit if the product were API-throughput-bound; this one isn't.
Node/NestJS + React	One language end-to-end; reasonable choice if the team is JS-only. NestJS's module system actually mirrors your modularization plan well, but Django's ORM + admin + migrations are more mature for this kind of data-modeling-heavy app.
Ruby on Rails + React	Similar "batteries included" philosophy to Django, smaller hiring pool.
Django + DRF + React ✅	Best match for the actual requirements: multi-tenant CRUD, reporting, moderate scale, fast MVP delivery.
3. Technology Stack
Layer	Technology	Notes
Frontend	React 18 + TypeScript + Vite	Fast dev server, native TS support
Styling	Tailwind CSS	Matches "simple, fast, mobile-responsive" UX goal
Frontend state	Zustand	Global/shared state only (auth, current business) — see §7.2
Forms/validation	React Hook Form + Zod	Shared validation shapes, typed forms
Charts	Recharts	Dashboard + reports
HTTP client	Axios	Interceptors for token refresh
Backend framework	Django + Django REST Framework	Modular monolith, see §6
Auth	JWT (djangorestframework-simplejwt)	Access + refresh token flow
Database	PostgreSQL	Relational, strong constraint support for tenant isolation
Async/background jobs	Celery + Redis	Expiry checks, notifications, future WhatsApp/SMS/email
Containerization	Docker + Docker Compose	Local dev parity with production
CI/CD	GitHub Actions (or equivalent)	Lint → test → deploy
Object storage (future)	S3-compatible	Business logos, receipts, future media
4. System Context Diagram
Future External Integrations

Data Layer

Async Layer

Django Modular Monolith

Edge

Client Layer

future

future

future

Admin / Staff Portal - React SPA

Customer Portal - React SPA

Nginx / Reverse Proxy

DRF API Layer

Authentication

Business/Tenant

Customers

Meals & Plans

Subscriptions

Payments

Deliveries

Notifications

Dashboard & Reports

Redis

Celery Worker

Celery Beat - scheduled jobs

PostgreSQL

Razorpay

WhatsApp API

SMS Gateway

Everything inside the "Django Modular Monolith" box is one deployable application — the boxes are Django apps (Python packages), not separate services. This is deliberate: Section 13 of the modularization plan is explicit that microservices are a future option, not a starting point.

5. Multi-Tenancy Architecture
Every business-owned model carries a business_id foreign key. Isolation is enforced in one place, not repeated per view:

attaches request.business

Incoming Request + JWT

TenantMiddleware

ViewSet

Base QuerySet: filter business=request.business

PostgreSQL

Implementation pattern:

A TenantScopedModel abstract base model provides business FK on every tenant-owned model.
A TenantScopedViewSet base class (in common/) overrides get_queryset() to always filter by request.user.business_id, and overrides perform_create() to force-set business on save. Individual views inherit this — they never write raw Model.objects.all().
A DRF permission class (IsSameBusiness) double-checks object-level access on retrieve/update/delete, so even a guessed ID from another tenant returns 404, not 403 (avoids leaking existence).
SUPER_ADMIN role bypasses the filter for platform-level operations (future SaaS admin).
This satisfies Rule 10 from the modularization plan: "Keep tenant/business isolation at the backend level" — the frontend never decides what a user can see; it only reflects what the API already scoped.

6. Backend Architecture
6.1 Layered structure inside each Django app
Every domain app (customers/, subscriptions/, payments/, etc.) follows the same internal layering, per the modularization plan:

views.py - HTTP handling

serializers.py - I/O validation

services.py - business operations

selectors.py - complex read queries

models.py

permissions.py

PostgreSQL

views.py stays thin: parses request, calls a service or selector, returns a response. No business logic here.
services.py holds multi-step business operations (e.g. SubscriptionService.renew_subscription()), and is what calls into other apps' services when a workflow spans modules.
selectors.py holds non-trivial read queries (SubscriptionSelector.get_expiring_subscriptions()), keeping query complexity out of views and serializers.
permissions.py encodes role + tenant checks.
This mirrors §21–23 of the modularization plan directly — nothing new is invented here, this section just wires it into request/response flow.

6.2 Module dependency graph
Authentication

Business/Tenant

Users & Staff

Customers

Meals

Plans

Subscriptions

Payments

Deliveries

Notifications

Dashboard

Reports

Settings

Rule enforced in code review: an app may import another app's services/selectors (its public interface), but never its models directly for writes, and never reach across to another app's views. This is what keeps the dependency arrows one-directional as the plan requires.

6.3 Example cross-module flow: creating and activating a subscription
This is the flow described in §26 of poc.md, drawn as an actual sequence:

PostgreSQL
NotificationService
DeliveryService
PaymentService
SubscriptionService
DRF API
Admin (React)
PostgreSQL
NotificationService
DeliveryService
PaymentService
SubscriptionService
DRF API
Admin (React)
alt
[fully paid]
POST /api/subscriptions/ {customer_id, plan_id}
create_subscription()
validate customer & plan belong to same business
INSERT Subscription (status=PENDING)
201 Created (PENDING)
POST /api/payments/ {subscription_id, amount}
record_payment()
INSERT Payment
recalculate paid_amount / pending_amount
UPDATE Subscription status=ACTIVE
generate_delivery_schedule(start_date, end_date, meal_type)
bulk INSERT Delivery rows (status=PENDING)
emit SUBSCRIPTION_RENEWED
INSERT Notification
201 Created (payment + updated subscription)
Note the pattern: SubscriptionService never imports DeliveryModel or NotificationModel directly — it calls DeliveryService.generate_delivery_schedule() and NotificationService.emit(). This is the "services talk to services" rule from §27 of the modularization plan.

6.4 Subscription state machine
created, awaiting payment

payment recorded

pause requested

resumed

end_date passed (calculated)

cancelled

cancelled

renewed (new period)

PENDING

ACTIVE

PAUSED

EXPIRED

CANCELLED

EXPIRING is deliberately not a stored state — it's computed at query time (end_date - today <= 3 days AND status = ACTIVE), exactly as the spec calls out. This avoids a scheduled job having to "catch" every subscription at the right moment; it's always correct at read time.

6.5 Backend project layout
backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py          # for future websocket/Channels needs
│   └── wsgi.py
│
├── apps/
│   ├── accounts/         # Auth + User + Staff
│   ├── businesses/       # Business/Tenant
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   ├── dashboard/
│   └── reports/
│
├── common/
│   ├── models.py         # TenantScopedModel, TimeStampedModel
│   ├── viewsets.py        # TenantScopedViewSet
│   ├── permissions.py     # IsSameBusiness, RoleBasedPermission
│   ├── pagination.py
│   ├── exceptions.py      # unified error handler
│   └── constants.py
│
├── celery_app.py
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
└── .env.example
7. Frontend Architecture
7.1 Project structure
src/
├── app/
│   ├── App.tsx
│   ├── routes.tsx          # role-based route trees (Admin / Customer / Staff)
│   └── providers.tsx
│
├── layouts/
│   ├── AdminLayout.tsx
│   ├── CustomerLayout.tsx
│   └── StaffLayout.tsx
│
├── features/                # one folder per domain, mirrors backend apps
│   ├── auth/
│   ├── business/
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   ├── dashboard/
│   └── reports/
│
├── components/ui/           # generic, reusable, no domain knowledge
├── services/apiClient.ts    # single Axios instance
├── store/                   # Zustand — shared state only
├── hooks/
├── utils/
└── types/
Each features/<domain>/ folder is self-contained: <domain>Api.ts, <domain>Types.ts, <domain>Validation.ts, pages/, components/. A feature never imports another feature's internals — if subscriptions needs customer data, it calls customersApi, not customers/components/CustomerForm.

7.2 State management boundaries
Local to feature (React Query / component state)

customer list/detail

subscription list/detail

payment list

delivery list

Zustand (global, shared)

authStore

businessContext

uiPreferences

Per §25 of the modularization plan: Zustand holds only truly cross-cutting state (who's logged in, which business, UI prefs). Domain lists/detail data stay close to the feature that fetches them — recommend TanStack Query on top of Axios for this layer (caching, refetch-on-focus, optimistic updates for actions like "mark delivered"), even though it wasn't named explicitly in poc.md; it solves exactly the "don't dump every API response into Zustand" rule with less hand-rolled code.

7.3 API client
// services/apiClient.ts (shape, not full implementation)
- baseURL from env (VITE_API_BASE_URL)
- request interceptor: attach Authorization: Bearer <access_token>
- response interceptor: on 401 → attempt refresh once → retry original request
                         on refresh failure → clear authStore → redirect to /login
Every features/*/api.ts file imports this one client — no feature creates its own Axios instance.

8. API Architecture
8.1 Conventions
Base path: /api/v1/ (versioned from day one — cheap now, expensive to retrofit).
Resource-based URLs, plural nouns: /api/v1/customers/, /api/v1/subscriptions/{id}/pause/.
Standard verbs: GET/POST/PUT/PATCH/DELETE; state transitions as POST actions (/subscriptions/{id}/pause/, /renew/, /cancel/) rather than overloading PATCH with a status field — keeps business-rule validation (e.g. "can't pause a CANCELLED subscription") in one place per action.
Pagination: DRF PageNumberPagination, consistent envelope:
{
  "count": 142,
  "next": "...",
  "previous": null,
  "results": [ /* items */ ]
}
Filtering: django-filter per viewset (?status=ACTIVE&meal=LUNCH), matching the filter UI described in §19 of poc.md.
Errors: a single DRF exception handler (common/exceptions.py) normalizes all error responses to:
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "fields": { "phone": ["This field is required."] }
  }
}
8.2 Authentication flow
Django API
React App
Browser
Django API
React App
Browser
access token expires (~15 min)
refresh_token expires / logout
enter credentials
POST /api/v1/auth/login/
{ access_token, refresh_token, user, business }
store access_token in memory, refresh_token in httpOnly cookie (preferred) or secure storage
GET /api/v1/auth/me/ (Authorization: Bearer access_token)
profile + role + business_id
POST /api/v1/auth/refresh/ (refresh_token)
new access_token
POST /api/v1/auth/logout/ (blacklist refresh_token)
Access tokens are short-lived (~15 min) and kept in memory only; refresh tokens are longer-lived and, where the deployment allows it, stored in an httpOnly secure cookie rather than localStorage — directly satisfying the spec's security requirement: "No sensitive information in frontend local storage where avoidable."

8.3 Endpoint summary (from poc.md, unchanged — this doc doesn't redefine it)
The full endpoint list is already specified in §17 of poc.md (/customers/, /plans/, /subscriptions/{id}/pause|resume|renew|cancel/, /payments/, /deliveries/today/, /reports/*). This architecture doc's job is the how, not re-listing the what — see that section for the authoritative endpoint list.

9. Data Architecture
9.1 Core entity relationships
employs

has

defines

offers

used in

subscribes

based on

paid via

generates

records

records

receives

BUSINESS

uuid

id

PK

string

name

string

status

USER

uuid

id

PK

uuid

business_id

FK

string

role

bool

is_active

CUSTOMER

uuid

id

PK

uuid

business_id

FK

string

customer_code

string

status

MEAL

uuid

id

PK

uuid

business_id

FK

string

name

bool

is_active

PLAN

uuid

id

PK

uuid

business_id

FK

int

duration_days

decimal

price

int

total_meals

SUBSCRIPTION

uuid

id

PK

uuid

business_id

FK

uuid

customer_id

FK

uuid

plan_id

FK

date

start_date

date

end_date

string

status

decimal

total_amount

decimal

paid_amount

int

remaining_meals

PAYMENT

uuid

id

PK

uuid

subscription_id

FK

decimal

amount

string

payment_method

string

status

DELIVERY

uuid

id

PK

uuid

subscription_id

FK

date

delivery_date

string

meal_type

string

status

MEALSKIP

uuid

id

PK

uuid

subscription_id

FK

date

date

SUBSCRIPTIONPAUSE

uuid

id

PK

uuid

subscription_id

FK

date

start_date

date

end_date

NOTIFICATION

uuid

id

PK

uuid

user_id

FK

string

type

bool

is_read

Field lists match §7–13 of poc.md exactly; this diagram just makes the relationships explicit for schema design and migration planning.

9.2 Indexing priorities (for launch, not exhaustive)
Table	Index	Why
every tenant table	(business_id)	every query filters by tenant first
subscription	(business_id, status, end_date)	expiry queries (§21 poc.md) run constantly
delivery	(business_id, delivery_date, status)	"today's deliveries" is a hot path
customer	(business_id, name), (business_id, phone)	search (§27 poc.md)
payment	(subscription_id)	payment history lookups
9.3 Reports — no separate warehouse for MVP
Per §16 of poc.md, reports query live operational tables directly (via selectors.py), not a duplicated reporting store. If report queries become a performance bottleneck as data grows, the escalation path is: (1) add read replicas, (2) add materialized views for the heaviest aggregates — not a new database.

10. Security Architecture
Request

HTTPS/TLS termination at Nginx

JWT validation

Role-based permission check

Tenant-scoped queryset

Serializer validation + sanitization

Rate limiting - DRF throttling

View/Service logic

Audit log for admin actions

Requirement (from poc.md §36)	Mechanism
JWT authentication	djangorestframework-simplejwt
Password hashing	Django's default (PBKDF2/Argon2) — never rolled by hand
Role-based permissions	DRF permission classes per viewset, mapped to the role table below
Business-level data isolation	TenantScopedViewSet (§5) — enforced backend-side, never trusted from frontend
API validation / input sanitization	DRF serializers + Zod on the frontend (defense in depth, not either/or)
Rate limiting	DRF ScopedRateThrottle on auth + write-heavy endpoints
HTTPS in production	Enforced at Nginx/load balancer
Secure env vars	.env + secrets manager in production, never committed
Audit trail	AuditLog model (poc.md §29), written from services.py on state-changing actions
Role permission matrix (condensed from poc.md §3):

Role	Customers	Plans/Meals	Subscriptions	Payments	Deliveries	Reports	Settings
Owner/Manager	CRUD	CRUD	CRUD	CRUD	CRUD	Read	CRUD
Delivery Staff	Read (assigned only)	–	–	–	Update status + notes	–	–
Kitchen Staff	–	Read (counts)	–	–	Read (counts)	–	–
Customer	Read (self)	Read	Read + skip/pause/renew (self)	Read (self)	Read (self)	–	–
11. Infrastructure & Deployment
11.1 Local development
docker-compose.yml

proxy /api

react - Vite dev server :5173

django - runserver :8000

postgres:15 :5432

redis:7 :6379

One docker-compose.yml, one .env, docker compose up gives a new developer the full stack — matches Phase 1 of poc.md's development phases.

11.2 Production
Internet

Nginx / Load Balancer + TLS

Static React build - CDN or Nginx

Gunicorn + Django - instance 1

Gunicorn + Django - instance 2

Managed PostgreSQL

Managed Redis

Celery Worker

Celery Beat

Object storage: logos, receipts

Django app instances are stateless (JWT means no server-side session store), so horizontal scaling is just "add another Gunicorn instance behind the load balancer" — no sticky sessions needed.

11.3 CI/CD
Feature branch

Pull Request

CI: lint + backend tests + frontend tests

Code review

Merge to develop

Auto-deploy to staging

Manual QA

Merge to main

Deploy to production

Matches the Git branch strategy already defined in §32 of the modularization plan (feature/* → develop → main).

12. Background Jobs (Celery + Redis)
Not explicitly named in poc.md's stack list, but required to implement several features it does specify without blocking the request/response cycle:

Job	Trigger	Why async
Generate next day's delivery records	Celery Beat, nightly	Bulk insert across all active subscriptions — shouldn't block any user request
Mark subscriptions EXPIRED	Celery Beat, nightly (or computed at read-time — see §6.4, either works; scheduled write is only needed if you want EXPIRED to be a real stored state for historical reporting)	Batch operation
Send notifications (in-app now, WhatsApp/SMS/email later)	Triggered by service-layer events	Decouples SubscriptionService from notification delivery mechanics, exactly matching poc.md's notification architecture diagram
Future: Razorpay webhook processing	Webhook receiver → queued job	Webhooks must return fast; processing happens off the request thread
This is the one addition beyond what's explicitly listed in your two source documents — it's the standard way Django implements the "Subscription Module → event → Notification Service" architecture your modularization plan already describes conceptually.

13. Scalability & Evolution Path
Per §40 of the modularization plan: start monolith, extract later, only if needed.

If/when a module outgrows the monolith

Today: Modular Monolith

only if module has independent scaling/team needs

Django app - all modules, one deploy

Core API: Auth, Business, Customers, Subscriptions

Payment Service

Notification Service

Delivery Service

Analytics Service

Because each module already respects the service/selector boundaries in §6.1–6.2, extraction later means moving a Django app to its own deployment and replacing in-process service calls with HTTP/message-queue calls — not a rewrite. Concretely, Notifications and Payments are the two most likely first candidates to split out, since they're the ones most likely to gain heavy external-integration surface area (WhatsApp/SMS providers, Razorpay).

14. Non-Functional Requirements
Category	Target for MVP
Availability	Single-region, single environment acceptable for MVP; multi-instance app servers for basic redundancy
Performance	List/dashboard endpoints < 300ms p95 with proper indexing (§9.2); acceptable given data volumes in §30 of poc.md (dozens–hundreds of records per business at MVP stage)
Logging	Structured JSON logs from Django + Celery; correlate by request_id
Monitoring	Basic APM (e.g. Sentry for errors, simple uptime checks) from day one — cheap now, invaluable once real customers are on it
Testing	Backend: pytest-django covering auth, permissions, tenant isolation, subscription/payment calculations, expiry logic (poc.md §37). Frontend: component + integration tests for forms, protected routes, and the core Rahul-style workflow (poc.md §39)
Backups	Automated daily PostgreSQL backups, tested restore process before first paying customer
15. Summary
Architecture style: modular monolith — one Django app, one React app, one PostgreSQL database, clean internal module boundaries (per §43 of the modularization plan).
Stack validation: Django + DRF + React is well-matched to this specific product (multi-tenant CRUD + reporting), not a generic default — see §2 for the reasoning and alternatives.
What this document adds beyond the two source docs: concrete request-flow diagrams (auth, subscription creation), the tenant-isolation mechanism, the layered service/selector pattern wired into actual request handling, the background-job layer (Celery/Redis) needed to realize the notification/expiry features already specified, and a deployment/scaling path.
Build order stays exactly as defined in poc.md §31 and the modularization plan §30 — this document doesn't change sequencing, only the how of implementation.🏗️ Mess Management System — Technical Architecture
Stack: Django + Django REST Framework (backend) · React + TypeScript (frontend) · PostgreSQL (database) Architecture style: Modular Monolith, SaaS-ready from day one Companion documents: mess_management_modularization_plan.md, poc.md

1. Purpose
This document translates the modularization plan and product spec into a concrete technical architecture: how the system is structured, how components talk to each other, how data flows through a request, and how the system is deployed and scaled. It is the reference for making implementation decisions consistently across modules.

2. Architecture Decision: Stack Validation
Before the diagrams, the stack choice itself, made explicit:

Requirement from the spec	Why Django + DRF + React satisfies it
Multi-tenant data isolation (Business A ≠ Business B)	Centralized queryset filtering + permission classes at the ORM layer, not per-view logic
CRUD-heavy domains (customers, plans, subscriptions, payments)	DRF ModelViewSet/serializers map almost directly onto the API design in the spec
Role-based access (Owner, Manager, Delivery, Kitchen, Customer)	DRF permission classes + Django's built-in auth/groups
Admin/ops visibility without building custom tooling	Django Admin, free, for internal support/debugging
Background work (expiry checks, notifications, future WhatsApp/SMS)	Celery integrates natively with Django
Small team, fast MVP, need to hire easily later	Django/DRF and React are both mainstream, well-documented, large hiring pool
Future SaaS scaling, possible service extraction	Modular monolith with clean app boundaries → extractable later (Section 13)
Where this stack is not ideal: true real-time features (live GPS tracking, live delivery-staff location) don't fit a synchronous WSGI request/response cycle well. That's explicitly a future feature in your spec — when it's needed, it's added as a narrow ASGI (Django Channels) or a small standalone WebSocket service, not a reason to change the core stack now.

Alternatives considered:

Option	Verdict for this project
FastAPI + React	Async-native, faster raw throughput, but no built-in admin, weaker batteries-included auth/permissions — you'd rebuild what Django gives free. Better fit if the product were API-throughput-bound; this one isn't.
Node/NestJS + React	One language end-to-end; reasonable choice if the team is JS-only. NestJS's module system actually mirrors your modularization plan well, but Django's ORM + admin + migrations are more mature for this kind of data-modeling-heavy app.
Ruby on Rails + React	Similar "batteries included" philosophy to Django, smaller hiring pool.
Django + DRF + React ✅	Best match for the actual requirements: multi-tenant CRUD, reporting, moderate scale, fast MVP delivery.
3. Technology Stack
Layer	Technology	Notes
Frontend	React 18 + TypeScript + Vite	Fast dev server, native TS support
Styling	Tailwind CSS	Matches "simple, fast, mobile-responsive" UX goal
Frontend state	Zustand	Global/shared state only (auth, current business) — see §7.2
Forms/validation	React Hook Form + Zod	Shared validation shapes, typed forms
Charts	Recharts	Dashboard + reports
HTTP client	Axios	Interceptors for token refresh
Backend framework	Django + Django REST Framework	Modular monolith, see §6
Auth	JWT (djangorestframework-simplejwt)	Access + refresh token flow
Database	PostgreSQL	Relational, strong constraint support for tenant isolation
Async/background jobs	Celery + Redis	Expiry checks, notifications, future WhatsApp/SMS/email
Containerization	Docker + Docker Compose	Local dev parity with production
CI/CD	GitHub Actions (or equivalent)	Lint → test → deploy
Object storage (future)	S3-compatible	Business logos, receipts, future media
4. System Context Diagram
Future External Integrations

Data Layer

Async Layer

Django Modular Monolith

Edge

Client Layer

future

future

future

Admin / Staff Portal - React SPA

Customer Portal - React SPA

Nginx / Reverse Proxy

DRF API Layer

Authentication

Business/Tenant

Customers

Meals & Plans

Subscriptions

Payments

Deliveries

Notifications

Dashboard & Reports

Redis

Celery Worker

Celery Beat - scheduled jobs

PostgreSQL

Razorpay

WhatsApp API

SMS Gateway

Everything inside the "Django Modular Monolith" box is one deployable application — the boxes are Django apps (Python packages), not separate services. This is deliberate: Section 13 of the modularization plan is explicit that microservices are a future option, not a starting point.

5. Multi-Tenancy Architecture
Every business-owned model carries a business_id foreign key. Isolation is enforced in one place, not repeated per view:

attaches request.business

Incoming Request + JWT

TenantMiddleware

ViewSet

Base QuerySet: filter business=request.business

PostgreSQL

Implementation pattern:

A TenantScopedModel abstract base model provides business FK on every tenant-owned model.
A TenantScopedViewSet base class (in common/) overrides get_queryset() to always filter by request.user.business_id, and overrides perform_create() to force-set business on save. Individual views inherit this — they never write raw Model.objects.all().
A DRF permission class (IsSameBusiness) double-checks object-level access on retrieve/update/delete, so even a guessed ID from another tenant returns 404, not 403 (avoids leaking existence).
SUPER_ADMIN role bypasses the filter for platform-level operations (future SaaS admin).
This satisfies Rule 10 from the modularization plan: "Keep tenant/business isolation at the backend level" — the frontend never decides what a user can see; it only reflects what the API already scoped.

6. Backend Architecture
6.1 Layered structure inside each Django app
Every domain app (customers/, subscriptions/, payments/, etc.) follows the same internal layering, per the modularization plan:

views.py - HTTP handling

serializers.py - I/O validation

services.py - business operations

selectors.py - complex read queries

models.py

permissions.py

PostgreSQL

views.py stays thin: parses request, calls a service or selector, returns a response. No business logic here.
services.py holds multi-step business operations (e.g. SubscriptionService.renew_subscription()), and is what calls into other apps' services when a workflow spans modules.
selectors.py holds non-trivial read queries (SubscriptionSelector.get_expiring_subscriptions()), keeping query complexity out of views and serializers.
permissions.py encodes role + tenant checks.
This mirrors §21–23 of the modularization plan directly — nothing new is invented here, this section just wires it into request/response flow.

6.2 Module dependency graph
Authentication

Business/Tenant

Users & Staff

Customers

Meals

Plans

Subscriptions

Payments

Deliveries

Notifications

Dashboard

Reports

Settings

Rule enforced in code review: an app may import another app's services/selectors (its public interface), but never its models directly for writes, and never reach across to another app's views. This is what keeps the dependency arrows one-directional as the plan requires.

6.3 Example cross-module flow: creating and activating a subscription
This is the flow described in §26 of poc.md, drawn as an actual sequence:

PostgreSQL
NotificationService
DeliveryService
PaymentService
SubscriptionService
DRF API
Admin (React)
PostgreSQL
NotificationService
DeliveryService
PaymentService
SubscriptionService
DRF API
Admin (React)
alt
[fully paid]
POST /api/subscriptions/ {customer_id, plan_id}
create_subscription()
validate customer & plan belong to same business
INSERT Subscription (status=PENDING)
201 Created (PENDING)
POST /api/payments/ {subscription_id, amount}
record_payment()
INSERT Payment
recalculate paid_amount / pending_amount
UPDATE Subscription status=ACTIVE
generate_delivery_schedule(start_date, end_date, meal_type)
bulk INSERT Delivery rows (status=PENDING)
emit SUBSCRIPTION_RENEWED
INSERT Notification
201 Created (payment + updated subscription)
Note the pattern: SubscriptionService never imports DeliveryModel or NotificationModel directly — it calls DeliveryService.generate_delivery_schedule() and NotificationService.emit(). This is the "services talk to services" rule from §27 of the modularization plan.

6.4 Subscription state machine
created, awaiting payment

payment recorded

pause requested

resumed

end_date passed (calculated)

cancelled

cancelled

renewed (new period)

PENDING

ACTIVE

PAUSED

EXPIRED

CANCELLED

EXPIRING is deliberately not a stored state — it's computed at query time (end_date - today <= 3 days AND status = ACTIVE), exactly as the spec calls out. This avoids a scheduled job having to "catch" every subscription at the right moment; it's always correct at read time.

6.5 Backend project layout
backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py          # for future websocket/Channels needs
│   └── wsgi.py
│
├── apps/
│   ├── accounts/         # Auth + User + Staff
│   ├── businesses/       # Business/Tenant
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   ├── dashboard/
│   └── reports/
│
├── common/
│   ├── models.py         # TenantScopedModel, TimeStampedModel
│   ├── viewsets.py        # TenantScopedViewSet
│   ├── permissions.py     # IsSameBusiness, RoleBasedPermission
│   ├── pagination.py
│   ├── exceptions.py      # unified error handler
│   └── constants.py
│
├── celery_app.py
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
└── .env.example
7. Frontend Architecture
7.1 Project structure
src/
├── app/
│   ├── App.tsx
│   ├── routes.tsx          # role-based route trees (Admin / Customer / Staff)
│   └── providers.tsx
│
├── layouts/
│   ├── AdminLayout.tsx
│   ├── CustomerLayout.tsx
│   └── StaffLayout.tsx
│
├── features/                # one folder per domain, mirrors backend apps
│   ├── auth/
│   ├── business/
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   ├── dashboard/
│   └── reports/
│
├── components/ui/           # generic, reusable, no domain knowledge
├── services/apiClient.ts    # single Axios instance
├── store/                   # Zustand — shared state only
├── hooks/
├── utils/
└── types/
Each features/<domain>/ folder is self-contained: <domain>Api.ts, <domain>Types.ts, <domain>Validation.ts, pages/, components/. A feature never imports another feature's internals — if subscriptions needs customer data, it calls customersApi, not customers/components/CustomerForm.

7.2 State management boundaries
Local to feature (React Query / component state)

customer list/detail

subscription list/detail

payment list

delivery list

Zustand (global, shared)

authStore

businessContext

uiPreferences

Per §25 of the modularization plan: Zustand holds only truly cross-cutting state (who's logged in, which business, UI prefs). Domain lists/detail data stay close to the feature that fetches them — recommend TanStack Query on top of Axios for this layer (caching, refetch-on-focus, optimistic updates for actions like "mark delivered"), even though it wasn't named explicitly in poc.md; it solves exactly the "don't dump every API response into Zustand" rule with less hand-rolled code.

7.3 API client
// services/apiClient.ts (shape, not full implementation)
- baseURL from env (VITE_API_BASE_URL)
- request interceptor: attach Authorization: Bearer <access_token>
- response interceptor: on 401 → attempt refresh once → retry original request
                         on refresh failure → clear authStore → redirect to /login
Every features/*/api.ts file imports this one client — no feature creates its own Axios instance.

8. API Architecture
8.1 Conventions
Base path: /api/v1/ (versioned from day one — cheap now, expensive to retrofit).
Resource-based URLs, plural nouns: /api/v1/customers/, /api/v1/subscriptions/{id}/pause/.
Standard verbs: GET/POST/PUT/PATCH/DELETE; state transitions as POST actions (/subscriptions/{id}/pause/, /renew/, /cancel/) rather than overloading PATCH with a status field — keeps business-rule validation (e.g. "can't pause a CANCELLED subscription") in one place per action.
Pagination: DRF PageNumberPagination, consistent envelope:
{
  "count": 142,
  "next": "...",
  "previous": null,
  "results": [ /* items */ ]
}
Filtering: django-filter per viewset (?status=ACTIVE&meal=LUNCH), matching the filter UI described in §19 of poc.md.
Errors: a single DRF exception handler (common/exceptions.py) normalizes all error responses to:
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "fields": { "phone": ["This field is required."] }
  }
}
8.2 Authentication flow
Django API
React App
Browser
Django API
React App
Browser
access token expires (~15 min)
refresh_token expires / logout
enter credentials
POST /api/v1/auth/login/
{ access_token, refresh_token, user, business }
store access_token in memory, refresh_token in httpOnly cookie (preferred) or secure storage
GET /api/v1/auth/me/ (Authorization: Bearer access_token)
profile + role + business_id
POST /api/v1/auth/refresh/ (refresh_token)
new access_token
POST /api/v1/auth/logout/ (blacklist refresh_token)
Access tokens are short-lived (~15 min) and kept in memory only; refresh tokens are longer-lived and, where the deployment allows it, stored in an httpOnly secure cookie rather than localStorage — directly satisfying the spec's security requirement: "No sensitive information in frontend local storage where avoidable."

8.3 Endpoint summary (from poc.md, unchanged — this doc doesn't redefine it)
The full endpoint list is already specified in §17 of poc.md (/customers/, /plans/, /subscriptions/{id}/pause|resume|renew|cancel/, /payments/, /deliveries/today/, /reports/*). This architecture doc's job is the how, not re-listing the what — see that section for the authoritative endpoint list.

9. Data Architecture
9.1 Core entity relationships
employs

has

defines

offers

used in

subscribes

based on

paid via

generates

records

records

receives

BUSINESS

uuid

id

PK

string

name

string

status

USER

uuid

id

PK

uuid

business_id

FK

string

role

bool

is_active

CUSTOMER

uuid

id

PK

uuid

business_id

FK

string

customer_code

string

status

MEAL

uuid

id

PK

uuid

business_id

FK

string

name

bool

is_active

PLAN

uuid

id

PK

uuid

business_id

FK

int

duration_days

decimal

price

int

total_meals

SUBSCRIPTION

uuid

id

PK

uuid

business_id

FK

uuid

customer_id

FK

uuid

plan_id

FK

date

start_date

date

end_date

string

status

decimal

total_amount

decimal

paid_amount

int

remaining_meals

PAYMENT

uuid

id

PK

uuid

subscription_id

FK

decimal

amount

string

payment_method

string

status

DELIVERY

uuid

id

PK

uuid

subscription_id

FK

date

delivery_date

string

meal_type

string

status

MEALSKIP

uuid

id

PK

uuid

subscription_id

FK

date

date

SUBSCRIPTIONPAUSE

uuid

id

PK

uuid

subscription_id

FK

date

start_date

date

end_date

NOTIFICATION

uuid

id

PK

uuid

user_id

FK

string

type

bool

is_read

Field lists match §7–13 of poc.md exactly; this diagram just makes the relationships explicit for schema design and migration planning.

9.2 Indexing priorities (for launch, not exhaustive)
Table	Index	Why
every tenant table	(business_id)	every query filters by tenant first
subscription	(business_id, status, end_date)	expiry queries (§21 poc.md) run constantly
delivery	(business_id, delivery_date, status)	"today's deliveries" is a hot path
customer	(business_id, name), (business_id, phone)	search (§27 poc.md)
payment	(subscription_id)	payment history lookups
9.3 Reports — no separate warehouse for MVP
Per §16 of poc.md, reports query live operational tables directly (via selectors.py), not a duplicated reporting store. If report queries become a performance bottleneck as data grows, the escalation path is: (1) add read replicas, (2) add materialized views for the heaviest aggregates — not a new database.

10. Security Architecture
Request

HTTPS/TLS termination at Nginx

JWT validation

Role-based permission check

Tenant-scoped queryset

Serializer validation + sanitization

Rate limiting - DRF throttling

View/Service logic

Audit log for admin actions

Requirement (from poc.md §36)	Mechanism
JWT authentication	djangorestframework-simplejwt
Password hashing	Django's default (PBKDF2/Argon2) — never rolled by hand
Role-based permissions	DRF permission classes per viewset, mapped to the role table below
Business-level data isolation	TenantScopedViewSet (§5) — enforced backend-side, never trusted from frontend
API validation / input sanitization	DRF serializers + Zod on the frontend (defense in depth, not either/or)
Rate limiting	DRF ScopedRateThrottle on auth + write-heavy endpoints
HTTPS in production	Enforced at Nginx/load balancer
Secure env vars	.env + secrets manager in production, never committed
Audit trail	AuditLog model (poc.md §29), written from services.py on state-changing actions
Role permission matrix (condensed from poc.md §3):

Role	Customers	Plans/Meals	Subscriptions	Payments	Deliveries	Reports	Settings
Owner/Manager	CRUD	CRUD	CRUD	CRUD	CRUD	Read	CRUD
Delivery Staff	Read (assigned only)	–	–	–	Update status + notes	–	–
Kitchen Staff	–	Read (counts)	–	–	Read (counts)	–	–
Customer	Read (self)	Read	Read + skip/pause/renew (self)	Read (self)	Read (self)	–	–
11. Infrastructure & Deployment
11.1 Local development
docker-compose.yml

proxy /api

react - Vite dev server :5173

django - runserver :8000

postgres:15 :5432

redis:7 :6379

One docker-compose.yml, one .env, docker compose up gives a new developer the full stack — matches Phase 1 of poc.md's development phases.

11.2 Production
Internet

Nginx / Load Balancer + TLS

Static React build - CDN or Nginx

Gunicorn + Django - instance 1

Gunicorn + Django - instance 2

Managed PostgreSQL

Managed Redis

Celery Worker

Celery Beat

Object storage: logos, receipts

Django app instances are stateless (JWT means no server-side session store), so horizontal scaling is just "add another Gunicorn instance behind the load balancer" — no sticky sessions needed.

11.3 CI/CD
Feature branch

Pull Request

CI: lint + backend tests + frontend tests

Code review

Merge to develop

Auto-deploy to staging

Manual QA

Merge to main

Deploy to production

Matches the Git branch strategy already defined in §32 of the modularization plan (feature/* → develop → main).

12. Background Jobs (Celery + Redis)
Not explicitly named in poc.md's stack list, but required to implement several features it does specify without blocking the request/response cycle:

Job	Trigger	Why async
Generate next day's delivery records	Celery Beat, nightly	Bulk insert across all active subscriptions — shouldn't block any user request
Mark subscriptions EXPIRED	Celery Beat, nightly (or computed at read-time — see §6.4, either works; scheduled write is only needed if you want EXPIRED to be a real stored state for historical reporting)	Batch operation
Send notifications (in-app now, WhatsApp/SMS/email later)	Triggered by service-layer events	Decouples SubscriptionService from notification delivery mechanics, exactly matching poc.md's notification architecture diagram
Future: Razorpay webhook processing	Webhook receiver → queued job	Webhooks must return fast; processing happens off the request thread
This is the one addition beyond what's explicitly listed in your two source documents — it's the standard way Django implements the "Subscription Module → event → Notification Service" architecture your modularization plan already describes conceptually.

13. Scalability & Evolution Path
Per §40 of the modularization plan: start monolith, extract later, only if needed.

If/when a module outgrows the monolith

Today: Modular Monolith

only if module has independent scaling/team needs

Django app - all modules, one deploy

Core API: Auth, Business, Customers, Subscriptions

Payment Service

Notification Service

Delivery Service

Analytics Service

Because each module already respects the service/selector boundaries in §6.1–6.2, extraction later means moving a Django app to its own deployment and replacing in-process service calls with HTTP/message-queue calls — not a rewrite. Concretely, Notifications and Payments are the two most likely first candidates to split out, since they're the ones most likely to gain heavy external-integration surface area (WhatsApp/SMS providers, Razorpay).

14. Non-Functional Requirements
Category	Target for MVP
Availability	Single-region, single environment acceptable for MVP; multi-instance app servers for basic redundancy
Performance	List/dashboard endpoints < 300ms p95 with proper indexing (§9.2); acceptable given data volumes in §30 of poc.md (dozens–hundreds of records per business at MVP stage)
Logging	Structured JSON logs from Django + Celery; correlate by request_id
Monitoring	Basic APM (e.g. Sentry for errors, simple uptime checks) from day one — cheap now, invaluable once real customers are on it
Testing	Backend: pytest-django covering auth, permissions, tenant isolation, subscription/payment calculations, expiry logic (poc.md §37). Frontend: component + integration tests for forms, protected routes, and the core Rahul-style workflow (poc.md §39)
Backups	Automated daily PostgreSQL backups, tested restore process before first paying customer
15. Summary
Architecture style: modular monolith — one Django app, one React app, one PostgreSQL database, clean internal module boundaries (per §43 of the modularization plan).
Stack validation: Django + DRF + React is well-matched to this specific product (multi-tenant CRUD + reporting), not a generic default — see §2 for the reasoning and alternatives.
What this document adds beyond the two source docs: concrete request-flow diagrams (auth, subscription creation), the tenant-isolation mechanism, the layered service/selector pattern wired into actual request handling, the background-job layer (Celery/Redis) needed to realize the notification/expiry features already specified, and a deployment/scaling path.
Build order stays exactly as defined in poc.md §31 and the modularization plan §30 — this document doesn't change sequencing, only the how of implementation.