import { useEffect, useState } from 'react'
import type { PortalDelivery } from './portalApi'
import { portalApi } from './portalApi'

const STATUS_STYLES: Record<string, string> = {
  PENDING: 'bg-yellow-50 text-yellow-700',
  OUT_FOR_DELIVERY: 'bg-blue-50 text-blue-700',
  DELIVERED: 'bg-green-50 text-green-700',
  NOT_DELIVERED: 'bg-red-50 text-red-700',
  SKIPPED: 'bg-gray-100 text-gray-500',
  CANCELLED: 'bg-gray-100 text-gray-400',
}

export function PortalDeliveriesPage() {
  const [deliveries, setDeliveries] = useState<PortalDelivery[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    portalApi
      .deliveries()
      .then((res) => setDeliveries(res.data))
      .catch(() => setDeliveries([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900 sm:text-2xl">My Meals</h1>

      {deliveries.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-500">No deliveries yet</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {deliveries.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm"
            >
              <div>
                <p className="text-sm font-medium text-gray-900">{d.meal_name}</p>
                <p className="text-xs text-gray-500">{d.delivery_date}</p>
                {d.notes && <p className="mt-1 text-xs text-gray-400">{d.notes}</p>}
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  STATUS_STYLES[d.status] ?? 'bg-gray-100 text-gray-600'
                }`}
              >
                {d.status.replace(/_/g, ' ')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
