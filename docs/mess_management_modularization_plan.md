# 🍱 Mess Management System — Modularization & Module Development Plan

## 1. Purpose

This document defines how the Mess Management System should be split into independent modules so that:

- Each feature has a clear responsibility.
- Frontend and backend code remain maintainable.
- Features can be developed independently.
- New features can be added without rewriting existing modules.
- The system can later evolve into a multi-tenant SaaS product.
- Business logic is not tightly coupled to UI components.

The goal is to avoid building one large application where customer, payment, subscription, delivery, and reporting logic are mixed together.

---

# 2. Modular Architecture

The system should follow a **domain-based modular architecture**.

```text
MESS MANAGEMENT SYSTEM
│
├── Authentication
│
├── Business / Tenant
│
├── User & Staff
│
├── Customer
│
├── Meal
│
├── Plan
│
├── Subscription
│
├── Payment
│
├── Delivery
│
├── Notification
│
├── Dashboard
│
├── Reports
│
└── Settings
```

Each module should have:

```text
UI
API
State
Types
Validation
Business Logic
Tests
```

where applicable.

---

# 3. Module Dependency Principle

Avoid circular dependencies.

Recommended dependency direction:

```text
                    ┌───────────────┐
                    │ Authentication│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    Business   │
                    └───────┬───────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
         Customers        Plans          Users
              │             │
              └──────┬──────┘
                     ▼
               Subscriptions
                     │
            ┌────────┴────────┐
            ▼                 ▼
        Payments          Deliveries
            │                 │
            └────────┬────────┘
                     ▼
                Notifications
                     │
                     ▼
                Dashboard
                     │
                     ▼
                  Reports
```

The dependency direction should generally flow from core entities toward business operations.

---

# 4. Core Modules

## Module 01 — Authentication

### Responsibility

Handle identity and login.

### Features

- Login
- Logout
- JWT access token
- Refresh token
- Current user
- Password handling
- Authentication state
- Protected routes

### Frontend

```text
features/auth/
├── pages/
│   └── LoginPage.tsx
├── components/
├── authApi.ts
├── authStore.ts
├── authTypes.ts
├── authValidation.ts
└── index.ts
```

### Backend

```text
apps/accounts/
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── permissions.py
├── services.py
└── tests.py
```

### Depends On

Nothing initially.

---

# 5. Module 02 — Business / Tenant

### Responsibility

Represent each mess business.

### Features

- Create business
- Business profile
- Business status
- Business settings
- Logo
- Contact details
- Address
- Tenant isolation

### Example

```text
Business A
    Customers
    Plans
    Subscriptions

Business B
    Customers
    Plans
    Subscriptions
```

Business A must never access Business B's data.

### Frontend

```text
features/business/
├── pages/
├── components/
├── businessApi.ts
├── businessStore.ts
├── businessTypes.ts
└── index.ts
```

### Backend

```text
apps/businesses/
├── models.py
├── serializers.py
├── views.py
├── permissions.py
├── services.py
└── tests.py
```

### Depends On

- Authentication

---

# 6. Module 03 — Users & Staff

### Responsibility

Manage employees and their roles.

### Roles

```text
OWNER
MANAGER
DELIVERY_STAFF
KITCHEN_STAFF
CUSTOMER
```

### Features

- Add staff
- Edit staff
- Activate/deactivate staff
- Assign role
- Permissions

### Frontend

```text
features/users/
├── pages/
├── components/
├── usersApi.ts
├── usersTypes.ts
└── index.ts
```

### Backend

```text
apps/accounts/
```

The authentication module can own the User model, while the staff UI can remain a separate frontend module.

### Depends On

- Authentication
- Business

---

# 7. Module 04 — Customer

### Responsibility

Manage customer information.

### Features

- Create customer
- Edit customer
- View customer
- Search customer
- Filter customer
- Activate/deactivate customer
- Customer notes
- Customer address
- Customer history

### Customer Profile

```text
Customer
├── Personal Information
├── Address
├── Current Subscription
├── Payment History
├── Delivery History
├── Meal Skip History
└── Pause History
```

### Frontend

```text
features/customers/
├── pages/
│   ├── CustomersPage.tsx
│   └── CustomerDetailsPage.tsx
├── components/
│   ├── CustomerForm.tsx
│   ├── CustomerTable.tsx
│   └── CustomerCard.tsx
├── customersApi.ts
├── customersTypes.ts
├── customersValidation.ts
└── index.ts
```

### Backend

```text
apps/customers/
├── models.py
├── serializers.py
├── views.py
├── filters.py
├── services.py
└── tests.py
```

### Depends On

- Authentication
- Business

---

# 8. Module 05 — Meals

### Responsibility

Define meal types.

### Examples

```text
Breakfast
Lunch
Dinner
Snacks
```

### Features

- Create meal
- Edit meal
- Activate/deactivate meal
- Meal description
- Meal price if required

### Frontend

```text
features/meals/
├── pages/
├── components/
├── mealsApi.ts
├── mealsTypes.ts
└── index.ts
```

### Backend

```text
apps/meals/
```

### Depends On

- Business

---

# 9. Module 06 — Plans

### Responsibility

Manage subscription plans.

### Features

- Create plan
- Edit plan
- Activate/deactivate plan
- Duration
- Price
- Meal type
- Total meals
- Skip configuration
- Pause configuration

### Example

```text
Monthly Lunch

Duration: 30 days
Price: ₹2500
Meal: Lunch
Meals: 30
Skip: Enabled
Pause: Enabled
```

### Frontend

```text
features/plans/
├── pages/
├── components/
├── plansApi.ts
├── plansTypes.ts
├── plansValidation.ts
└── index.ts
```

### Backend

```text
apps/plans/
```

### Depends On

- Business
- Meals

---

# 10. Module 07 — Subscriptions

### Responsibility

Manage the customer's subscription lifecycle.

This is one of the most important business modules.

### Features

- Create subscription
- Activate
- Pause
- Resume
- Renew
- Cancel
- Expire
- Calculate remaining days
- Calculate remaining meals
- Subscription history

### States

```text
PENDING
ACTIVE
PAUSED
EXPIRED
CANCELLED
```

`EXPIRING` should preferably be treated as a calculated UI/reporting state rather than a permanent database state.

### Frontend

```text
features/subscriptions/
├── pages/
│   ├── SubscriptionsPage.tsx
│   └── SubscriptionDetailsPage.tsx
├── components/
│   ├── SubscriptionCard.tsx
│   ├── SubscriptionForm.tsx
│   ├── SubscriptionStatus.tsx
│   └── RenewalDialog.tsx
├── subscriptionsApi.ts
├── subscriptionsTypes.ts
├── subscriptionsValidation.ts
├── subscriptionsUtils.ts
└── index.ts
```

### Backend

```text
apps/subscriptions/
├── models.py
├── serializers.py
├── views.py
├── services.py
├── selectors.py
├── permissions.py
└── tests.py
```

### Depends On

- Customer
- Plan
- Business

---

# 11. Module 08 — Payments

### Responsibility

Track money received from customers.

### Features

- Record payment
- Payment history
- Pending amount
- Partial payment
- Payment status
- Payment method
- Transaction reference
- Refund status

### Payment Methods

```text
CASH
UPI
BANK_TRANSFER
CARD
ONLINE
OTHER
```

### Frontend

```text
features/payments/
├── pages/
├── components/
├── paymentsApi.ts
├── paymentsTypes.ts
├── paymentsValidation.ts
└── index.ts
```

### Backend

```text
apps/payments/
├── models.py
├── serializers.py
├── views.py
├── services.py
├── selectors.py
└── tests.py
```

### Depends On

- Customer
- Subscription
- Business

---

# 12. Module 09 — Deliveries

### Responsibility

Manage daily meal delivery.

### Features

- Generate daily delivery list
- View today's deliveries
- Assign delivery staff
- Mark delivered
- Mark not delivered
- Mark skipped
- Add delivery notes
- Delivery history

### Delivery Status

```text
PENDING
OUT_FOR_DELIVERY
DELIVERED
NOT_DELIVERED
SKIPPED
CANCELLED
```

### Frontend

```text
features/deliveries/
├── pages/
│   ├── TodayDeliveriesPage.tsx
│   └── DeliveryHistoryPage.tsx
├── components/
│   ├── DeliveryTable.tsx
│   ├── DeliveryCard.tsx
│   └── DeliveryStatus.tsx
├── deliveriesApi.ts
├── deliveriesTypes.ts
└── index.ts
```

### Backend

```text
apps/deliveries/
├── models.py
├── serializers.py
├── views.py
├── services.py
├── selectors.py
└── tests.py
```

### Depends On

- Customer
- Subscription
- Meal
- Business
- Staff

---

# 13. Module 10 — Meal Skip & Pause

This can initially be part of the Subscription module.

Later, if the business logic becomes complex, split it into its own module.

### Features

```text
Skip Meal
Pause Subscription
Resume Subscription
Meal Credit
Subscription Extension
```

### Important Business Rule

Different businesses may have different rules.

For example:

```text
Business A:
Skipped meal → Extend subscription

Business B:
Skipped meal → Meal credit

Business C:
Skipped meal → No adjustment
```

Therefore, avoid hard-coding one universal rule.

Use configurable business settings.

---

# 14. Module 11 — Notifications

### Responsibility

Notify customers, staff, and admins.

### Notification Types

```text
SUBSCRIPTION_EXPIRING
SUBSCRIPTION_EXPIRED
PAYMENT_RECEIVED
PAYMENT_PENDING
DELIVERY_UPDATE
SUBSCRIPTION_RENEWED
```

### Channels

Initial:

```text
IN_APP
```

Future:

```text
WHATSAPP
SMS
EMAIL
PUSH
```

### Architecture

```text
Subscription Module
       │
       │ event
       ▼
Notification Service
       │
       ├── In-App
       ├── WhatsApp
       ├── SMS
       └── Email
```

The subscription module should not directly depend on a WhatsApp provider.

---

# 15. Module 12 — Dashboard

### Responsibility

Aggregate information from other modules.

The dashboard should **not own the underlying business data**.

Example:

```text
Dashboard
   │
   ├── Customers → Active count
   ├── Subscriptions → Expiring count
   ├── Payments → Pending amount
   ├── Deliveries → Today's delivery count
   └── Meals → Today's meal count
```

### Frontend

```text
features/dashboard/
├── pages/
│   └── DashboardPage.tsx
├── components/
│   ├── StatCard.tsx
│   ├── ExpiryWidget.tsx
│   ├── DeliveryWidget.tsx
│   ├── PaymentWidget.tsx
│   └── MealSummaryWidget.tsx
├── dashboardApi.ts
├── dashboardTypes.ts
└── index.ts
```

### Backend

```text
apps/reports/
or
apps/dashboard/
```

For the MVP, a `dashboard` API can aggregate data from domain services.

---

# 16. Module 13 — Reports

### Responsibility

Read-only business analytics.

### Reports

```text
Customer Report
Subscription Report
Revenue Report
Payment Report
Delivery Report
Meal Report
```

### Important Rule

Reports should query existing business data.

Do not duplicate customer/payment/subscription data inside a separate report database for the MVP.

---

# 17. Module 14 — Settings

### Responsibility

Business configuration.

### Settings

```text
Business Profile
Meal Settings
Subscription Rules
Skip Rules
Pause Rules
Notification Preferences
Payment Settings
Staff Settings
```

Example:

```text
Maximum skip days
Minimum pause duration
Subscription extension rule
Delivery time window
```

---

# 18. Frontend Modular Structure

Recommended final structure:

```text
src/
│
├── app/
│   ├── App.tsx
│   ├── routes.tsx
│   └── providers.tsx
│
├── components/
│   └── ui/
│
├── layouts/
│   ├── AdminLayout.tsx
│   ├── CustomerLayout.tsx
│   └── StaffLayout.tsx
│
├── features/
│   │
│   ├── auth/
│   ├── business/
│   ├── users/
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   ├── dashboard/
│   ├── reports/
│   └── settings/
│
├── services/
│   └── apiClient.ts
│
├── store/
│   ├── authStore.ts
│   └── appStore.ts
│
├── hooks/
├── utils/
├── types/
└── assets/
```

---

# 19. Frontend Module Internal Pattern

Each domain module should follow a consistent pattern.

Example:

```text
features/customers/

├── pages/
│   ├── CustomersPage.tsx
│   └── CustomerDetailsPage.tsx
│
├── components/
│   ├── CustomerForm.tsx
│   ├── CustomerTable.tsx
│   └── CustomerStatusBadge.tsx
│
├── customersApi.ts
├── customersTypes.ts
├── customersValidation.ts
├── customersUtils.ts
└── index.ts
```

Do not put customer-specific logic into generic global files.

---

# 20. Backend Modular Structure

```text
backend/
│
├── config/
│   ├── settings/
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   │
│   ├── accounts/
│   ├── businesses/
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   ├── dashboard/
│   ├── reports/
│   └── settings/
│
├── common/
│   ├── exceptions/
│   ├── pagination/
│   ├── permissions/
│   ├── utilities/
│   └── constants/
│
├── manage.py
└── requirements.txt
```

---

# 21. Backend Module Pattern

Each module:

```text
subscriptions/

├── migrations/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── services.py
├── selectors.py
├── permissions.py
├── constants.py
└── tests/
```

### Responsibility

`models.py`

Database structure.

`serializers.py`

Input/output validation.

`views.py`

HTTP/API handling.

`services.py`

Business operations.

`selectors.py`

Complex read/query operations.

`permissions.py`

Authorization.

`tests/`

Module-specific tests.

---

# 22. Service Layer

Important business operations should be handled by services.

Bad:

```text
View
 ├── Validate payment
 ├── Update subscription
 ├── Calculate remaining meals
 ├── Generate delivery
 ├── Send notification
 └── Save everything
```

Better:

```text
View
  ↓
SubscriptionService
  ↓
PaymentService
  ↓
DeliveryService
  ↓
NotificationService
```

Example:

```text
SubscriptionService.renew_subscription()
```

could:

```text
1. Validate customer
2. Validate plan
3. Calculate new dates
4. Create subscription period
5. Update payment information
6. Generate required delivery records
7. Trigger notification
```

---

# 23. Selectors / Query Layer

Keep complicated read queries separate.

Example:

```text
SubscriptionSelector.get_expiring_subscriptions()

CustomerSelector.get_active_customers()

DeliverySelector.get_today_deliveries()

PaymentSelector.get_pending_payments()
```

This prevents large query logic from accumulating inside views.

---

# 24. Shared Components vs Module Components

## Shared

Use global components for generic UI:

```text
Button
Input
Modal
Dialog
Table
Pagination
Dropdown
Badge
DatePicker
Loader
EmptyState
Toast
```

Location:

```text
components/ui/
```

## Module-specific

Customer-specific:

```text
CustomerStatusBadge
CustomerForm
CustomerTable
```

Subscription-specific:

```text
SubscriptionStatus
SubscriptionCard
RenewalDialog
```

Do not make every component global.

---

# 25. State Management Strategy

Use Zustand only for **shared application state**.

Good Zustand use cases:

```text
Authentication
Current User
Business Context
Global Notifications
UI Preferences
```

Avoid putting every API response into Zustand.

For example:

```text
Customer list
Subscription list
Payment list
Delivery list
```

should preferably remain local to their respective feature/data-fetching layer.

---

# 26. API Client

Create one common API client.

```text
services/apiClient.ts
```

Responsibilities:

```text
Base URL
Authentication headers
Token refresh
Error handling
Request configuration
```

Domain modules use it:

```text
customersApi.ts
subscriptionsApi.ts
paymentsApi.ts
deliveriesApi.ts
```

---

# 27. Cross-Module Communication

Modules should communicate through clearly defined services/events.

Example:

```text
Customer Created
       ↓
Customer Module

Subscription Created
       ↓
Subscription Module
       │
       ├── Payment
       ├── Delivery
       └── Notification
```

Avoid directly modifying another module's database models from unrelated code.

---

# 28. Domain Ownership

Each piece of data should have one owner.

```text
Customer data
→ Customer module

Plan data
→ Plan module

Subscription data
→ Subscription module

Payment data
→ Payment module

Delivery data
→ Delivery module

Notification data
→ Notification module
```

Other modules can read required information through services/selectors/API contracts.

---

# 29. Module Dependency Matrix

| Module | Depends On |
|---|---|
| Authentication | None |
| Business | Authentication |
| Users | Authentication, Business |
| Customers | Authentication, Business |
| Meals | Business |
| Plans | Business, Meals |
| Subscriptions | Customer, Plan, Business |
| Payments | Customer, Subscription, Business |
| Deliveries | Customer, Subscription, Meal, Staff |
| Notifications | User, Business |
| Dashboard | Customers, Subscriptions, Payments, Deliveries |
| Reports | Customers, Subscriptions, Payments, Deliveries |
| Settings | Business |

Keep dependencies one-directional where possible.

---

# 30. Development Order

Do not develop modules randomly.

Recommended order:

```text
PHASE 1
Authentication
       ↓
Business
       ↓
Users
```

```text
PHASE 2
Customers
       ↓
Meals
       ↓
Plans
```

```text
PHASE 3
Subscriptions
       ↓
Payments
```

```text
PHASE 4
Deliveries
       ↓
Meal Skip / Pause
```

```text
PHASE 5
Dashboard
       ↓
Notifications
       ↓
Reports
```

```text
PHASE 6
Customer Portal
       ↓
Advanced Settings
```

---

# 31. Development Strategy Per Module

Every module should follow the same cycle.

```text
1. Define requirement
       ↓
2. Define database model
       ↓
3. Define API contract
       ↓
4. Implement backend
       ↓
5. Write backend tests
       ↓
6. Implement frontend API layer
       ↓
7. Implement UI
       ↓
8. Connect UI + API
       ↓
9. Test complete workflow
       ↓
10. Refactor
       ↓
11. Commit
```

---

# 32. Git Branch Strategy

Use feature-based branches.

```text
main
│
├── develop
│
├── feature/auth
├── feature/customers
├── feature/plans
├── feature/subscriptions
├── feature/payments
├── feature/deliveries
└── feature/dashboard
```

Example:

```text
feature/customer-management
```

After completion:

```text
feature/customer-management
            ↓
          PR
            ↓
         develop
            ↓
          main
```

---

# 33. Module Definition of Done

A module is not complete when its UI is finished.

It is complete when:

```text
✓ Database model completed
✓ API completed
✓ Validation completed
✓ Permissions completed
✓ Frontend UI completed
✓ Loading states completed
✓ Error states completed
✓ Empty states completed
✓ Tests completed
✓ API integrated
✓ Responsive UI verified
✓ Module documentation updated
```

---

# 34. MVP Module Scope

## Must Build

```text
Authentication
Business
Customers
Meals
Plans
Subscriptions
Payments
Deliveries
Dashboard
```

## Build After Core MVP

```text
Notifications
Reports
Customer Portal
Staff Management
Pause / Skip enhancements
Settings
```

## Future Modules

```text
Online Payments
WhatsApp
SMS
GPS
Route Optimization
Inventory
Expenses
GST
Multi-Branch
AI Analytics
Mobile Application
```

---

# 35. Suggested First Sprint

Build only:

```text
AUTH
BUSINESS
CUSTOMER
PLAN
SUBSCRIPTION
```

Expected workflow:

```text
Admin Login
    ↓
Business Dashboard
    ↓
Create Customer
    ↓
Create Plan
    ↓
Create Subscription
    ↓
View Active Subscription
```

Do not start payment or delivery until this flow is stable.

---

# 36. Suggested Second Sprint

```text
PAYMENTS
DELIVERIES
```

Workflow:

```text
Subscription
    ↓
Payment
    ↓
Today's Delivery
    ↓
Mark Delivered
```

---

# 37. Suggested Third Sprint

```text
DASHBOARD
EXPIRY TRACKING
REPORTS
NOTIFICATIONS
```

Workflow:

```text
System Data
     ↓
Dashboard
     ├── Active Customers
     ├── Expiring Subscriptions
     ├── Pending Payments
     ├── Today's Deliveries
     └── Today's Meal Count
```

---

# 38. Customer Portal Module

Keep the customer portal as a separate frontend experience while reusing the same domain modules/API.

```text
Customer Portal
│
├── Dashboard
├── Subscription
├── Meals
├── Payments
├── Deliveries
└── Profile
```

The customer should not receive admin APIs or admin permissions.

---

# 39. SaaS Expansion

When moving from POC to SaaS:

```text
Platform
│
├── Business A
│   ├── Admin
│   ├── Staff
│   └── Customers
│
├── Business B
│   ├── Admin
│   ├── Staff
│   └── Customers
│
└── Business C
    ├── Admin
    ├── Staff
    └── Customers
```

Every request should resolve:

```text
Authenticated User
       ↓
Business / Tenant
       ↓
Allowed Resource
```

Never rely only on frontend filtering for tenant isolation.

---

# 40. Future Microservice Consideration

Do NOT start with microservices.

Start with a modular monolith:

```text
                Django
                  │
       ┌──────────┼──────────┐
       │          │          │
 Customers   Subscriptions Payments
       │          │          │
       └──────────┼──────────┘
                  │
              PostgreSQL
```

If the product grows significantly, selected modules can later become independent services.

Possible future separation:

```text
Core API
   │
   ├── Payment Service
   ├── Notification Service
   ├── Delivery Service
   └── Analytics Service
```

But the POC should remain one backend application.

---

# 41. Important Modularization Rules

### Rule 1

Do not create a separate module for every tiny component.

### Rule 2

Modules should represent business domains, not just UI screens.

### Rule 3

Do not duplicate business logic between frontend and backend.

### Rule 4

Backend remains the source of truth for business rules.

### Rule 5

Keep API communication inside feature modules.

### Rule 6

Keep reusable UI components generic.

### Rule 7

Avoid circular module dependencies.

### Rule 8

Use services for complex business operations.

### Rule 9

Use selectors for complex read queries.

### Rule 10

Keep tenant/business isolation at the backend level.

---

# 42. Final Target Architecture

```text
                         MESS PLATFORM
                              │
                ┌─────────────┴─────────────┐
                │                           │
           ADMIN PORTAL               CUSTOMER PORTAL
                │                           │
                └─────────────┬─────────────┘
                              │
                         REST API
                              │
                       DJANGO MODULAR
                         MONOLITH
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        │          │          │          │          │
     Customer     Plans   Subscription Payment   Delivery
        │          │          │          │          │
        └──────────┴──────────┼──────────┴──────────┘
                              │
                         PostgreSQL
                              │
                  ┌───────────┴───────────┐
                  │                       │
             Notifications            Reports
```

---

# 43. Golden Rule for This Project

Build the application as:

```text
MODULAR MONOLITH
```

not:

```text
ONE GIANT FRONTEND
+
ONE GIANT BACKEND
```

and not:

```text
10 MICROservices
```

The ideal first architecture is:

```text
One React Application
        +
One Django Application
        +
One PostgreSQL Database
        +
Clearly separated business modules
```

This gives the project enough structure to scale while keeping the initial development simple.
