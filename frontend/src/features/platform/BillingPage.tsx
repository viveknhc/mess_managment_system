import { useState, useEffect, useCallback } from 'react'
import { billingApi, type BillingData, type SaasPlan } from './platformApi'

export function BillingPage() {
  const [billing, setBilling] = useState<BillingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [checkoutLoading, setCheckoutLoading] = useState(false)

  const fetchBilling = useCallback(async () => {
    setLoading(true)
    try {
      const data = await billingApi.getBilling()
      setBilling(data)
    } catch {
      setError('Failed to load billing information.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBilling()
  }, [fetchBilling])

  async function handleCheckout(plan: SaasPlan) {
    setCheckoutLoading(true)
    setError('')
    const result = await billingApi.checkout(plan.id)
    if (!result.ok) {
      setError(result.error)
      setCheckoutLoading(false)
      return
    }

    // If Razorpay subscription ID returned, open Razorpay checkout
    if (result.data.razorpay_subscription_id) {
      openRazorpayCheckout(result.data)
    } else {
      // Direct activation (dev mode)
      await fetchBilling()
    }
    setCheckoutLoading(false)
  }

  function openRazorpayCheckout(data: { razorpay_subscription_id: string; razorpay_key: string }) {
    const options = {
      key: data.razorpay_key,
      subscription_id: data.razorpay_subscription_id,
      name: 'Mess Manager',
      description: 'Monthly Subscription',
      handler: () => {
        fetchBilling()
      },
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const rzp = new (window as any).Razorpay(options)
    rzp.open()
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (error && !billing) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      </div>
    )
  }

  const sub = billing?.subscription
  const plans = billing?.available_plans || []

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Billing</h1>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Current Plan Status */}
      {sub && (
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Current Plan</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <span
                className={`inline-block mt-1 rounded-full px-3 py-1 text-xs font-medium ${
                  sub.status === 'ACTIVE'
                    ? 'bg-green-100 text-green-700'
                    : sub.status === 'TRIAL'
                      ? 'bg-blue-100 text-blue-700'
                      : sub.status === 'PAST_DUE'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                }`}
              >
                {sub.status}
              </span>
            </div>
            <div>
              <p className="text-sm text-gray-500">Plan</p>
              <p className="mt-1 font-medium text-gray-900">
                {sub.plan_name || 'Free Trial'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">
                {sub.status === 'TRIAL' ? 'Trial Days Remaining' : 'Days Until Renewal'}
              </p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {sub.days_remaining ?? '—'}
              </p>
            </div>
          </div>
          {sub.status === 'TRIAL' && sub.trial_end_date && (
            <p className="mt-4 text-sm text-gray-500">
              Trial expires on {new Date(sub.trial_end_date).toLocaleDateString('en-IN')}
            </p>
          )}
        </div>
      )}

      {/* Available Plans */}
      {plans.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            {sub?.plan_name ? 'Change Plan' : 'Choose a Plan'}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`rounded-xl border p-6 ${
                  sub?.plan === plan.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-white'
                }`}
              >
                <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                <p className="mt-1 text-3xl font-bold text-gray-900">
                  <span className="text-lg">&#8377;</span>{plan.price_monthly}
                  <span className="text-sm font-normal text-gray-500">/month</span>
                </p>
                <ul className="mt-4 space-y-2">
                  {plan.features.map((f, i) => (
                    <li key={i} className="flex items-center text-sm text-gray-600">
                      <span className="mr-2 text-green-500">&#10003;</span>
                      {f}
                    </li>
                  ))}
                  <li className="flex items-center text-sm text-gray-600">
                    <span className="mr-2 text-green-500">&#10003;</span>
                    {plan.max_customers === 0 ? 'Unlimited' : plan.max_customers} customers
                  </li>
                  <li className="flex items-center text-sm text-gray-600">
                    <span className="mr-2 text-green-500">&#10003;</span>
                    {plan.max_staff === 0 ? 'Unlimited' : plan.max_staff} staff members
                  </li>
                </ul>
                {sub?.plan !== plan.id && (
                  <button
                    onClick={() => handleCheckout(plan)}
                    disabled={checkoutLoading}
                    className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {checkoutLoading ? 'Processing...' : 'Subscribe'}
                  </button>
                )}
                {sub?.plan === plan.id && (
                  <p className="mt-4 text-center text-sm font-medium text-blue-600">
                    Current Plan
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
