import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { SubscriptionForm } from './SubscriptionForm'

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
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [actionError, setActionError] = useState('')
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchSubs = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page: String(page) }
      if (statusFilter) params.status = statusFilter
      const { data } = await apiClient.get('/subscriptions/', { params })
      setSubs(data.results)
      setCount(data.count)
    } catch {
      // empty state
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => { fetchSubs() }, [fetchSubs])
  useEffect(() => { setPage(1) }, [statusFilter])

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

  const totalPages = Math.ceil(count / 20)

  if (loading && subs.length === 0) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
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

      {subs.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">
            {statusFilter ? `No ${STATUS_LABELS[statusFilter].toLowerCase()} subscriptions` : 'No subscriptions yet'}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {subs.map((sub) => (
              <div key={sub.id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{sub.customer_name}</h3>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[sub.status] || ''}`}>
                        {sub.status}
                      </span>
                      {sub.is_expiring && (
                        <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700">
                          Expiring
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-gray-500">{sub.plan_name}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-gray-900">₹{Number(sub.paid_amount).toLocaleString('en-IN')}</div>
                    <div className="text-xs text-gray-500">of ₹{Number(sub.total_amount).toLocaleString('en-IN')}</div>
                  </div>
                </div>

                <div className="mt-3 flex gap-6 text-xs text-gray-600">
                  <span>{sub.start_date} → {sub.end_date}</span>
                  <span>{sub.remaining_days} days left</span>
                  <span>{sub.remaining_meals} meals left</span>
                  {Number(sub.pending_amount) > 0 && (
                    <span className="font-medium text-red-600">₹{Number(sub.pending_amount).toLocaleString('en-IN')} pending</span>
                  )}
                </div>

                {canWrite && (
                  <div className="mt-3 flex gap-2 border-t border-gray-100 pt-3">
                    {sub.status === 'ACTIVE' && (
                      <>
                        <button onClick={() => handleAction(sub.id, 'pause')}
                          className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50">Pause</button>
                        <button onClick={() => handleAction(sub.id, 'cancel')}
                          className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">Cancel</button>
                      </>
                    )}
                    {sub.status === 'PAUSED' && (
                      <button onClick={() => handleAction(sub.id, 'resume')}
                        className="rounded px-2 py-1 text-xs font-medium text-green-600 hover:bg-green-50">Resume</button>
                    )}
                    {sub.status === 'PENDING' && (
                      <button onClick={() => handleAction(sub.id, 'cancel')}
                        className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">Cancel</button>
                    )}
                    {(sub.status === 'EXPIRED' || sub.status === 'CANCELLED') && (
                      <button onClick={() => handleAction(sub.id, 'renew')}
                        className="rounded px-2 py-1 text-xs font-medium text-green-600 hover:bg-green-50">Renew</button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">Previous</button>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">Next</button>
              </div>
            </div>
          )}
        </>
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
