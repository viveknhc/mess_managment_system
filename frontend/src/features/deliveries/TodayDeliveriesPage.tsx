import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'

interface DeliveryItem {
  id: string
  customer_name: string
  customer_phone: string
  customer_address: string
  meal_name: string
  delivery_date: string
  status: string
  assigned_staff_name: string | null
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

export function TodayDeliveriesPage() {
  const [deliveries, setDeliveries] = useState<DeliveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [actionError, setActionError] = useState('')
  const user = useAuthStore((s) => s.user)
  const canUpdate = user?.role === 'OWNER' || user?.role === 'MANAGER' || user?.role === 'DELIVERY_STAFF'

  const fetchToday = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/deliveries/today/')
      setDeliveries(data.results ?? data)
    } catch {
      // empty
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchToday() }, [fetchToday])

  async function handleStatus(id: string, status: string) {
    setActionError('')
    try {
      await apiClient.patch(`/deliveries/${id}/status/`, { status })
      await fetchToday()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || 'Failed'
      setActionError(msg)
      setTimeout(() => setActionError(''), 3000)
    }
  }

  async function handleSkip(id: string) {
    setActionError('')
    try {
      await apiClient.post(`/deliveries/${id}/skip/`)
      await fetchToday()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || 'Failed'
      setActionError(msg)
      setTimeout(() => setActionError(''), 3000)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const pending = deliveries.filter((d) => d.status === 'PENDING' || d.status === 'OUT_FOR_DELIVERY')
  const completed = deliveries.filter((d) => d.status !== 'PENDING' && d.status !== 'OUT_FOR_DELIVERY')

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Today's Deliveries</h1>
        <p className="mt-1 text-sm text-gray-500">
          {pending.length} pending · {completed.length} completed · {deliveries.length} total
        </p>
      </div>

      {actionError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</div>
      )}

      {deliveries.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No deliveries scheduled for today</p>
        </div>
      ) : (
        <div className="space-y-3">
          {deliveries.map((d) => (
            <div key={d.id} className={`rounded-xl border bg-white p-4 shadow-sm ${
              d.status === 'DELIVERED' ? 'border-green-200 bg-green-50/30' :
              d.status === 'PENDING' ? 'border-gray-200' : 'border-gray-100 opacity-70'
            }`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{d.customer_name}</h3>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[d.status] || ''}`}>
                      {d.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {d.meal_name} · {d.customer_phone || 'No phone'} · {d.customer_address || 'No address'}
                  </div>
                  {d.notes && <p className="mt-1 text-xs text-gray-400">Note: {d.notes}</p>}
                </div>
              </div>

              {canUpdate && d.status === 'PENDING' && (
                <div className="mt-3 flex gap-2 border-t border-gray-100 pt-3">
                  <button onClick={() => handleStatus(d.id, 'DELIVERED')}
                    className="rounded-lg bg-green-600 px-4 py-2 text-xs font-medium text-white hover:bg-green-700">
                    Delivered
                  </button>
                  <button onClick={() => handleStatus(d.id, 'NOT_DELIVERED')}
                    className="rounded-lg bg-red-100 px-4 py-2 text-xs font-medium text-red-700 hover:bg-red-200">
                    Not Delivered
                  </button>
                  <button onClick={() => handleSkip(d.id)}
                    className="rounded-lg bg-gray-100 px-4 py-2 text-xs font-medium text-gray-600 hover:bg-gray-200">
                    Skip
                  </button>
                </div>
              )}
              {canUpdate && d.status === 'OUT_FOR_DELIVERY' && (
                <div className="mt-3 flex gap-2 border-t border-gray-100 pt-3">
                  <button onClick={() => handleStatus(d.id, 'DELIVERED')}
                    className="rounded-lg bg-green-600 px-4 py-2 text-xs font-medium text-white hover:bg-green-700">
                    Delivered
                  </button>
                  <button onClick={() => handleStatus(d.id, 'NOT_DELIVERED')}
                    className="rounded-lg bg-red-100 px-4 py-2 text-xs font-medium text-red-700 hover:bg-red-200">
                    Not Delivered
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
