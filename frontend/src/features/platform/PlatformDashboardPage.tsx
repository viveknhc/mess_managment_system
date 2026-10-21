import { useState, useEffect } from 'react'
import { platformApi, type PlatformStats } from './platformApi'

export function PlatformDashboardPage() {
  const [stats, setStats] = useState<PlatformStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    platformApi.getStats()
      .then(setStats)
      .catch((e) => setError(e?.response?.data?.error?.message || 'Failed to load dashboard.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
          {error || 'Failed to load dashboard. Please try again.'}
        </div>
      </div>
    )
  }

  const cards = [
    { label: 'Total Businesses', value: stats.total_businesses, color: 'blue' },
    { label: 'Active', value: stats.active_businesses, color: 'green' },
    { label: 'On Trial', value: stats.trial_businesses, color: 'indigo' },
    { label: 'Paid', value: stats.paid_businesses, color: 'emerald' },
    { label: 'Suspended', value: stats.suspended_businesses, color: 'red' },
    { label: 'Total Revenue', value: `\u20B9${stats.total_revenue}`, color: 'purple' },
  ]

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Platform Overview</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-sm text-gray-500">{c.label}</p>
            <p className="mt-1 text-3xl font-bold text-gray-900">{c.value}</p>
          </div>
        ))}
      </div>

      {stats.plans_breakdown.length > 0 && (
        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Plans Breakdown</h2>
          <div className="space-y-2">
            {stats.plans_breakdown.map((p) => (
              <div key={p.plan__name} className="flex items-center justify-between">
                <span className="text-sm text-gray-700">{p.plan__name}</span>
                <span className="rounded-full bg-purple-100 px-3 py-0.5 text-sm font-medium text-purple-700">
                  {p.count} businesses
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
