import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { SubscriptionForm } from './SubscriptionForm'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'
import { notify } from '../../utils/notify'
import { confirmDialog } from '../../components/ui/dialog'
import { FEATURES, useFeature } from '../../hooks/useFeature'
import { CustomizeSubscriptionModal, inr as inrFmt, type CustomItem } from './CustomizationEditor'

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
  custom_price: string | null
  items: CustomItem[]
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

const ACTION_TOAST: Record<string, string> = {
  pause: 'Subscription paused',
  resume: 'Subscription resumed',
  cancel: 'Subscription cancelled',
  renew: 'Subscription renewed',
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
  const table = useServerTable()
  const { params: tableParams, setPage } = table
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'
  const customOn = useFeature(FEATURES.CUSTOM_SUBSCRIPTIONS)
  const [customizing, setCustomizing] = useState<{ sub: Subscription; price: number | null; meals: number | null } | null>(null)

  async function openCustomize(sub: Subscription) {
    let price: number | null = null
    let meals: number | null = null
    if (sub.status === 'PENDING') {
      try {
        const { data } = await apiClient.get(`/plans/${sub.plan}/`)
        price = Number(data.price)
        meals = data.total_meals
      } catch {
        // preview only — the server computes the real total
      }
    }
    setCustomizing({ sub, price, meals })
  }

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

  async function handleAction(sub: Subscription, action: string) {
    if (action === 'cancel') {
      const ok = await confirmDialog({
        title: `Cancel ${sub.customer_name}'s subscription?`,
        message: `${sub.plan_name} will stop and upcoming deliveries will not be made. This cannot be undone.`,
        confirmText: 'Cancel subscription',
        cancelText: 'Keep it',
        tone: 'danger',
      })
      if (!ok) return
    }
    try {
      await apiClient.post(`/subscriptions/${sub.id}/${action}/`)
      notify.success(ACTION_TOAST[action] ?? 'Subscription updated', `${sub.customer_name} — ${sub.plan_name}`)
      await fetchSubs()
    } catch (err: unknown) {
      notify.error(err, `Failed to ${action} subscription`)
    }
  }

  const inr = (v: string) => `₹${Number(v).toLocaleString('en-IN')}`
  const actionBtn = 'rounded px-2 py-1 text-xs font-medium'

  const columns: Column<Subscription>[] = [
    {
      key: 'customer__name', mobile: 'title',
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
    {
      key: 'plan__name', mobile: 'subtitle',
      header: 'Plan',
      sortable: true,
      className: 'text-gray-600',
      render: (s) => (
        <>
          <div>{s.plan_name}</div>
          {s.custom_price !== null && (
            <div className="text-xs text-gray-400">Custom price {inrFmt(s.custom_price)}</div>
          )}
          {s.items.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {s.items.map((i) => (
                <span key={i.label} className="rounded bg-orange-50 px-1.5 py-0.5 text-xs text-orange-700">
                  {i.label}{Number(i.price_per_meal) > 0 ? ` +${inrFmt(i.price_per_meal)}` : ''}
                </span>
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
          {customOn && ['PENDING', 'ACTIVE', 'PAUSED'].includes(s.status) && (
            <button onClick={() => openCustomize(s)} className={`${actionBtn} text-orange-600 hover:bg-orange-50`}>Customize</button>
          )}
          {s.status === 'ACTIVE' && (
            <>
              <button onClick={() => handleAction(s, 'pause')} className={`${actionBtn} text-blue-600 hover:bg-blue-50`}>Pause</button>
              <button onClick={() => handleAction(s, 'cancel')} className={`${actionBtn} text-red-600 hover:bg-red-50`}>Cancel</button>
            </>
          )}
          {s.status === 'PAUSED' && (
            <button onClick={() => handleAction(s, 'resume')} className={`${actionBtn} text-green-600 hover:bg-green-50`}>Resume</button>
          )}
          {s.status === 'PENDING' && (
            <button onClick={() => handleAction(s, 'cancel')} className={`${actionBtn} text-red-600 hover:bg-red-50`}>Cancel</button>
          )}
          {(s.status === 'EXPIRED' || s.status === 'CANCELLED') && (
            <button onClick={() => handleAction(s, 'renew')} className={`${actionBtn} text-green-600 hover:bg-green-50`}>Renew</button>
          )}
        </div>
      ),
    })
  }

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
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

      {customizing && (
        <CustomizeSubscriptionModal
          sub={customizing.sub}
          planPrice={customizing.price}
          totalMeals={customizing.meals}
          onClose={() => setCustomizing(null)}
          onSaved={() => { setCustomizing(null); fetchSubs() }}
        />
      )}

      {showForm && (
        <SubscriptionForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchSubs() }}
        />
      )}
    </div>
  )
}
