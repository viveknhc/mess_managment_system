import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { SubscriptionForm } from './SubscriptionForm'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

interface Subscription {
  id: string
  customer: string
  customer_name: string
  plan: string
  plan_name: string
  start_date: string
  end_date: string
  status: string
  total_amount: string
  paid_amount: string
  pending_amount: string
  remaining_meals: number
  remaining_days: number
  is_expiring: boolean
  renewed_from: string | null
}

const STATUS_TABS = ['', 'PENDING', 'ACTIVE', 'PAUSED', 'EXPIRED', 'CANCELLED'] as const
const STATUS_LABELS: Record<string, string> = {
  '': 'All',
  PENDING: 'Pending',
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  EXPIRED: 'Expired',
  CANCELLED: 'Cancelled',
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'bg-yellow-50 text-yellow-700',
  ACTIVE: 'bg-green-50 text-green-700',
  PAUSED: 'bg-blue-50 text-blue-700',
  EXPIRED: 'bg-gray-100 text-gray-600',
  CANCELLED: 'bg-red-50 text-red-700',
}

export function SubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [actionError, setActionError] = useState('')
  const table = useServerTable()
  const { params: tableParams, setPage } = table
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchSubs = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { ...tableParams }
      if (statusFilter) params.status = statusFilter
      const { data } = await apiClient.get('/subscriptions/', { params })
      setSubs(data.results)
      setCount(data.count)
    } catch {
      // empty state
    } finally {
      setLoading(false)
    }
  }, [tableParams, statusFilter])

  useEffect(() => { fetchSubs() }, [fetchSubs])
  useEffect(() => { setPage(1) }, [statusFilter, setPage])

  async function handleAction(subId: string, action: string) {
    setActionError('')
    try {
      await apiClient.post(`/subscriptions/${subId}/${action}/`)
      await fetchSubs()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || `Failed to ${action}`
      setActionError(msg)
      setTimeout(() => setActionError(''), 4000)
    }
  }

  const inr = (v: string) => `₹${Number(v).toLocaleString('en-IN')}`
  const actionBtn = 'rounded px-2 py-1 text-xs font-medium'

  const columns: Column<Subscription>[] = [
    {
      key: 'customer__name',
      header: 'Customer',
      sortable: true,
      render: (s) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900">{s.customer_name}</span>
          {s.is_expiring && (
            <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700">Expiring</span>
          )}
        </div>
      ),
    },
    { key: 'plan__name', header: 'Plan', sortable: true, className: 'text-gray-600', render: (s) => s.plan_name },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (s) => (
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[s.status] || ''}`}>{s.status}</span>
      ),
    },
    { key: 'start_date', header: 'Start', sortable: true, className: 'whitespace-nowrap text-gray-600', render: (s) => s.start_date },
    {
      key: 'end_date',
      header: 'End',
      sortable: true,
      className: 'whitespace-nowrap',
      render: (s) => (
        <>
          <div className="text-gray-600">{s.end_date}</div>
          <div className="text-xs text-gray-400">{s.remaining_days} days left</div>
        </>
      ),
    },
    { key: 'remaining_meals', header: 'Meals left', sortable: true, align: 'right', className: 'text-gray-600', render: (s) => s.remaining_meals },
    {
      key: 'paid_amount',
      header: 'Paid',
      sortable: true,
      align: 'right',
      className: 'whitespace-nowrap',
      render: (s) => (
        <>
          <div className="font-semibold text-gray-900">{inr(s.paid_amount)}</div>
          <div className="text-xs text-gray-500">of {inr(s.total_amount)}</div>
        </>
      ),
    },
    {
      key: 'pending_amount',
      header: 'Pending',
      sortable: true,
      align: 'right',
      className: 'whitespace-nowrap',
      render: (s) =>
        Number(s.pending_amount) > 0 ? <span className="font-medium text-red-600">{inr(s.pending_amount)}</span> : <span className="text-gray-400">—</span>,
    },
  ]

  if (canWrite) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (s) => (
        <div className="flex justify-end gap-1">
          {s.status === 'ACTIVE' && (
            <>
              <button onClick={() => handleAction(s.id, 'pause')} className={`${actionBtn} text-blue-600 hover:bg-blue-50`}>Pause</button>
              <button onClick={() => handleAction(s.id, 'cancel')} className={`${actionBtn} text-red-600 hover:bg-red-50`}>Cancel</button>
            </>
          )}
          {s.status === 'PAUSED' && (
            <button onClick={() => handleAction(s.id, 'resume')} className={`${actionBtn} text-green-600 hover:bg-green-50`}>Resume</button>
          )}
          {s.status === 'PENDING' && (
            <button onClick={() => handleAction(s.id, 'cancel')} className={`${actionBtn} text-red-600 hover:bg-red-50`}>Cancel</button>
          )}
          {(s.status === 'EXPIRED' || s.status === 'CANCELLED') && (
            <button onClick={() => handleAction(s.id, 'renew')} className={`${actionBtn} text-green-600 hover:bg-green-50`}>Renew</button>
          )}
        </div>
      ),
    })
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Subscriptions</h1>
          <p className="mt-1 text-sm text-gray-500">{count} subscription{count !== 1 ? 's' : ''}</p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New Subscription
          </button>
        )}
      </div>

      {actionError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</div>
      )}

      {/* Status tabs */}
      <div className="mb-4 flex gap-1 overflow-x-auto">
        {STATUS_TABS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${
              statusFilter === s
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {STATUS_LABELS[s]}
          </button>
        ))}
      </div>

      <DataTable
        columns={columns}
        rows={subs}
        rowKey={(s) => s.id}
        loading={loading}
        emptyMessage={statusFilter ? `No ${STATUS_LABELS[statusFilter].toLowerCase()} subscriptions` : 'No subscriptions yet'}
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

      {showForm && (
        <SubscriptionForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchSubs() }}
        />
      )}
    </div>
  )
}
