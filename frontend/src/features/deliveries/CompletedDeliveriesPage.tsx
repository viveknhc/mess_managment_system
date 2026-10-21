import { useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'
import { DataTable, type Column } from '../../components/ui/DataTable'

interface DeliveryItem {
  id: string
  customer_name: string
  meal_name: string
  delivery_date: string
  status: string
  delivered_at: string | null
  notes: string
}

const STATUS_STYLES: Record<string, string> = {
  DELIVERED: 'bg-green-50 text-green-700',
  NOT_DELIVERED: 'bg-red-50 text-red-700',
  SKIPPED: 'bg-gray-100 text-gray-500',
  CANCELLED: 'bg-gray-100 text-gray-400',
}

const columns: Column<DeliveryItem>[] = [
  {
    key: 'customer_name',
    header: 'Customer',
    sortable: true,
    className: 'font-medium text-gray-900',
    render: (d) => d.customer_name,
  },
  { key: 'meal_name', header: 'Meal', sortable: true, className: 'text-gray-500', render: (d) => d.meal_name },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (d) => (
      <span
        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${
          STATUS_STYLES[d.status] ?? 'bg-gray-100 text-gray-600'
        }`}
      >
        {d.status.replace(/_/g, ' ')}
      </span>
    ),
  },
  {
    key: 'delivered_at',
    header: 'Time',
    sortable: true,
    className: 'whitespace-nowrap text-gray-500',
    sortValue: (d) => (d.delivered_at ? new Date(d.delivered_at).getTime() : null),
    render: (d) =>
      d.delivered_at ? new Date(d.delivered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—',
  },
  {
    key: 'delivery_date',
    header: 'Date',
    sortable: true,
    className: 'whitespace-nowrap text-gray-500',
    render: (d) => d.delivery_date,
  },
]

export function CompletedDeliveriesPage() {
  const [items, setItems] = useState<DeliveryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // /deliveries/today/ is paginated (20 by default); request the max page size (100)
    // so the client-side filter below sees all of today's deliveries, not just page 1.
    apiClient
      .get('/deliveries/today/', { params: { page_size: '100' } })
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
        <DataTable columns={columns} rows={items} rowKey={(d) => d.id} emptyMessage="Nothing completed yet today" />
      )}
    </div>
  )
}
