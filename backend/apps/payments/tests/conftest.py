"""Share the online-payment fixtures (businesses, users, plan, subscription, Razorpay mock)
with the other payment test modules."""

from apps.payments.tests.test_online_payments import (  # noqa: F401
    biz_a,
    biz_b,
    cust_a,
    cust_b,
    cust_user_a,
    cust_user_b,
    manager_a,
    online_a,
    owner_a,
    plan_a,
    rz,
    sub_a,
)
