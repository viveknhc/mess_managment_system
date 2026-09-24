# 🍱 Mess Management System — System Design (HLD + LLD)

Reference for *how the system actually works internally*: schema, contracts, flows, concurrency rules, failure behavior. Complements the existing docs:

| Doc | Answers |
|---|---|
| `poc.md` | What we're building (features, roles, rules) |
| `mess_management_modularization_plan.md` | Module boundaries & build order |
| `technical_architechture.md` | Stack choice & architecture style |
| `development_plan.md` / `tasks.md` | When & in what order it gets built |
| **`system_design.md` (this doc)** | **How each part works at the design level** |

---

# Part I — High-Level Design

## 1. System Overview

A multi-tenant web application for mess/subscription-food businesses. Three user surfaces (Admin/Staff, Customer, future Kitchen) talk to one Django modular-monolith API over HTTPS/REST, backed by PostgreSQL. Celery + Redis handle scheduled and event-driven work so no user request ever waits on bulk writes or external sends.

```text
┌──────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                            │
│   Admin/Staff SPA        Customer SPA        (mobile browsers)   │
└──────────────┬───────────────────────┬───────────────────────────┘
               │ HTTPS (JWT Bearer)    │
┌──────────────▼───────────────────────▼───────────────────────────┐
│                       EDGE: Nginx (TLS, static)                  │
└──────────────┬───────────────────────────────────────────────────┘
               │ /api/v1/*
┌──────────────▼───────────────────────────────────────────────────┐
│                DJANGO MODULAR MONOLITH (Gunicorn)                │
│  TenantMiddleware → DRF (authn → perms → view → service → ORM)   │
│  apps: accounts · businesses · customers · meals · plans ·       │
│        subscriptions · payments · deliveries · notifications ·   │
│        dashboard · reports · settings · audit                    │
└──────┬───────────────────────┬───────────────────────┬───────────┘
       │                       │                       │
┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼───────────┐
│ PostgreSQL  │         │    Redis    │         │  Celery Worker   │
│ (system of  │         │ broker +    │         │  + Celery Beat   │
│  record)    │         │ cache       │         │  (async jobs)    │
└─────────────┘         └─────────────┘         └──────────────────┘
                                                       │ future
                                        Razorpay · WhatsApp · SMS (outbound only)
```

Key properties:

- **Stateless app tier** — JWT means any Gunicorn instance can serve any request; scale = add instances.
- **One database, schema-per-convention tenancy** — shared tables, every tenant row carries `business_id` (row-level isolation, enforced in code, see §6).
- **Sync for reads/writes, async for side effects** — a payment is recorded synchronously; notification sending and bulk delivery generation happen on Celery.
- **Outbound-only external integrations in MVP** — nothing external can call in (webhook receiver for Razorpay is designed but not built).

## 2. Component Responsibilities

| Component | Owns | Never does |
|---|---|---|
| React SPA (feature modules) | rendering, form validation (Zod), auth token handling | business rules, tenant filtering decisions |
| DRF layer (views/serializers) | HTTP parsing, I/O validation, status codes, throttling | multi-step business logic |
| Service layer (`services.py`) | business operations, transactions, cross-module orchestration, audit writes | raw HTTP concerns |
| Selector layer (`selectors.py`) | complex/aggregate reads | writes |
| PostgreSQL | durability, constraints, indexes | — |
| Redis | Celery broker, short-TTL cache for hot aggregates | system of record |
| Celery worker/beat | nightly delivery generation, expiry sweep, notification dispatch | synchronous request work |

## 3. Tenancy Model (HLD)

Shared-database, shared-schema multi-tenancy:

- Every tenant-owned table has `business_id` FK, indexed as the **leading column** of every composite index.
- Every request resolves `request.user.business_id` → injected by `TenantScopedViewSet.get_queryset()`; object access double-checked by `IsSameBusiness` returning **404** (existence never leaked).
- Cross-tenant writes are structurally impossible through the API: `perform_create()` force-sets `business` server-side; clients cannot POST a business_id.
- `SUPER_ADMIN` (future platform staff) is the only role that can bypass scoping, via an explicit admin-only code path.
- **Guardrail:** a CI lint rule / code-review check that greps for `objects.all()` outside `common/` — tenant filter bypasses fail the build.

Why not schema-per-tenant: dozens–hundreds of records per business at MVP scale (poc §30), single region, single DB; shared-schema is simplest to back up, migrate, and query across (needed for reports later). Escalation path if a tenant needs hard isolation: migrate that tenant to a second DB instance — no code redesign, because all queries already funnel through the tenant base classes.

## 4. The Two Write Pipelines

**Pipeline A — synchronous (user waiting):** Create customer, plan, subscription, payment → validated, written in one ACID transaction, response returns the created/updated resource. Duration target < 300 ms.

**Pipeline B — asynchronous (side effects):** Delivery schedule bulk-generation on activation, nightly next-day generation, nightly expiry sweep + expiring notifications, future provider sends (WhatsApp/SMS/email). Triggered by service-layer events → Celery tasks. **Rule: an HTTP request may enqueue a task but never performs bulk side-effects inline** (exception: the small first delivery batch for "today" is written inline at activation so Today's Deliveries is immediately correct — see §13.3).

## 5. Capacity & Sizing Assumptions (MVP)

| Metric | Assumption |
|---|---|
| Businesses (tenants) | 5–50 at MVP |
| Customers per business | 50–500 |
| Active subscriptions per business | 50–300 |
| Delivery rows | ≈ subs × meals/day × days → ~10k–100k rows/year per business; fine for Postgres with composite indexes |
| Peak request rate | < 50 req/s across all tenants (single small VPS comfortably handles this with Gunicorn ×4) |
| Celery throughput | nightly bulk job: a few thousand inserts per tenant — sub-second per tenant, seconds overall |

No sharding, no partitions, no read replicas needed at MVP. Revisit if any tenant exceeds ~100k delivery rows (then: monthly `BRIN` index on `delivery_date` or partition by month — decided then, §19).

---

# Part II — Low-Level Design

## 6. Tenancy Mechanics (LLD)

```python
# common/models.py
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class TenantScopedModel(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    class Meta:
        abstract = True
```

```python
# common/viewsets.py
class TenantScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSameBusiness]

    def get_queryset(self):
        return self.queryset.filter(business_id=self.request.user.business_id)

    def perform_create(self, serializer):
        serializer.save(business_id=self.request.user.business_id)  # client value ignored
```

```python
# common/permissions.py
class IsSameBusiness(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "SUPER_ADMIN":
            return True
        return obj.business_id == request.user.business_id   # viewset already 404s for foreign rows
```

Rules:
1. `business_id` is **read-only** in every serializer (`fields = (..., read_only)`) — never client-settable.
2. Object-level lookups in views always go through `get_object()` on the filtered queryset — a foreign-ID fetch is a `DoesNotExist` → 404 naturally.
3. Service functions called outside a request (Celery) take `business_id` as an explicit argument — no ambient tenant state in workers.
4. Staff-of-business scoping (delivery staff sees only assigned rows) is an **additional** queryset filter layered on top of the tenant filter, never a replacement.

## 7. Database Schema (LLD)

PostgreSQL, UUID v4 PKs (`id UUID DEFAULT gen_random_uuid()`), `TIMESTAMPTZ` timestamps, `NUMERIC(10,2)` for money (never float), `DATE` for dates. **Money lives on Subscription; Payment rows are the immutable ledger that justifies it** — `pending_amount` is derivable and kept for read speed, recomputed inside the same transaction that records a payment.

```text
businesses            id, name, phone, email, address, logo, status, ts
accounts.User         id, business_id(FK, null for SUPER_ADMIN), name, phone, email,
                      password, role, is_active, ts
customers.Customer    id, business_id, user_id(FK null), customer_code, name, phone, email,
                      address, location, latitude, longitude, notes, status, ts
meals.Meal            id, business_id, name, description, price, is_active, ts
plans.Plan            id, business_id, name, description, duration_days, price,
                      meal_id(FK), total_meals, skip_allowed, pause_allowed, is_active, ts

subscriptions.Subscription
                      id, business_id, customer_id(FK), plan_id(FK),
                      start_date, end_date, status,          -- PENDING|ACTIVE|PAUSED|EXPIRED|CANCELLED
                      total_amount, paid_amount, pending_amount, remaining_meals,
                      renewed_from_id(FK self, null), ts

payments.Payment      id, business_id, customer_id, subscription_id, amount,
                      method, transaction_reference, payment_date, status,   -- PENDING|PAID|FAILED|REFUNDED|PARTIAL
                      notes, ts

deliveries.Delivery   id, business_id, customer_id, subscription_id, delivery_date,
                      meal_type, status,                     -- PENDING|OUT_FOR_DELIVERY|DELIVERED|NOT_DELIVERED|SKIPPED|CANCELLED
                      assigned_staff_id(FK null), delivered_at, notes, ts

deliveries.MealSkip   id, business_id, customer_id, subscription_id, date, meal_type, reason, ts
deliveries.SubscriptionPause
                      id, business_id, subscription_id, start_date, end_date, reason, ts

notifications.Notification
                      id, business_id, user_id, type, title, message, is_read, sent_at, ts

settings.BusinessSettings
                      id, business_id (unique), max_skip_days, min_pause_days, skip_rule,
                      pause_rule, delivery_window, notification_prefs(JSONB), ts

audit.AuditLog        id, business_id, user_id, action, entity_type, entity_id, description, created_at

-- constraints worth stating explicitly:
--   Subscription CHECK (paid_amount >= 0 AND paid_amount <= total_amount + overpay_guard)
--   Subscription CHECK (end_date >= start_date)
--   Customer UNIQUE (business_id, customer_code)
--   Delivery UNIQUE (subscription_id, delivery_date, meal_type)  ← makes schedule generation idempotent
--   Payment CHECK (amount > 0)
```

### Index plan (launch set, from arch. §9.2 plus derived needs)

| Table | Index | Serves |
|---|---|---|
| all tenant tables | `(business_id)` or composite w/ leading business_id | every list endpoint |
| subscription | `(business_id, status, end_date)` | expiry widgets, nightly sweep |
| subscription | `(customer_id)` | customer detail aggregate |
| delivery | `(business_id, delivery_date, status)` | Today's Deliveries (hot path) |
| delivery | `(subscription_id, delivery_date)` | schedule generation idempotency check |
| customer | `(business_id, name)`, `(business_id, phone)` | search |
| payment | `(subscription_id)`, `(business_id, payment_date)` | history + revenue reports |

## 8. Subscription State Machine (LLD)

```text
                 ┌────────── pause ──────────► PAUSED ── resume ──► ACTIVE
                 │                              │
POST /           │                              │ (max pause rule may auto-expire)
subscriptions/   ▼                              ▼
        ┌► PENDING ── full payment ──► ACTIVE ──────────────► EXPIRED
        │   (awaiting       (delivery rows        ▲    ▲            (end_date < today)
        │    payment)        generated)           │    │
        │                                         │    └── cancel ──► CANCELLED (terminal)
        └── cancel ───────────────────────────────┘
```

Transition table (enforced in `services.py`, single `TRANSITIONS` map in `constants.py`; illegal call → `400 INVALID_TRANSITION`):

| From | Allowed → | Trigger / side effects |
|---|---|---|
| PENDING | ACTIVE | payment covers total → generate delivery schedule (inline today-batch + async rest), emit SUBSCRIPTION_RENEWED-style event |
| PENDING | CANCELLED | cancel |
| ACTIVE | PAUSED | pause(date_range) → deliveries in range → CANCELLED (or SKIPPED per rule); if range extends past end_date, extend end_date per settings rule |
| ACTIVE | CANCELLED | cancel — remaining deliveries CANCELLED |
| PAUSED | ACTIVE | resume → un-CANCEL future deliveries back to PENDING |
| ACTIVE | EXPIRED | end_date < today (nightly sweep writes it; reads compute it live — both agree because both use the same predicate) |
| EXPIRED | (none) | terminal; renewal creates a **new** Subscription row with `renewed_from_id` link (history preserved, no in-place mutation) |

**EXPIRING is never stored.** One predicate everywhere (constant, single definition):

```python
EXPIRING_Q = Q(status="ACTIVE", end_date__gte=today, end_date__lte=today + timedelta(days=3))
```

Rationale: a stored flag goes stale (job crashes → wrong badges for days); a computed predicate is always consistent with the data and costs nothing at these volumes.

## 9. Payment State & Reconciliation (LLD)

`Payment.status` semantics per poc §26, applied in `PaymentService.record_payment()` inside one transaction:

```text
record_payment(subscription, amount, method, ref):
    with transaction.atomic():
        p = Payment.objects.create(..., status=PAID)          # MVP: CASH/UPI marked paid on entry
        sub = Subscription.objects.select_for_update().get(id=subscription_id, business_id=...)
        sub.paid_amount += amount
        sub.pending_amount = max(sub.total_amount - sub.paid_amount, 0)
        if   sub.paid_amount == 0:            pass            # PENDING
        elif sub.paid_amount <  total:        pass            # PARTIAL (display state; Payment row carries PARTIAL too)
        else:                                                 # fully paid
            sub.status = "ACTIVE"                             # only legal from PENDING or unpaid ACTIVE
            SubscriptionService.on_fully_paid(sub)            # → delivery schedule + notification event
        sub.save()
        AuditLog.write(action="PAYMENT_RECORDED", ...)
    return sub
```

- **Row lock** (`select_for_update`) on the subscription makes concurrent double-payment safe — the second request waits, then recomputes from committed state.
- Overpayment → rejected by serializer (amount > remaining → 400) at MVP; wallet/credit is future scope.
- Refund: `Payment.status → REFUNDED`, subscription amounts recomputed via reverse of the above; if it drops below fully-paid, subscription does **not** auto-revert status (manual operation; logged in audit) — documented decision, avoids cascading cancellations of delivered meals.

## 10. Delivery Generation (LLD)

Two entry points, one idempotent core:

```python
def generate_delivery_schedule(subscription):                    # called on activation
    dates = each_day(subscription.start_date, subscription.end_date)
    skip_if_in_active_pause_range(...)
    Delivery.objects.bulk_create([
        Delivery(business_id=..., subscription_id=..., customer_id=...,
                 delivery_date=d, meal_type=subscription.plan.meal, status="PENDING")
        for d in dates
    ], ignore_conflicts=True)          # UNIQUE(subscription, date, meal) → re-run safe
```

1. **At activation (Pipeline A + B split):** "today's" rows (if any) insert inline so Today's Deliveries is immediately correct; remaining dates → enqueued task (bulk, off-request).
2. **Nightly Beat job:** for every ACTIVE subscription where `end_date >= tomorrow`, ensure tomorrow's row exists (idempotent by unique constraint). Runs ~00:30; also the retry mechanism — a failed night is corrected by the next run (and by the same run for new activations).
3. **Pause/resume/cancel:** date-range UPDATEs on deliveries inside the same transaction as the subscription transition.

## 11. Expiry Sweep (LLD)

Nightly Beat job, tenant-looped, chunked (`.iterator()`):

```text
for business in businesses:
    expired = Subscription.objects.filter(business=b, status="ACTIVE", end_date__lt=today)
    ids = list(expired.values_list("id", flat=True))
    Subscription.objects.filter(id__in=ids).update(status="EXPIRED")   # bulk, no signals
    emit SUBSCRIPTION_EXPIRED notifications (batch insert)
```

EXPIRING notifications: separate nightly job on the `EXPIRING_Q` predicate → dedupe by checking existing unread notification of same type for same subscription (unique-ish check at query level; acceptable at MVP scale). Retries: Beat jobs are idempotent by design (`update(status=...)` is naturally re-runnable), so Celery's `acks_late + retry` is safe to enable.

## 12. API Contract (canonical examples)

Conventions: base `/api/v1/`, JWT Bearer, pagination envelope `{count, next, previous, results}`, filter params `?status=&customer=&search=&ordering=`, unified error envelope.

```http
POST /api/v1/subscriptions/
{ "customer_id": "…", "plan_id": "…", "start_date": "2026-09-20" }
→ 201 { "id": "…", "status": "PENDING", "total_amount": "2500.00",
        "paid_amount": "0.00", "pending_amount": "2500.00", "remaining_meals": 30, … }

POST /api/v1/payments/
{ "subscription_id": "…", "amount": "2500.00", "method": "UPI", "transaction_reference": "UPI/…" }
→ 201 { "id": "…", "status": "PAID", … }        # subscription now ACTIVE (side effects per §9)

POST /api/v1/subscriptions/{id}/pause/
{ "start_date": "2026-09-25", "end_date": "2026-09-30", "reason": "travel" }
→ 200 { "id": "…", "status": "PAUSED", … }
→ 400 { "error": { "code": "INVALID_TRANSITION",
        "message": "Cannot pause a CANCELLED subscription", "fields": {} } }

PATCH /api/v1/deliveries/{id}/status/
{ "status": "DELIVERED" }                        # staff: assigned rows only
→ 200 { "id": "…", "status": "DELIVERED", "delivered_at": "2026-09-20T13:05:00Z" }

GET /api/v1/reports/dashboard/
→ 200 { "active_customers": 142, "todays_meals": 225, "expiring_today": 4,
        "expiring_this_week": 18, "pending_payments": 11, "todays_revenue": "6250.00", … }
```

Error codes (stable strings): `VALIDATION_ERROR` (422/400), `INVALID_TRANSITION` (400), `AUTH_INVALID` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404), `RATE_LIMITED` (429), `SERVER_ERROR` (500). Frontend keys off `error.code`, displays `error.message`, maps `error.fields` onto form fields.

## 13. Key Sequence Flows

### 13.1 End-to-end activation (the golden path)

```text
Admin UI        API                 SubscriptionService   PaymentService   DeliveryService    NotificationService  Celery
  │ POST /subscriptions/  │                │                    │                │                  │           │
  │──────────────────────►│ create_subscription()               │                │                  │           │
  │ 201 PENDING           │ INSERT sub      │                    │                │                  │           │
  │◄──────────────────────│                 │                    │                │                  │           │
  │ POST /payments/       │───────────────► │ record_payment()   │                │                  │           │
  │                       │  TX: lock sub, ledger row, recalc, set ACTIVE       │                  │           │
  │                       │                 │───────────────────►│ on_fully_paid():                 │           │
  │                       │                 │                    │ generate(today-batch inline)     │           │
  │                       │                 │                    │────────────────────────────────► │ .delay()  │
  │                       │                 │                    │  emit(PAYMENT_RECEIVED)          │ enqueue   │
  │ 201 PAID + sub ACTIVE │                 │                    │────────────────────────────────────────────────► │
  │◄──────────────────────│                 │                    │                                  │  bulk rows│
  │                       │                 │                    │                                  │  notify() │
```

Failure semantics: TX rollback on any inline step → API 500, user retries, nothing half-written. Celery failure after commit → schedule-generation task retries (idempotent `ignore_conflicts`), worst case nightly job fills the gap.

### 13.2 Skip a meal (customer or admin)

```text
POST /api/v1/subscriptions/{id}/skips/  {date, meal_type, reason}
→ service: validate (date >= today, plan.skip_allowed, within max_skip_days setting)
→ TX: MealSkip row + Delivery(status→SKIPPED) for that slot
→ apply business skip_rule (settings): EXTEND → end_date += 1 (remaining_meals unchanged)
                                        | CREDIT   → credit note (MVP: notes field)
                                        | NONE     → no adjustment
→ AuditLog + emit DELIVERY_UPDATE
```

### 13.3 Nightly ops (Beat)

```text
00:30  generate_tomorrows_deliveries()   — idempotent bulk insert per tenant
01:00  sweep_expired_subscriptions()     — bulk flip ACTIVE→EXPIRED, batch notify
01:15  notify_expiring_subscriptions()   — EXPIRING_Q scan, dedupe, batch notify
```

## 14. Caching Strategy

Deliberately minimal at MVP — Postgres is fast at these volumes and cache invalidation bugs cost more than they save:

| Data | Strategy |
|---|---|
| Auth: current user | no cache; 1 indexed query per request, cheap |
| Today's deliveries | no cache (filtered index hit); TanStack Query refetch-on-focus on client |
| Dashboard aggregates | Redis `SETEX dashboard:{business_id} 60` — 60 s TTL, invalidated by write events (payment recorded / delivery status change) from services |
| Report series | client-side cache via TanStack Query (stale 5 min); server re-queries live tables |
| Anything else | no cache |

Rule: **cache only aggregate/read-mostly endpoints, always with short TTL + event invalidation where correctness matters.** Lists stay cacheless.

## 15. Security Design (LLD deltas to arch. §10)

- **Token handling:** access ~15 min in memory only; refresh in httpOnly Secure SameSite=Strict cookie (path=`/api/v1/auth/`), rotation on use, blacklist on logout (simplejwt blacklist app). CSRF protection applies to the refresh endpoint only (cookie path-scoped); all other API calls are Bearer-header → no CSRF surface.
- **Authorization matrix:** enforced twice — viewset-level (`RoleBasedPermission` map, role→allowed actions per app) and object-level (`IsSameBusiness` + staff-assigned filter). Customer role additionally restricted to **self-owned objects only** via `customer.user_id == request.user.id` filter on portal views (PT-01/PT-02 tests).
- **Throttling:** `ScopedRateThrottle` — login `5/min/IP`, refresh `30/min`, writes `60/min/user`, portal reads `120/min/user`.
- **Input handling:** DRF serializers strip unknown fields; Zod mirrors key shapes client-side (defense in depth); `transaction_reference` and notes are sanitized/length-capped; UUIDs as PKs make ID-guessing enumeration useless (and 404s hide existence anyway).
- **Audit:** services (not views) write `AuditLog` for: subscription transitions, payments, delivery status changes, staff changes, settings changes — user, action, entity, timestamp.

## 16. Concurrency & Consistency Rules (summary)

1. Money mutations: `select_for_update()` on Subscription; ledger rows are append-only.
2. State transitions: guarded by `TRANSITIONS` map + row lock; double-pause race → second call gets `INVALID_TRANSITION`.
3. Bulk generation: idempotent via DB unique constraint + `ignore_conflicts`; safe to re-run and to overlap with nightly job.
4. Beat jobs: re-runnable by construction (idempotent updates, dedupe on notifications).
5. Read-your-writes: post-payment UI refetches subscription (TanStack invalidation) — user never sees stale status after a 200.
6. Clock source: single Postgres `now()`/app server time in one region; nightly jobs tolerate a few minutes' skew because predicates use date granularity.

## 17. Failure Modes & Degradation

| Failure | Behavior | Recovery |
|---|---|---|
| Payment TX fails mid-way | full rollback, API 5xx/4xx | user retries; no partial rows |
| Celery worker down | deliveries/notifications delayed | tasks persist in Redis; worker restart drains queue; nightly job backstops |
| Redis down | app still serves requests (no hard dependency in request path — dashboard cache miss = direct DB query); new task enqueue fails → alert | restart Redis; idempotent jobs |
| Postgres down | app degraded (health endpoint fails) | infra-level: managed DB, backups daily, restore runbook (SD-05) |
| Beat job missed | next run self-heals (idempotency) | none needed |
| Duplicate payment submit (double-click) | row lock serializes; second recomputes → second payment recorded against remaining 0 → rejected by overpay guard | user sees clear 400 |

## 18. Observability

- **Logging:** structured JSON (django-structlog): request_id, user_id, business_id on every log line; services log business events (`subscription.activated`, `payment.recorded`) — those double as the audit trail's noisy sibling.
- **Errors:** Sentry (backend + frontend), release-tagged.
- **Metrics (minimal):** p95 latency per endpoint (DRF middleware), Celery queue depth, nightly job duration.
- **Health:** `/api/v1/health/` checks DB + Redis reachability; used by uptime monitor + LB.
- **Alerts:** job didn't run by 02:00; queue age > 5 min; error rate spike.

## 19. Scaling Path (when, not if)

Trigger → action, in order:

1. **List endpoints slow** (>300 ms p95) → verify indexes (§7) → `select_related/prefetch_outline` on serializers → only then consider caching.
2. **Read load** → Postgres read replica; point reports/dashboard selectors at it (selectors make this a one-line connection change).
3. **Delivery table growth** (>1M rows) → monthly partitions or BRIN on `delivery_date`.
4. **Notification/provider volume** → extract `notifications` app to its own worker only (first candidate per arch. §13).
5. **Multi-region / heavy tenants** → reconsider tenancy (per-tenant DB pinning) — code unaffected due to centralized scoping.
6. **Real-time features** (live tracking) → Django Channels on the existing Redis; additive, not a redesign.

## 20. Design Decision Log (ADR-style one-liners)

| # | Decision | Why / trade-off |
|---|---|---|
| D1 | Shared-schema tenancy | simplest ops at MVP scale; centralized scoping keeps escape hatches open |
| D2 | UUID PKs | non-enumerable IDs, safe URL exposure |
| D3 | EXPIRING computed, not stored | always correct; zero sync jobs for a display state |
| D4 | Money as NUMERIC on subscription + append-only Payment ledger | reconciliation, refund trail |
| D5 | Today's delivery batch written inline at activation | correctness of the daily screen immediately; bulk remainder async |
| D6 | UNIQUE(subscription, date, meal) constraint | makes generation idempotent — concurrency safety from the DB, not code |
| D7 | Refresh token httpOnly cookie, path-scoped, CSRF only there | XSS-resistant auth without CSRF complexity elsewhere |
| D8 | Cache only aggregates, 60 s TTL + event invalidation | invalidation bugs cost more than DB time at this scale |
| D9 | Refund never auto-reverts subscription status | avoids cascading mutations of delivered meals; manual + audited |
| D10 | Services emit events; Celery executes | request path stays fast; provider swaps don't touch business logic |
