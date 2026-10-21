import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { CustomerForm } from './CustomerForm'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

interface Customer {
  id: string
  customer_code: string
  name: string
  phone: string
  email: string
  status: string
  location: string
  created_at: string
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
  { key: 'name', header: 'Name', sortable: true, className: 'font-medium text-gray-900', render: (c) => c.name },
  {
    key: 'phone',
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
      <span
        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
          c.status === 'ACTIVE'
            ? 'bg-green-50 text-green-700'
            : c.status === 'BLOCKED'
              ? 'bg-red-50 text-red-700'
              : 'bg-gray-100 text-gray-500'
        }`}
      >
        {c.status}
      </span>
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
  const table = useServerTable()
  const { params: tableParams, setPage } = table
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchCustomers = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { ...tableParams }
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      const { data } = await apiClient.get('/customers/', { params })
      setCustomers(data.results)
      setCount(data.count)
    } catch {
      // handled by empty state
    } finally {
      setLoading(false)
    }
  }, [tableParams, search, statusFilter])

  useEffect(() => {
    fetchCustomers()
  }, [fetchCustomers])

  useEffect(() => {
    setPage(1)
  }, [search, statusFilter, setPage])

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Customers</h1>
          <p className="mt-1 text-sm text-gray-500">{count} customer{count !== 1 ? 's' : ''}</p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Add Customer
          </button>
        )}
      </div>

      {/* Search + filters */}
      <div className="mb-4 flex gap-3">
        <input
          type="text"
          placeholder="Search by name, phone, code, address..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
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
      </div>

      {!loading && count === 0 && !search && !statusFilter ? (
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
          columns={columns}
          rows={customers}
          rowKey={(c) => c.id}
          loading={loading}
          emptyMessage="No customers match your search"
          onRowClick={(c) => navigate(`/customers/${c.id}`)}
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
    </div>
  )
}
