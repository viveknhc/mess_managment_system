import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'

interface DashboardData {
  customers: { active: number; new_this_month: number }
  subscriptions: {
    active: number; pending: number; expiring_today: number
    expiring_3_days: number; expiring_week: number; expired: number
  }
  deliveries: { total_today: number; delivered: number; pending: number }
  meals_today: Array<{ meal__name: string; count: number }>
  payments: { today_revenue: number; month_revenue: number; total_pending: number }
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    apiClient.get('/dashboard/').then((res) => {
      setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!data) {
    return <div className="p-6 text-gray-500">Failed to load dashboard</div>
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">Dashboard</h1>

      {/* Stat cards row */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Active Customers" value={data.customers.active} onClick={() => navigate('/customers')} />
        <StatCard label="Active Subscriptions" value={data.subscriptions.active} onClick={() => navigate('/subscriptions')} />
        <StatCard label="Today's Revenue" value={`₹${Number(data.payments.today_revenue).toLocaleString('en-IN')}`} onClick={() => navigate('/payments')} />
        <StatCard label="Pending Payments" value={`₹${Number(data.payments.total_pending).toLocaleString('en-IN')}`} color="red" onClick={() => navigate('/payments')} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Expiry widget (DB-05) */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Expiring Subscriptions</h2>
          <div className="space-y-2">
            <ExpiryRow label="Expiring Today" count={data.subscriptions.expiring_today} color="red" />
            <ExpiryRow label="Within 3 Days" count={data.subscriptions.expiring_3_days} color="orange" />
            <ExpiryRow label="This Week" count={data.subscriptions.expiring_week} color="yellow" />
            <ExpiryRow label="Already Expired" count={data.subscriptions.expired} color="gray" />
            <ExpiryRow label="Pending Activation" count={data.subscriptions.pending} color="blue" />
          </div>
        </div>

        {/* Delivery widget (DB-06) */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Today's Deliveries</h2>
          <div className="mb-4 flex gap-4">
            <div className="flex-1 rounded-lg bg-green-50 p-3 text-center">
              <p className="text-2xl font-bold text-green-700">{data.deliveries.delivered}</p>
              <p className="text-xs text-green-600">Delivered</p>
            </div>
            <div className="flex-1 rounded-lg bg-yellow-50 p-3 text-center">
              <p className="text-2xl font-bold text-yellow-700">{data.deliveries.pending}</p>
              <p className="text-xs text-yellow-600">Pending</p>
            </div>
            <div className="flex-1 rounded-lg bg-gray-50 p-3 text-center">
              <p className="text-2xl font-bold text-gray-700">{data.deliveries.total_today}</p>
              <p className="text-xs text-gray-500">Total</p>
            </div>
          </div>

          {/* Meal counts */}
          {data.meals_today.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <p className="mb-2 text-xs font-medium text-gray-500">Meals Breakdown</p>
              {data.meals_today.map((m) => (
                <div key={m.meal__name} className="flex items-center justify-between py-1">
                  <span className="text-sm text-gray-700">{m.meal__name}</span>
                  <span className="text-sm font-semibold text-gray-900">{m.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Payment widget (DB-07) */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Revenue</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Today</span>
              <span className="text-lg font-bold text-gray-900">₹{Number(data.payments.today_revenue).toLocaleString('en-IN')}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">This Month</span>
              <span className="text-lg font-bold text-gray-900">₹{Number(data.payments.month_revenue).toLocaleString('en-IN')}</span>
            </div>
            <div className="flex items-center justify-between border-t border-gray-100 pt-3">
              <span className="text-sm font-medium text-red-600">Total Pending</span>
              <span className="text-lg font-bold text-red-600">₹{Number(data.payments.total_pending).toLocaleString('en-IN')}</span>
            </div>
          </div>
        </div>

        {/* Quick actions (DB-08) */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            <QuickAction label="Add Customer" onClick={() => navigate('/customers')} />
            <QuickAction label="New Subscription" onClick={() => navigate('/subscriptions')} />
            <QuickAction label="Record Payment" onClick={() => navigate('/payments')} />
            <QuickAction label="View Deliveries" onClick={() => navigate('/deliveries')} />
          </div>
        </div>
      </div>

      {/* New this month */}
      <div className="mt-4 text-xs text-gray-400 text-right">
        {data.customers.new_this_month} new customer{data.customers.new_this_month !== 1 ? 's' : ''} this month
      </div>
    </div>
  )
}

function StatCard({ label, value, color, onClick }: { label: string; value: string | number; color?: string; onClick?: () => void }) {
  return (
    <button onClick={onClick} className="rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm hover:shadow-md transition-shadow">
      <p className="text-xs font-medium text-gray-500 uppercase">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color === 'red' ? 'text-red-600' : 'text-gray-900'}`}>{value}</p>
    </button>
  )
}

function ExpiryRow({ label, count, color }: { label: string; count: number; color: string }) {
  const colors: Record<string, string> = {
    red: 'bg-red-100 text-red-700',
    orange: 'bg-orange-100 text-orange-700',
    yellow: 'bg-yellow-100 text-yellow-700',
    gray: 'bg-gray-100 text-gray-600',
    blue: 'bg-blue-100 text-blue-700',
  }
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${colors[color] || ''}`}>{count}</span>
    </div>
  )
}

function QuickAction({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded-lg border border-gray-200 p-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
      {label}
    </button>
  )
}
