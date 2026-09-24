# 🍱 Mess Management System — Development Specification

## 1. Project Overview

A web-based SaaS-ready management system for mess/home-food businesses to replace manual notebooks, WhatsApp messages, and spreadsheets.

The first version (MVP/POC) focuses on:

- Customer management
- Meal plans
- Subscription management
- Payment tracking
- Daily food delivery tracking
- Subscription expiry monitoring
- Basic dashboard and reports
- Customer portal

The system should be designed so that multiple mess businesses can be supported later.

---

# 2. Product Goals

## Primary Goal

Digitize the day-to-day operations of a mess business.

## Problems to Solve

- Customer information stored in notebooks
- No reliable subscription tracking
- Difficult to identify expiring subscriptions
- Manual payment tracking
- No centralized delivery list
- Difficulty tracking skipped/paused meals
- No clear view of active/inactive customers
- Difficult to generate business reports

---

# 3. User Roles

## 3.1 Super Admin

For future SaaS version.

Permissions:

- Manage mess businesses
- Manage platform users
- View platform-level statistics
- Activate/deactivate businesses

## 3.2 Mess Owner / Admin

Main business user.

Permissions:

- Dashboard
- Customers
- Plans
- Subscriptions
- Payments
- Deliveries
- Reports
- Staff management
- Business settings

## 3.3 Delivery Staff

Permissions:

- View assigned deliveries
- View customer delivery information
- Mark delivered
- Mark failed/not delivered
- Add delivery notes

## 3.4 Kitchen Staff

Permissions:

- View today's meal requirements
- View meal counts
- View meal categories

## 3.5 Customer

Permissions:

- View profile
- View subscription
- View payment history
- View delivery history
- Skip meal
- Request pause
- Renew subscription

---

# 4. Recommended Technology Stack

## Frontend

- React.js
- TypeScript
- Vite
- Tailwind CSS
- Zustand
- React Router
- Axios
- React Hook Form
- Zod
- Recharts

## Backend

- Python
- Django
- Django REST Framework
- JWT Authentication

## Database

- PostgreSQL

## Development

- Git
- GitHub
- Docker
- Docker Compose
- Environment variables

## Future Integrations

- Razorpay
- WhatsApp API
- SMS provider
- Email
- Google Maps
- Push notifications

---

# 5. High-Level Architecture

```text
                    ┌───────────────────┐
                    │     React App     │
                    │ TypeScript + Vite │
                    └─────────┬─────────┘
                              │
                           REST API
                              │
                    ┌─────────▼─────────┐
                    │ Django REST API   │
                    │ Authentication     │
                    │ Business Logic     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   PostgreSQL      │
                    └───────────────────┘
```

Future:

```text
                    React Web
                       │
             ┌─────────┴─────────┐
             │                   │
        Admin Portal        Customer Portal
             │                   │
             └─────────┬─────────┘
                       │
                 Django API
                       │
       ┌───────────────┼────────────────┐
       │               │                │
 PostgreSQL        Payments       Notifications
                                    │
                              WhatsApp / SMS
```

---

# 6. Multi-Tenant Design

The system should be SaaS-ready from the beginning.

Every business-related record should be associated with a `Business`.

Example:

```text
Business
   │
   ├── Users
   ├── Customers
   ├── Plans
   ├── Subscriptions
   ├── Payments
   └── Deliveries
```

A user belonging to Business A must never be able to access Business B data.

---

# 7. Core Database Models

## 7.1 Business

```text
Business
--------
id
name
phone
email
address
logo
status
created_at
updated_at
```

Status:

```text
ACTIVE
INACTIVE
SUSPENDED
```

---

## 7.2 User

```text
User
----
id
business_id
name
phone
email
password
role
is_active
created_at
updated_at
```

Roles:

```text
SUPER_ADMIN
OWNER
MANAGER
DELIVERY_STAFF
KITCHEN_STAFF
CUSTOMER
```

---

## 7.3 Customer

```text
Customer
--------
id
business_id
user_id
customer_code
name
phone
email
address
location
latitude
longitude
notes
status
created_at
updated_at
```

Status:

```text
ACTIVE
INACTIVE
BLOCKED
```

---

## 7.4 Meal

```text
Meal
----
id
business_id
name
description
price
is_active
created_at
updated_at
```

Examples:

```text
Breakfast
Lunch
Dinner
Snacks
```

---

## 7.5 Plan

```text
Plan
----
id
business_id
name
description
duration_days
price
meal_type
total_meals
skip_allowed
pause_allowed
is_active
created_at
updated_at
```

Example:

```text
Monthly Lunch

Duration: 30 days
Price: ₹2500
Meal: Lunch
Meals: 30
Skip: Yes
Pause: Yes
```

---

# 8. Subscription Model

```text
Subscription
------------
id
business_id
customer_id
plan_id

start_date
end_date

status

total_amount
paid_amount
pending_amount

remaining_meals

created_at
updated_at
```

Status:

```text
ACTIVE
EXPIRING
EXPIRED
PAUSED
CANCELLED
```

Important:

`EXPIRING` can also be calculated dynamically instead of permanently stored.

Example:

```text
end_date - current_date <= 3 days
```

---

# 9. Payment Model

```text
Payment
-------
id
business_id
customer_id
subscription_id

amount
payment_method
transaction_reference

payment_date
status

notes
created_at
updated_at
```

Payment methods:

```text
CASH
UPI
BANK_TRANSFER
CARD
ONLINE
OTHER
```

Status:

```text
PENDING
PAID
FAILED
REFUNDED
PARTIAL
```

---

# 10. Delivery Model

```text
Delivery
--------
id
business_id
customer_id
subscription_id

delivery_date
meal_type

status

assigned_staff
delivered_at

notes
created_at
updated_at
```

Status:

```text
PENDING
OUT_FOR_DELIVERY
DELIVERED
NOT_DELIVERED
SKIPPED
CANCELLED
```

---

# 11. Skip Meal Model

```text
MealSkip
--------
id
business_id
customer_id
subscription_id

date
meal_type
reason

created_at
```

Example:

```text
Customer: Rahul
Date: 18 Sep
Meal: Lunch
Reason: Going home
```

---

# 12. Subscription Pause Model

```text
SubscriptionPause
-----------------
id
business_id
customer_id
subscription_id

start_date
end_date

reason

created_at
```

Business configuration should determine whether paused days:

- Extend subscription
- Become meal credits
- Are ignored

---

# 13. Notification Model

```text
Notification
------------
id
business_id
user_id

type
title
message

is_read
sent_at

created_at
```

Notification types:

```text
SUBSCRIPTION_EXPIRING
PAYMENT_PENDING
PAYMENT_RECEIVED
DELIVERY_UPDATE
SUBSCRIPTION_RENEWED
```

---

# 14. Frontend Application Structure

Recommended:

```text
src/
│
├── assets/
│
├── components/
│   ├── ui/
│   ├── forms/
│   ├── tables/
│   ├── cards/
│   └── layout/
│
├── pages/
│   ├── auth/
│   ├── dashboard/
│   ├── customers/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── reports/
│   └── settings/
│
├── features/
│   ├── customers/
│   ├── subscriptions/
│   ├── payments/
│   └── deliveries/
│
├── store/
│   ├── authStore.ts
│   ├── businessStore.ts
│   └── notificationStore.ts
│
├── services/
│   ├── api.ts
│   ├── authApi.ts
│   ├── customerApi.ts
│   ├── subscriptionApi.ts
│   ├── paymentApi.ts
│   └── deliveryApi.ts
│
├── hooks/
├── utils/
├── types/
├── routes/
└── App.tsx
```

---

# 15. Backend Structure

Recommended Django structure:

```text
backend/
│
├── config/
│
├── apps/
│   ├── accounts/
│   ├── businesses/
│   ├── customers/
│   ├── meals/
│   ├── plans/
│   ├── subscriptions/
│   ├── payments/
│   ├── deliveries/
│   ├── notifications/
│   └── reports/
│
├── requirements.txt
├── manage.py
└── .env
```

Each app should contain:

```text
models.py
serializers.py
views.py
urls.py
permissions.py
services.py
tests.py
```

Keep business logic in services rather than putting everything inside views.

---

# 16. Authentication

Use JWT authentication.

Flow:

```text
Login
  ↓
POST /api/auth/login/
  ↓
Access Token
Refresh Token
  ↓
React stores authentication state
  ↓
API requests use Access Token
```

Required endpoints:

```text
POST /api/auth/login/
POST /api/auth/refresh/
POST /api/auth/logout/
GET  /api/auth/me/
```

---

# 17. API Design

Base:

```text
/api/
```

## Customers

```text
GET    /customers/
POST   /customers/
GET    /customers/{id}/
PUT    /customers/{id}/
PATCH  /customers/{id}/
DELETE /customers/{id}/
```

## Plans

```text
GET    /plans/
POST   /plans/
GET    /plans/{id}/
PUT    /plans/{id}/
PATCH  /plans/{id}/
DELETE /plans/{id}/
```

## Subscriptions

```text
GET    /subscriptions/
POST   /subscriptions/
GET    /subscriptions/{id}/
PATCH  /subscriptions/{id}/
POST   /subscriptions/{id}/pause/
POST   /subscriptions/{id}/resume/
POST   /subscriptions/{id}/renew/
POST   /subscriptions/{id}/cancel/
```

## Payments

```text
GET  /payments/
POST /payments/
GET  /payments/{id}/
```

## Deliveries

```text
GET   /deliveries/
GET   /deliveries/today/
PATCH /deliveries/{id}/status/
```

## Reports

```text
GET /reports/dashboard/
GET /reports/revenue/
GET /reports/customers/
GET /reports/subscriptions/
GET /reports/meals/
```

---

# 18. Dashboard Requirements

Dashboard should show:

```text
Active Customers
New Customers
Today's Meals
Today's Deliveries
Expiring Today
Expiring This Week
Pending Payments
Today's Revenue
```

Example:

```text
┌─────────────────────────────────────┐
│ Active Customers        142         │
│ Today's Meals           225         │
│ Expiring Soon            18         │
│ Pending Payments         11         │
└─────────────────────────────────────┘
```

---

# 19. Customer Management

Customer list should support:

- Search
- Filter
- Sort
- Pagination
- Status filter
- Active subscription filter
- Location filter
- Meal filter

Example filters:

```text
Status:
[All] [Active] [Inactive]

Subscription:
[Active] [Expiring] [Expired] [Paused]

Meal:
[Breakfast] [Lunch] [Dinner]
```

Customer details page:

```text
Customer Information
Subscription
Payment History
Delivery History
Skip History
Pause History
Notes
```

---

# 20. Subscription Management

Admin should be able to:

1. Create subscription
2. Activate subscription
3. Pause subscription
4. Resume subscription
5. Renew subscription
6. Cancel subscription
7. View expiry date
8. View remaining meals
9. View payment status

Subscription card:

```text
Rahul

Monthly Lunch

01 Sep → 30 Sep

🟢 ACTIVE

13 days remaining

₹2500
₹2500 PAID
```

---

# 21. Expiry Monitoring

Dashboard sections:

```text
Expiring Today
Expiring Tomorrow
Expiring in 3 Days
Expiring This Week
Expired
```

The backend should calculate these based on the current date.

Example query:

```text
end_date >= today
AND
end_date <= today + 3 days
AND
status = ACTIVE
```

---

# 22. Daily Delivery

Route:

```text
/deliveries/today
```

Display:

```text
Customer
Phone
Address
Meal
Delivery Time
Status
Assigned Staff
```

Actions:

```text
Mark Delivered
Mark Not Delivered
Mark Skipped
Add Note
```

---

# 23. Meal Preparation Dashboard

For kitchen staff:

```text
Today's Meal Requirements

Breakfast     45
Lunch        127
Dinner        98

Vegetarian    31
Non-Veg       96
```

This should be calculated from active subscriptions and today's delivery records.

---

# 24. Payment Dashboard

Show:

```text
Today's Collection
This Month
Pending
Partial
Failed
Refunded
```

Customer payment history:

```text
Date
Amount
Method
Reference
Status
```

---

# 25. Customer Portal

Customer dashboard:

```text
Hello Rahul 👋

Current Plan
Monthly Lunch

Subscription
01 Sep → 30 Sep

13 days remaining

Today's Meal
Lunch
Status: Delivered

[Skip Meal]
[Pause Subscription]
[Renew]
```

Customer can:

- View subscription
- View payments
- View deliveries
- Skip meal
- Request pause
- Renew
- Update profile

---

# 26. Business Rules

## Subscription Activation

When a subscription is created:

```text
Customer
   ↓
Plan selected
   ↓
Payment recorded
   ↓
Subscription activated
   ↓
Delivery records generated
```

---

## Expiry

When:

```text
current_date > end_date
```

Subscription becomes:

```text
EXPIRED
```

---

## Expiring

If:

```text
0 < days_remaining <= 3
```

Display:

```text
EXPIRING SOON
```

---

## Payment

```text
paid_amount = total_amount
```

→ PAID

```text
paid_amount = 0
```

→ PENDING

```text
0 < paid_amount < total_amount
```

→ PARTIAL

---

# 27. Search & Filtering

Search should support:

```text
Customer Name
Phone
Customer ID
Address
```

Example:

```text
Search: Rahul
```

Result:

```text
Rahul
Rahul Kumar
Rahul P
```

---

# 28. Reports

## Customer Report

```text
Total
Active
Inactive
New
Cancelled
Paused
```

## Subscription Report

```text
Active
Expiring
Expired
Renewed
Cancelled
```

## Revenue Report

```text
Daily
Weekly
Monthly
Pending
```

## Meal Report

```text
Breakfast
Lunch
Dinner
Skipped
Delivered
Not Delivered
```

Charts can be added using Recharts.

---

# 29. Audit Trail

Important administrative actions should eventually be logged.

```text
AuditLog
--------
id
business_id
user_id
action
entity_type
entity_id
description
created_at
```

Example:

```text
17 Sep 2026
Admin created subscription for Rahul.

17 Sep 2026
Staff marked Lunch as Delivered.
```

This becomes useful when multiple employees operate the system.

---

# 30. POC Data

Create seed/demo data:

```text
1 Business

3 Staff

20 Customers

5 Plans

20+ Subscriptions

50+ Payments

100+ Deliveries
```

Include different statuses:

```text
Active
Expiring
Expired
Paused
Pending Payment
Partial Payment
Skipped
Not Delivered
```

This will make the POC realistic.

---

# 31. Development Phases

## Phase 1 — Project Setup

- Create Git repository
- Create React/Vite application
- Create Django application
- Configure PostgreSQL
- Configure environment variables
- Configure CORS
- Configure JWT
- Create base layout

---

## Phase 2 — Authentication

- Login
- Logout
- Token refresh
- Current user
- Role-based routing
- Protected routes

---

## Phase 3 — Business & Users

- Business model
- User roles
- Staff management
- Permissions

---

## Phase 4 — Customers

- Customer CRUD
- Customer search
- Customer filters
- Customer details
- Customer status

---

## Phase 5 — Plans & Meals

- Meal CRUD
- Plan CRUD
- Plan configuration
- Active/inactive plans

---

## Phase 6 — Subscriptions

- Create subscription
- Activate
- Pause
- Resume
- Renew
- Cancel
- Expiry calculation
- Remaining meals

---

## Phase 7 — Payments

- Record payment
- Payment history
- Pending payments
- Partial payments
- Payment summary

---

## Phase 8 — Deliveries

- Generate daily deliveries
- Today's delivery list
- Delivery status
- Skip meal
- Delivery notes

---

## Phase 9 — Dashboard

- KPI cards
- Expiring subscriptions
- Today's meals
- Pending payments
- Delivery statistics
- Revenue summary

---

## Phase 10 — Reports

- Customer reports
- Subscription reports
- Revenue reports
- Meal reports

---

## Phase 11 — Customer Portal

- Customer login
- Subscription
- Payment history
- Delivery history
- Skip meal
- Pause request
- Renewal

---

# 32. Suggested MVP Navigation

Admin:

```text
Dashboard
Customers
Subscriptions
Plans
Payments
Deliveries
Reports
Staff
Settings
```

Customer:

```text
Dashboard
My Subscription
My Meals
Payments
Profile
```

Delivery Staff:

```text
Today's Deliveries
Completed
Profile
```

Kitchen Staff:

```text
Today's Meals
Meal Summary
```

---

# 33. UI/UX Direction

The application should be:

- Simple
- Fast
- Mobile responsive
- Easy for non-technical mess owners
- Minimal data entry
- Clear status indicators
- Large action buttons
- Search-first
- Dashboard-driven

Avoid making it look like a complicated ERP.

The user should understand the dashboard within a few seconds.

---

# 34. Important UX Principle

The mess owner should be able to perform the common workflow quickly:

```text
Add Customer
      ↓
Select Plan
      ↓
Record Payment
      ↓
Activate
      ↓
Done
```

Daily:

```text
Open Dashboard
      ↓
See Today's Meals
      ↓
See Deliveries
      ↓
Mark Delivered
      ↓
Finish
```

---

# 35. Future Features

Do NOT implement these in the first POC, but keep the architecture ready.

### Payments

- Razorpay
- Automatic payment verification
- Online subscription renewal

### Notifications

- WhatsApp
- SMS
- Email
- Push notifications

### Delivery

- GPS
- Route optimization
- Delivery staff mobile app
- Live tracking

### Kitchen

- Automatic meal quantity calculation
- Menu management
- Ingredient planning
- Inventory

### Business

- Expense management
- Profit/loss
- GST invoices
- Multiple branches

### Customer

- Ratings
- Feedback
- Referral system
- Coupons
- Wallet/credits

---

# 36. Security Requirements

- JWT authentication
- Password hashing
- Role-based permissions
- Business-level data isolation
- API validation
- Input sanitization
- Rate limiting
- HTTPS in production
- Secure environment variables
- No sensitive information in frontend local storage where avoidable
- Audit important administrative actions

---

# 37. Testing

## Backend

Test:

- Authentication
- Permissions
- Customer CRUD
- Subscription calculations
- Expiry logic
- Payment calculations
- Delivery status
- Multi-business data isolation

## Frontend

Test:

- Login
- Protected routes
- Forms
- Tables
- Filters
- Subscription actions
- Payment actions
- Dashboard

---

# 38. Definition of Done — MVP

The MVP is complete when an admin can:

```text
✓ Login

✓ Create customer

✓ Create meal plan

✓ Create subscription

✓ Record payment

✓ View active customers

✓ View expiring subscriptions

✓ View expired subscriptions

✓ View today's deliveries

✓ Mark food as delivered

✓ Mark food as skipped

✓ View payment history

✓ View basic revenue

✓ View basic meal statistics
```

A customer can:

```text
✓ Login

✓ View subscription

✓ View remaining days

✓ View payments

✓ View deliveries

✓ Skip a meal
```

---

# 39. Recommended First POC Demo

The demo should tell one complete story.

### Scenario

Create:

```text
Customer:
Rahul

Plan:
Monthly Lunch

Price:
₹2,500

Subscription:
01 Sep → 30 Sep
```

Then demonstrate:

```text
1. Rahul is added

2. Monthly Lunch plan selected

3. ₹2,500 payment recorded

4. Subscription becomes ACTIVE

5. Today's lunch delivery appears

6. Staff marks it DELIVERED

7. Rahul skips tomorrow's lunch

8. Delivery changes to SKIPPED

9. Admin dashboard shows upcoming expiry

10. Admin opens Rahul's profile

11. Admin sees subscription + payment + delivery history

12. Rahul opens Customer Portal and sees the same information
```

This gives you a complete end-to-end POC rather than a collection of disconnected screens.

---

# 40. Development Priority

```text
HIGH PRIORITY
─────────────

Authentication
Customers
Plans
Subscriptions
Payments
Deliveries
Dashboard
Expiry Tracking


MEDIUM PRIORITY
───────────────

Customer Portal
Reports
Staff Management
Pause Subscription
Meal Skip


LATER
─────

WhatsApp
Razorpay
GPS
Route Optimization
Mobile App
Inventory
AI
Multi-branch
Advanced Analytics
```

---

# 41. Product Positioning

The initial product should not be positioned simply as:

> "Food Delivery App"

Instead:

> **"Digital Management System for Mess & Subscription-Based Food Businesses."**

Core value:

```text
Notebook
   ↓
Digital Customer Records

Manual Subscription Tracking
   ↓
Automatic Expiry Tracking

Manual Payment Tracking
   ↓
Digital Payment Records

Daily WhatsApp/Notebook Delivery List
   ↓
Digital Delivery Management

Guessing Meal Quantity
   ↓
Automatic Meal Count
```

---

# 42. First Development Milestone

Build only this:

```text
LOGIN
  ↓
DASHBOARD
  ↓
CUSTOMERS
  ↓
CUSTOMER DETAILS
  ↓
PLANS
  ↓
SUBSCRIPTION
  ↓
PAYMENT
  ↓
TODAY'S DELIVERY
```

Once this workflow works correctly with demo data, move to reports and the customer portal.

This should be treated as the **MVP foundation**. Future features such as WhatsApp, online payments, GPS, mobile apps, and inventory should be added only after validating the core workflow with actual mess businesses.
