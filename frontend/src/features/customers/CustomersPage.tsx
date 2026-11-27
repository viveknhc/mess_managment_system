import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { CustomerForm } from './CustomerForm'
import { CustomerImportModal } from './CustomerImportModal'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'
import { notify } from '../../utils/notify'
import { FEATURES, useFeature } from '../../hooks/useFeature'
import { routeApi, type DeliveryRoute } from '../deliveries/routeApi'
import { StatusBadge } from '../../components/ui/StatusBadge'

interface Customer {
  id: string
  customer_code: string
  name: string
  phone: string
  email: string
  status: string
  location: string
  route: string | null
  route_name: string | null
  created_at: string
}

/** Route filter value for customers on no route. */
const NO_ROUTE = 'none'

const routeColumn: Column<Customer> = {
  key: 'route',
  header: 'Route',
  className: 'whitespace-nowrap text-gray-500',
  render: (c) => c.route_name || '—',
}

const STATUS_OPTIONS = ['', 'ACTIVE', 'INACTIVE', 'BLOCKED'] as const

const columns: Column<Customer>[] = [
  {
    key: 'customer_code',
    header: 'Code',
    sortable: true,
    className: 'font-mono text-xs text-gray-500',
    render: (c) => c.customer_code,
  },
  { key: 'name', mobile: 'title', header: 'Name', sortable: true, className: 'font-medium text-gray-900', render: (c) => c.name },
  {
    key: 'phone', mobile: 'subtitle',
    header: 'Contact',
    sortable: true,
    render: (c) => (
      <>
        <div className="text-gray-900">{c.phone || '—'}</div>
        <div className="text-xs text-gray-500">{c.email || ''}</div>
      </>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (c) => (
      <StatusBadge status={c.status} />
    ),
  },
  { key: 'location', header: 'Location', sortable: true, className: 'text-gray-500', render: (c) => c.location || '—' },
  {
    key: 'created_at',
    header: 'Joined',
    sortable: true,
    className: 'whitespace-nowrap text-gray-500',
    render: (c) => c.created_at.slice(0, 10),
  },
]

export function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const table = useServerTable()
  const { params: tableParams, setPage } = table
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'
  const routesOn = useFeature(FEATURES.DELIVERY_ROUTES) && canWrite
  const [routes, setRoutes] = useState<DeliveryRoute[]>([])
  const [routeFilter, setRouteFilter] = useState('')
  const shownColumns = routesOn ? [...columns.slice(0, 5), routeColumn, ...columns.slice(5)] : columns

  useEffect(() => {
    if (routesOn) routeApi.list().then(setRoutes).catch(() => setRoutes([]))
  }, [routesOn])

  const fetchCustomers = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { ...tableParams }
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      if (routeFilter === NO_ROUTE) params.no_route = 'true'
      else if (routeFilter) params.route = routeFilter
      const { data } = await apiClient.get('/customers/', { params })
      setCustomers(data.results)
      setCount(data.count)
    } catch {
      // handled by empty state
    } finally {
      setLoading(false)
    }
  }, [tableParams, search, statusFilter, routeFilter])

  useEffect(() => {
    fetchCustomers()
  }, [fetchCustomers])

  useEffect(() => {
    setPage(1)
  }, [search, statusFilter, routeFilter, setPage])

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Customers</h1>
          <p className="mt-1 text-sm text-gray-500">{count} customer{count !== 1 ? 's' : ''}</p>
        </div>
        {canWrite && (
          <div className="flex gap-2">
            <button
              onClick={() => setShowImport(true)}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Import CSV
            </button>
            <button
              onClick={() => setShowForm(true)}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Add Customer
            </button>
          </div>
        )}
      </div>

      {/* Search + filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search by name, phone, code, address..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-0 flex-1 basis-56 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s || 'All Statuses'}
            </option>
          ))}
        </select>
        {routesOn && routes.length > 0 && (
          <select
            value={routeFilter}
            onChange={(e) => setRouteFilter(e.target.value)}
            aria-label="Filter by route"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          >
            <option value="">All Routes</option>
            {routes.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
            <option value={NO_ROUTE}>No route</option>
          </select>
        )}
      </div>

      {!loading && count === 0 && !search && !statusFilter && !routeFilter ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No customers yet</p>
          {canWrite && (
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Add your first customer
            </button>
          )}
        </div>
      ) : (
        <DataTable
          columns={shownColumns}
          rows={customers}
          rowKey={(c) => c.id}
          loading={loading}
          emptyMessage="No customers match your search"
          onRowClick={(c) => navigate(`/app/customers/${c.id}`)}
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

      {showForm && (
        <CustomerForm
          onClose={() => setShowForm(false)}
          onSaved={() => {
            setShowForm(false)
            fetchCustomers()
          }}
        />
      )}

      {showImport && (
        <CustomerImportModal
          onClose={() => setShowImport(false)}
          onImported={(created) => {
            setShowImport(false)
            notify.success(`Imported ${created} customer${created !== 1 ? 's' : ''}`)
            fetchCustomers()
          }}
        />
      )}
    </div>
  )
}
