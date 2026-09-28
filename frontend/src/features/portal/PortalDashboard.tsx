import { useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'

interface PortalData {
  customer_name: string
  active_subscription: {
    plan_name: string
    start_date: string
    end_date: string
    remaining_days: number
    remaining_meals: number
    status: string
    paid_amount: string
    total_amount: string
  } | null
  total_subscriptions: number
}

export function PortalDashboard() {
  const [data, setData] = useState<PortalData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get('/portal/dashboard/').then((res) => {
      setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!data) return <div className="p-6 text-gray-500">Failed to load portal</div>

  const sub = data.active_subscription

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-1 text-xl font-bold text-gray-900">Welcome, {data.customer_name}</h1>
      <p className="mb-6 text-sm text-gray-500">Your subscription overview</p>

      {sub ? (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold text-gray-900">{sub.plan_name}</h2>
              <p className="mt-0.5 text-xs text-gray-500">{sub.start_date} to {sub.end_date}</p>
            </div>
            <span className="rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">
              {sub.status}
            </span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-blue-50 p-3 text-center">
              <p className="text-2xl font-bold text-blue-700">{sub.remaining_days}</p>
              <p className="text-xs text-blue-600">Days Left</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-2xl font-bold text-green-700">{sub.remaining_meals}</p>
              <p className="text-xs text-green-600">Meals Left</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-500">No active subscription</p>
        </div>
      )}
    </div>
  )
}
