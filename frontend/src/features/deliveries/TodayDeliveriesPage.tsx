import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

interface DeliveryItem {
  id: string
  customer_name: string
  customer_phone: string
  customer_address: string
  meal_name: string
  delivery_date: string
  status: string
  assigned_staff_name: string | null
  delivered_at: string | null
  notes: string
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'bg-yellow-50 text-yellow-700',
  OUT_FOR_DELIVERY: 'bg-blue-50 text-blue-700',
  DELIVERED: 'bg-green-50 text-green-700',
  NOT_DELIVERED: 'bg-red-50 text-red-700',
  SKIPPED: 'bg-gray-100 text-gray-500',
  CANCELLED: 'bg-gray-100 text-gray-400',
}

function isOpen(status: string) {
  return status === 'PENDING' || status === 'OUT_FOR_DELIVERY'
}

function formatTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function errorMessage(err: unknown) {
  return (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed'
}

export function TodayDeliveriesPage() {
  const [deliveries, setDeliveries] = useState<DeliveryItem[]>([])
  const [count, setCount] = useState(0)
  const [summary, setSummary] = useState({ pending: 0, completed: 0 })
  const [loading, setLoading] = useState(true)
  const [actionError, setActionError] = useState('')
  const table = useServerTable()
  const { params: tableParams } = table
  const user = useAuthStore((s) => s.user)
  const canUpdate = user?.role === 'OWNER' || user?.role === 'MANAGER' || user?.role === 'DELIVERY_STAFF'

  const fetchToday = useCallback(async () => {
    setLoading(true)
    try {
      // The table shows one page; summary counts need every delivery for today,
      // so fetch a single max-size page (backend caps page_size at 100) alongside it.
      const [pageRes, summaryRes] = await Promise.all([
        apiClient.get('/deliveries/today/', { params: tableParams }),
        apiClient.get('/deliveries/today/', { params: { page_size: '100' } }),
      ])
      setDeliveries(pageRes.data.results ?? pageRes.data)
      setCount(pageRes.data.count ?? (pageRes.data.results ?? pageRes.data).length)
      const all: DeliveryItem[] = summaryRes.data.results ?? summaryRes.data
      const pending = all.filter((d) => isOpen(d.status)).length
      setSummary({ pending, completed: all.length - pending })
    } catch {
      // empty
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchToday()
  }, [fetchToday])

  function showError(err: unknown) {
    setActionError(errorMessage(err))
    setTimeout(() => setActionError(''), 3000)
  }

  async function handleStatus(id: string, status: string) {
    setActionError('')
    try {
      await apiClient.patch(`/deliveries/${id}/status/`, { status })
      await fetchToday()
    } catch (err: unknown) {
      showError(err)
    }
  }

  async function handleSkip(id: string) {
    setActionError('')
    try {
      await apiClient.post(`/deliveries/${id}/skip/`)
      await fetchToday()
    } catch (err: unknown) {
      showError(err)
    }
  }

  const columns: Column<DeliveryItem>[] = [
    {
      key: 'customer__name',
      header: 'Customer',
      sortable: true,
      className: 'font-medium text-gray-900',
      render: (d) => d.customer_name,
    },
    {
      key: 'phone',
      header: 'Phone',
      className: 'whitespace-nowrap text-gray-500',
      render: (d) => d.customer_phone || 'No phone',
    },
    {
      key: 'customer__address',
      header: 'Address',
      sortable: true,
      className: 'text-gray-500',
      render: (d) => d.customer_address || 'No address',
    },
    { key: 'meal__name', header: 'Meal', sortable: true, className: 'text-gray-700', render: (d) => d.meal_name },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (d) => (
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${STATUS_COLORS[d.status] || ''}`}
        >
          {d.status.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'assigned_staff__name',
      header: 'Staff',
      sortable: true,
      className: 'text-gray-500',
      render: (d) => d.assigned_staff_name || '—',
    },
    {
      key: 'delivered_at',
      header: 'Delivered',
      sortable: true,
      className: 'whitespace-nowrap text-gray-500',
      render: (d) => formatTime(d.delivered_at),
    },
    {
      key: 'notes',
      header: 'Notes',
      className: 'text-xs text-gray-400',
      render: (d) => d.notes || '',
    },
  ]

  if (canUpdate) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (d) =>
        isOpen(d.status) ? (
          <div className="flex justify-end gap-2 whitespace-nowrap">
            <button
              type="button"
              onClick={() => handleStatus(d.id, 'DELIVERED')}
              className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
            >
              Delivered
            </button>
            <button
              type="button"
              onClick={() => handleStatus(d.id, 'NOT_DELIVERED')}
              className="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200"
            >
              Not Delivered
            </button>
            {d.status === 'PENDING' && (
              <button
                type="button"
                onClick={() => handleSkip(d.id)}
                className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200"
              >
                Skip
              </button>
            )}
          </div>
        ) : null,
    })
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Today's Deliveries</h1>
        <p className="mt-1 text-sm text-gray-500">
          {summary.pending} pending · {summary.completed} completed · {count} total
        </p>
      </div>

      {actionError && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</div>}

      {!loading && count === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No deliveries scheduled for today</p>
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={deliveries}
          rowKey={(d) => d.id}
          loading={loading}
          emptyMessage="No deliveries scheduled for today"
          rowClassName={(d) =>
            d.status === 'DELIVERED' ? 'bg-green-50/30' : isOpen(d.status) ? '' : 'opacity-70'
          }
          sort={table.sort}
          onSortChange={table.setSort}
          pagination={{
            page: table.page,
            pageSize: table.pageSize,
            count,
            onPageChange: table.setPage,
            onPageSizeChange: table.setPageSize,
          }}
        />
      )}
    </div>
  )
}
