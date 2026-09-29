import { useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'

interface DeliveryItem {
  id: string
  customer_name: string
  meal_name: string
  delivery_date: string
  status: string
  notes: string
}

const STATUS_STYLES: Record<string, string> = {
  DELIVERED: 'bg-green-50 text-green-700',
  NOT_DELIVERED: 'bg-red-50 text-red-700',
  SKIPPED: 'bg-gray-100 text-gray-500',
  CANCELLED: 'bg-gray-100 text-gray-400',
}

export function CompletedDeliveriesPage() {
  const [items, setItems] = useState<DeliveryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient
      .get('/deliveries/today/')
      .then((res) => {
        const all: DeliveryItem[] = res.data.results ?? res.data
        setItems(all.filter((d) => d.status !== 'PENDING' && d.status !== 'OUT_FOR_DELIVERY'))
      })
      .catch(() => setItems([]))
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
      <h1 className="mb-6 text-xl font-bold text-gray-900 sm:text-2xl">Completed</h1>

      {items.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-500">Nothing completed yet today</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm"
            >
              <div>
                <p className="text-sm font-medium text-gray-900">{d.customer_name}</p>
                <p className="text-xs text-gray-500">
                  {d.meal_name} · {d.delivery_date}
                </p>
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
