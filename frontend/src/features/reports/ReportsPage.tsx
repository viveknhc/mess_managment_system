import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { apiClient } from '../../services/apiClient'

interface RevenueData {
  daily: Array<{ payment_date: string; total: number; count: number }>
  monthly: Array<{ year: number; month: number; total: number }>
  total_collected: number
  total_pending: number
}

interface SubReport {
  active: number; pending: number; paused: number; expired: number; cancelled: number; expiring_3_days: number; renewed: number
}

interface MealItem { meal_name: string; delivered: number; skipped: number; not_delivered: number; pending: number; total: number }

const PIE_COLORS = ['#10b981', '#f59e0b', '#3b82f6', '#6b7280', '#ef4444']

export function ReportsPage() {
  const [revenue, setRevenue] = useState<RevenueData | null>(null)
  const [subs, setSubs] = useState<SubReport | null>(null)
  const [meals, setMeals] = useState<MealItem[]>([])
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  async function fetchReports() {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const [revRes, subRes, mealRes] = await Promise.all([
        apiClient.get('/reports/revenue/', { params }),
        apiClient.get('/reports/subscriptions/'),
        apiClient.get('/reports/meals/', { params }),
      ])
      setRevenue(revRes.data)
      setSubs(subRes.data)
      setMeals(mealRes.data.by_meal)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReports() }, [dateFrom, dateTo]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading && !revenue) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const subPieData = subs ? [
    { name: 'Active', value: subs.active },
    { name: 'Pending', value: subs.pending },
    { name: 'Paused', value: subs.paused },
    { name: 'Expired', value: subs.expired },
    { name: 'Cancelled', value: subs.cancelled },
  ].filter(d => d.value > 0) : []

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Reports</h1>
        <div className="flex gap-3">
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm" placeholder="From" />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm" placeholder="To" />
        </div>
      </div>

      {/* Revenue summary */}
      {revenue && (
        <div className="mb-6 grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase">Total Collected</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              ₹{Number(revenue.total_collected).toLocaleString('en-IN')}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-red-500 uppercase">Total Pending</p>
            <p className="mt-1 text-2xl font-bold text-red-600">
              ₹{Number(revenue.total_pending).toLocaleString('en-IN')}
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Revenue trend (R-07) */}
        {revenue && revenue.daily.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Revenue Trend</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={revenue.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="payment_date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="total" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Subscription status breakdown (R-08) */}
        {subPieData.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Subscription Status</h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={subPieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {subPieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            {subs && subs.expiring_3_days > 0 && (
              <p className="mt-2 text-center text-xs text-orange-600 font-medium">
                {subs.expiring_3_days} expiring within 3 days
              </p>
            )}
          </div>
        )}

        {/* Meal distribution (R-08) */}
        {meals.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Meal Distribution</h2>
            <div className="space-y-3">
              {meals.map((m) => (
                <div key={m.meal_name}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-900">{m.meal_name}</span>
                    <span className="text-gray-500">{m.total} total</span>
                  </div>
                  <div className="mt-1 flex gap-1 text-xs">
                    {m.delivered > 0 && <span className="rounded bg-green-50 px-1.5 py-0.5 text-green-700">{m.delivered} delivered</span>}
                    {m.pending > 0 && <span className="rounded bg-yellow-50 px-1.5 py-0.5 text-yellow-700">{m.pending} pending</span>}
                    {m.skipped > 0 && <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">{m.skipped} skipped</span>}
                    {m.not_delivered > 0 && <span className="rounded bg-red-50 px-1.5 py-0.5 text-red-700">{m.not_delivered} missed</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
