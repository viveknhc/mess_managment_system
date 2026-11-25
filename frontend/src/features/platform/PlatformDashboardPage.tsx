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
      <div className="p-4 sm:p-6">
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
          {error || 'Failed to load dashboard. Please try again.'}
        </div>
      </div>
    )
  }

  const cards = [
    { label: 'Total Businesses', value: stats.total_businesses },
    { label: 'Active', value: stats.active_businesses },
    { label: 'Awaiting First Payment', value: stats.pending_businesses },
    { label: 'Paid & Current', value: stats.paid_businesses },
    { label: 'Payment Overdue', value: stats.past_due_businesses, warn: stats.past_due_businesses > 0 },
    { label: 'Suspended', value: stats.suspended_businesses, warn: stats.suspended_businesses > 0 },
  ]

  return (
    <div className="mx-auto max-w-7xl space-y-3 px-3 pb-6 sm:space-y-4 sm:px-6">
      <h1 className="text-xl font-semibold text-gray-900 sm:text-2xl">Platform Overview</h1>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <div className="col-span-2 flex min-h-28 flex-col justify-between rounded-3xl bg-accent p-4 text-accent-ink sm:min-h-32 sm:p-5">
          <p className="text-xs font-medium sm:text-sm">Total Revenue</p>
          <p className="truncate text-3xl font-light tracking-tight sm:text-4xl">
            {'\u20B9'}{Number(stats.total_revenue).toLocaleString('en-IN')}
          </p>
        </div>
        {cards.map((c) => (
          <div key={c.label} className="flex min-h-24 min-w-0 flex-col justify-between rounded-3xl border border-gray-200 bg-white p-3.5 sm:min-h-32 sm:p-5">
            <p className="text-xs text-gray-500 sm:text-sm">{c.label}</p>
            <p className={`text-2xl font-light tracking-tight sm:text-4xl ${c.warn ? 'text-red-600' : 'text-gray-900'}`}>{c.value}</p>
          </div>
        ))}
      </div>

      {stats.plans_breakdown.length > 0 && (
        <section className="rounded-3xl border border-gray-200 bg-white p-4 sm:p-5">
          <h2 className="mb-3 text-lg font-normal text-gray-900 sm:text-xl">Plans Breakdown</h2>
          <div className="divide-y divide-gray-200">
            {stats.plans_breakdown.map((p) => (
              <div key={p.plan__name} className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-700">{p.plan__name}</span>
                <span className="rounded-full bg-gray-100 px-3 py-0.5 text-xs font-medium text-gray-800">
                  {p.count} {p.count === 1 ? 'business' : 'businesses'}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
