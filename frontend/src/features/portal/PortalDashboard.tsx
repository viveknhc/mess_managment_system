import { useEffect, useState } from 'react'
import type { PortalDashboardData } from './portalApi'
import { portalApi } from './portalApi'

export function PortalDashboard() {
  const [data, setData] = useState<PortalDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    portalApi
      .dashboard()
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load your dashboard. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (error || !data) {
    return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error || 'Failed to load portal'}</div>
  }

  const sub = data.active_subscription
  const meal = data.todays_meal

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">Hello, {data.customer_name} 👋</h1>
        <p className="mt-1 text-sm text-gray-500">Your subscription overview</p>
      </div>

      {sub ? (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{sub.plan_name}</h2>
              <p className="mt-0.5 text-xs text-gray-500">
                {sub.start_date} → {sub.end_date}
              </p>
            </div>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                sub.status === 'ACTIVE'
                  ? 'bg-green-50 text-green-700'
                  : sub.status === 'PAUSED'
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'bg-gray-100 text-gray-600'
              }`}
            >
              {sub.status}
            </span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:gap-4">
            <div className="rounded-lg bg-blue-50 p-3 text-center">
              <p className="text-2xl font-bold text-blue-700">{sub.remaining_days}</p>
              <p className="text-xs text-blue-600">Days Remaining</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-2xl font-bold text-green-700">{sub.remaining_meals}</p>
              <p className="text-xs text-green-600">Meals Remaining</p>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-sm">
            <span className="text-gray-500">Payment</span>
            <span className="font-medium text-gray-900">
              ₹{sub.paid_amount} paid
              {Number(sub.pending_amount) > 0 && (
                <span className="text-orange-600"> · ₹{sub.pending_amount} due</span>
              )}
            </span>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-500">No active subscription</p>
          <p className="mt-1 text-xs text-gray-400">Contact your mess to subscribe.</p>
        </div>
      )}

      {meal && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Today's Meal</p>
              <h3 className="mt-0.5 font-semibold text-gray-900">{meal.meal_name}</h3>
              <p className="text-xs text-gray-500">{meal.delivery_date}</p>
            </div>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                meal.status === 'DELIVERED'
                  ? 'bg-green-50 text-green-700'
                  : meal.status === 'PENDING' || meal.status === 'OUT_FOR_DELIVERY'
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'bg-gray-100 text-gray-500'
              }`}
            >
              {meal.status.replace(/_/g, ' ')}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
