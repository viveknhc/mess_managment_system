import { useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'

interface MealCount {
  meal__name: string
  count: number
}

interface StatusSummary {
  delivered: number
  pending: number
  skipped: number
  not_delivered: number
}

export function KitchenCountsPage({ showSummary = false }: { showSummary?: boolean }) {
  const [counts, setCounts] = useState<MealCount[]>([])
  const [summary, setSummary] = useState<StatusSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [countsRes, deliveriesRes] = await Promise.all([
          apiClient.get('/deliveries/kitchen_counts/'),
          apiClient.get('/deliveries/today/'),
        ])
        setCounts(countsRes.data)
        const items: Array<{ status: string }> = deliveriesRes.data.results ?? deliveriesRes.data
        setSummary({
          delivered: items.filter((d) => d.status === 'DELIVERED').length,
          pending: items.filter((d) => d.status === 'PENDING' || d.status === 'OUT_FOR_DELIVERY').length,
          skipped: items.filter((d) => d.status === 'SKIPPED').length,
          not_delivered: items.filter((d) => d.status === 'NOT_DELIVERED').length,
        })
      } catch {
        // empty state
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const total = counts.reduce((sum, c) => sum + c.count, 0)

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">
        {showSummary ? 'Meal Summary' : "Today's Meals"}
      </h1>
      <p className="mt-1 text-sm text-gray-500">Meals to prepare today</p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {counts.map((c) => (
          <div key={c.meal__name} className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow-sm">
            <p className="text-3xl font-bold text-primary-700">{c.count}</p>
            <p className="mt-1 text-sm font-medium text-gray-600">{c.meal__name}</p>
          </div>
        ))}
        {counts.length === 0 && (
          <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm sm:col-span-3">
            <p className="text-gray-500">No meals scheduled for today</p>
          </div>
        )}
      </div>

      {showSummary && summary && (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="mb-3 text-sm font-medium text-gray-700">Today's delivery outcomes</p>
          <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
            <div className="rounded-lg bg-green-50 p-3">
              <p className="text-xl font-bold text-green-700">{summary.delivered}</p>
              <p className="text-xs text-green-600">Delivered</p>
            </div>
            <div className="rounded-lg bg-yellow-50 p-3">
              <p className="text-xl font-bold text-yellow-700">{summary.pending}</p>
              <p className="text-xs text-yellow-600">Pending</p>
            </div>
            <div className="rounded-lg bg-gray-100 p-3">
              <p className="text-xl font-bold text-gray-600">{summary.skipped}</p>
              <p className="text-xs text-gray-500">Skipped</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3">
              <p className="text-xl font-bold text-red-700">{summary.not_delivered}</p>
              <p className="text-xs text-red-600">Not Delivered</p>
            </div>
          </div>
          <p className="mt-3 text-right text-xs text-gray-400">Total: {total} meals</p>
        </div>
      )}
    </div>
  )
}
