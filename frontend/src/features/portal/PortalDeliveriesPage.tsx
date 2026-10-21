import { useEffect, useState } from 'react'
import { DataTable, type Column } from '../../components/ui/DataTable'
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

// The backend DeliveryListSerializer also returns `delivered_at`; it is not on the shared type yet.
type DeliveryRow = PortalDelivery & { delivered_at?: string | null }

function formatDeliveredAt(value?: string | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

const columns: Column<DeliveryRow>[] = [
  {
    key: 'delivery_date',
    header: 'Date',
    sortable: true,
    render: (d) => <span className="whitespace-nowrap text-gray-700">{d.delivery_date}</span>,
  },
  {
    key: 'meal_name',
    header: 'Meal',
    sortable: true,
    render: (d) => <span className="font-medium text-gray-900">{d.meal_name}</span>,
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (d) => (
      <span
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${
          STATUS_STYLES[d.status] ?? 'bg-gray-100 text-gray-600'
        }`}
      >
        {d.status.replace(/_/g, ' ')}
      </span>
    ),
  },
  {
    key: 'delivered_at',
    header: 'Delivered at',
    sortable: true,
    render: (d) =>
      d.delivered_at ? (
        <span className="whitespace-nowrap text-gray-700">{formatDeliveredAt(d.delivered_at)}</span>
      ) : (
        <span className="text-gray-300">—</span>
      ),
  },
  {
    key: 'notes',
    header: 'Notes',
    render: (d) => (d.notes ? <span className="text-xs text-gray-400">{d.notes}</span> : null),
  },
]

export function PortalDeliveriesPage() {
  const [deliveries, setDeliveries] = useState<DeliveryRow[]>([])
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

      <DataTable
        columns={columns}
        rows={deliveries}
        rowKey={(d) => d.id}
        defaultSort={{ key: 'delivery_date', dir: 'desc' }}
        emptyMessage="No deliveries yet"
      />
    </div>
  )
}
