import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'
import { confirmDialog, promptDialog } from '../../components/ui/dialog'
import { notify } from '../../utils/notify'
import { NOT_DELIVERED_REASONS, deliveryApi, isOpen, type DeliveryItem } from './deliveryApi'
import { FEATURES, useFeature } from '../../hooks/useFeature'
import { routeApi, type DeliveryRoute } from './routeApi'

/** Route filter value: '' = all, NO_ROUTE = customers on no route, else a route id. */
const NO_ROUTE = 'none'

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'bg-yellow-50 text-yellow-700',
  OUT_FOR_DELIVERY: 'bg-blue-50 text-blue-700',
  DELIVERED: 'bg-green-50 text-green-700',
  NOT_DELIVERED: 'bg-red-50 text-red-700',
  SKIPPED: 'bg-gray-100 text-gray-500',
  CANCELLED: 'bg-gray-100 text-gray-400',
}

function formatTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function TodayDeliveriesPage() {
  const [deliveries, setDeliveries] = useState<DeliveryItem[]>([])
  const [count, setCount] = useState(0)
  const [summary, setSummary] = useState({ pending: 0, completed: 0 })
  const [loading, setLoading] = useState(true)
  const table = useServerTable()
  const { params: tableParams } = table
  const user = useAuthStore((s) => s.user)
  const canUpdate = user?.role === 'OWNER' || user?.role === 'MANAGER' || user?.role === 'DELIVERY_STAFF'
  // Skipping changes the customer's subscription — owner/manager only (delivery staff just record outcomes)
  const canSkip = user?.role === 'OWNER' || user?.role === 'MANAGER'
  const routesOn = useFeature(FEATURES.DELIVERY_ROUTES)
  const [routes, setRoutes] = useState<DeliveryRoute[]>([])
  const [routeFilter, setRouteFilter] = useState('')

  useEffect(() => {
    if (routesOn) routeApi.list().then(setRoutes).catch(() => setRoutes([]))
  }, [routesOn])

  const fetchToday = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { ...tableParams }
      if (routeFilter === NO_ROUTE) params.no_route = 'true'
      else if (routeFilter) params.route = routeFilter
      const [pageRes, summaryRes] = await Promise.all([
        apiClient.get('/deliveries/today/', { params }),
        apiClient.get<{ total: number; pending: number }>('/deliveries/today_summary/'),
      ])
      setDeliveries(pageRes.data.results ?? pageRes.data)
      setCount(pageRes.data.count ?? (pageRes.data.results ?? pageRes.data).length)
      const { total, pending } = summaryRes.data
      setSummary({ pending, completed: total - pending })
    } catch {
      // empty
    } finally {
      setLoading(false)
    }
  }, [tableParams, routeFilter])

  useEffect(() => {
    fetchToday()
  }, [fetchToday])

  useEffect(() => {
    table.setPage(1)
  }, [routeFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleUndo(d: DeliveryItem) {
    try {
      await deliveryApi.undo(d.id)
      notify.info(`${d.customer_name} moved back to pending`)
      await fetchToday()
    } catch (err: unknown) {
      notify.error(err, 'Could not undo')
    }
  }

  async function handleDelivered(d: DeliveryItem) {
    try {
      await deliveryApi.setStatus(d.id, 'DELIVERED')
      notify.undoable(`Delivered to ${d.customer_name}`, () => handleUndo(d))
      await fetchToday()
    } catch (err: unknown) {
      notify.error(err, 'Could not update the delivery')
    }
  }

  async function handleNotDelivered(d: DeliveryItem) {
    const reason = await promptDialog({
      title: `Couldn't deliver to ${d.customer_name}?`,
      message: 'Pick a reason or type one.',
      options: NOT_DELIVERED_REASONS,
      placeholder: 'Reason',
      confirmText: 'Mark not delivered',
      tone: 'danger',
    })
    if (reason === null) return
    try {
      await deliveryApi.setStatus(d.id, 'NOT_DELIVERED', reason)
      notify.undoable(`Marked not delivered: ${d.customer_name}`, () => handleUndo(d), reason)
      await fetchToday()
    } catch (err: unknown) {
      notify.error(err, 'Could not update the delivery')
    }
  }

  async function handleSkip(d: DeliveryItem) {
    const ok = await confirmDialog({
      title: `Skip ${d.customer_name}'s ${d.meal_name.toLowerCase()} today?`,
      message: "The meal won't be delivered. Your mess's skip rule decides whether the subscription is extended.",
      confirmText: 'Skip meal',
    })
    if (!ok) return
    try {
      await deliveryApi.skip(d.id)
      notify.success(`Skipped ${d.customer_name}'s meal`)
      await fetchToday()
    } catch (err: unknown) {
      notify.error(err, 'Could not skip the meal')
    }
  }

  const columns: Column<DeliveryItem>[] = [
    {
      key: 'customer__name', mobile: 'title',
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
      key: 'customer__address', mobile: 'subtitle',
      header: 'Address',
      sortable: true,
      className: 'text-gray-500',
      render: (d) => d.customer_address || 'No address',
    },
    {
      key: 'meal__name',
      header: 'Meal',
      sortable: true,
      className: 'text-gray-700',
      render: (d) => (
        <>
          <div>{d.meal_name}</div>
          {d.customizations.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {d.customizations.map((c) => (
                <span key={c} className="rounded bg-orange-50 px-1.5 py-0.5 text-xs font-medium text-orange-700">{c}</span>
              ))}
            </div>
          )}
        </>
      ),
    },
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
    ...(routesOn
      ? [
          {
            key: 'route',
            header: 'Route',
            className: 'whitespace-nowrap text-gray-500',
            render: (d: DeliveryItem) => d.route_name || '—',
          },
        ]
      : []),
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
              onClick={() => handleDelivered(d)}
              className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
            >
              Delivered
            </button>
            <button
              type="button"
              onClick={() => handleNotDelivered(d)}
              className="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200"
            >
              Not Delivered
            </button>
            {d.status === 'PENDING' && canSkip && (
              <button
                type="button"
                onClick={() => handleSkip(d)}
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
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Today's Deliveries</h1>
          <p className="mt-1 text-sm text-gray-500">
            {summary.pending} pending · {summary.completed} completed · {routeFilter ? `${count} on this route` : `${count} total`}
          </p>
        </div>
        {routesOn && routes.length > 0 && (
          <label className="flex items-center gap-2 text-sm text-gray-600">
            Route
            <select
              value={routeFilter}
              onChange={(e) => setRouteFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All routes</option>
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}{r.staff_name ? ` (${r.staff_name})` : ''}
                </option>
              ))}
              <option value={NO_ROUTE}>No route</option>
            </select>
          </label>
        )}
      </div>

      {!loading && count === 0 && !routeFilter ? (
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
