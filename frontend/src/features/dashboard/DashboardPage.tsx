import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { apiClient } from '../../services/apiClient'
import { useThemeColors } from '../../hooks/useThemeColors'

interface DashboardData {
  customers: { active: number; new_this_month: number }
  subscriptions: {
    active: number; pending: number; expiring_today: number
    expiring_3_days: number; expiring_week: number; expired: number
  }
  deliveries: { total_today: number; delivered: number; pending: number }
  meals_today: Array<{ meal__name: string; count: number }>
  activity?: Array<{ date: string; meals: number }>
  payments: { today_revenue: number; month_revenue: number; total_pending: number }
}

const inr = (v: number) => `₹${Number(v).toLocaleString('en-IN')}`

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

  const newThisMonth = data.customers.new_this_month
  return (
    <div className="mx-auto max-w-7xl space-y-3 px-3 pb-6 sm:space-y-4 sm:px-6">
      <h1 className="sr-only">Dashboard</h1>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard highlight label="Active Customers" value={data.customers.active}
          note={`+${newThisMonth} new this month`} onClick={() => navigate('/app/customers')} />
        <KpiCard label="Active Subscriptions" value={data.subscriptions.active}
          note={`${data.subscriptions.pending} waiting for payment`} onClick={() => navigate('/app/subscriptions')} />
        <KpiCard label="Today's Revenue" value={inr(data.payments.today_revenue)}
          note={`${inr(data.payments.month_revenue)} this month`} onClick={() => navigate('/app/payments')} />
        <KpiCard label="Pending Payments" value={inr(data.payments.total_pending)} tone="danger"
          note="still to collect" onClick={() => navigate('/app/payments')} />
      </div>

      <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <Panel title="Activity" tag="Last 7 days">
          <ActivityChart data={data.activity ?? []} />
        </Panel>
        <TodaysDeliveries data={data} onOpen={() => navigate('/app/deliveries')} />
      </div>

      <div className="grid gap-3 sm:gap-4 lg:grid-cols-3">
        <Panel title="Expiring Subscriptions">
          <div className="space-y-1.5">
            <PillRow label="Expiring today" count={data.subscriptions.expiring_today} tone="danger" />
            <PillRow label="Within 3 days" count={data.subscriptions.expiring_3_days} tone="warning" />
            <PillRow label="This week" count={data.subscriptions.expiring_week} tone="soft" />
            <PillRow label="Already expired" count={data.subscriptions.expired} tone="muted" />
            <PillRow label="Pending activation" count={data.subscriptions.pending} tone="accent" />
          </div>
        </Panel>

        <Panel title="Revenue" tag="This month">
          <p className="text-3xl font-light tracking-tight text-gray-900 sm:text-4xl">{inr(data.payments.month_revenue)}</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-2xl border border-gray-200 p-3">
              <p className="text-xs text-gray-500">Today</p>
              <p className="mt-1 text-xl font-medium text-gray-900">{inr(data.payments.today_revenue)}</p>
            </div>
            <div className="rounded-2xl border border-gray-200 p-3">
              <p className="text-xs text-red-600">Total pending</p>
              <p className="mt-1 text-xl font-medium text-red-600">{inr(data.payments.total_pending)}</p>
            </div>
          </div>
        </Panel>

        <Panel title="Quick Actions">
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-1 2xl:grid-cols-2">
            <QuickAction label="Add Customer" onClick={() => navigate('/app/customers')} />
            <QuickAction label="New Subscription" onClick={() => navigate('/app/subscriptions')} />
            <QuickAction label="Record Payment" onClick={() => navigate('/app/payments')} />
            <QuickAction label="View Deliveries" onClick={() => navigate('/app/deliveries')} />
          </div>
        </Panel>
      </div>
    </div>
  )
}

function ArrowIcon({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 17 17 7M8 7h9v9" />
    </svg>
  )
}

function KpiCard({ label, value, note, highlight, tone, onClick }: {
  label: string; value: string | number; note?: string; highlight?: boolean; tone?: 'danger'; onClick: () => void
}) {
  return (
    <button onClick={onClick}
      className={`group flex min-h-28 min-w-0 flex-col justify-between rounded-3xl p-3.5 text-left sm:min-h-32 sm:rounded-[1.75rem] sm:p-5 transition-transform hover:-translate-y-0.5 ${
        highlight ? 'bg-accent text-accent-ink' : 'border border-gray-200 bg-white text-gray-900'
      }`}>
      <span className="flex items-start justify-between gap-3">
        <span className={`text-xs font-medium sm:text-sm ${highlight ? '' : 'text-gray-700'}`}>{label}</span>
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors sm:h-10 sm:w-10 ${
          highlight ? 'bg-accent-ink text-accent' : 'border border-gray-300 text-gray-700 group-hover:bg-gray-100'
        }`}>
          <ArrowIcon />
        </span>
      </span>
      <span className="mt-3 flex min-w-0 flex-col sm:mt-4 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-2">
        <span className={`truncate text-2xl font-light tracking-tight sm:text-4xl ${tone === 'danger' && !highlight ? 'text-red-600' : ''}`}>{value}</span>
        {note && <span className={`truncate text-[11px] sm:text-xs ${highlight ? 'opacity-70' : 'text-gray-500'}`}>{note}</span>}
      </span>
    </button>
  )
}

function Panel({ title, tag, action, children }: { title: string; tag?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-gray-200 bg-white p-4 sm:rounded-[1.75rem] sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-3 sm:mb-4">
        <h2 className="text-lg font-normal text-gray-900 sm:text-xl">{title}</h2>
        {action ?? (tag && <span className="rounded-full bg-gray-100 px-3.5 py-1.5 text-xs text-gray-700">{tag}</span>)}
      </div>
      {children}
    </section>
  )
}

/** Meals per day — bars coloured like the reference: quiet (dark), usual (light), busy (accent),
 * measured against this week's average so a steady mess still shows its busier days. */
function ActivityChart({ data }: { data: Array<{ date: string; meals: number }> }) {
  const c = useThemeColors()
  const avg = data.reduce((sum, d) => sum + d.meals, 0) / Math.max(1, data.length)
  const band = (n: number) => (n > avg * 1.1 ? 'high' : n < avg * 0.9 ? 'low' : 'mid')
  const fill = { low: c.muted, mid: c.soft, high: c.accent }
  const rows = data.map((d) => ({
    ...d,
    label: new Date(`${d.date}T00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
  }))

  if (rows.every((r) => r.meals === 0)) {
    return <p className="py-10 text-center text-sm text-gray-500">No meals scheduled in the last 7 days yet.</p>
  }
  return (
    <div>
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 0, left: -24, bottom: 0 }} barCategoryGap="18%">
            <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: c.subtle, fontSize: 11 }} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: c.subtle, fontSize: 11 }} />
            <Tooltip
              cursor={false}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="rounded-xl bg-gray-900 px-3 py-2 text-xs text-white shadow-lg">
                    <p className="font-semibold">{payload[0].payload.label}</p>
                    <p>{payload[0].payload.meals} meals</p>
                  </div>
                ) : null
              }
            />
            <Bar dataKey="meals" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {rows.map((r) => <Cell key={r.date} fill={fill[band(r.meals)]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex flex-wrap justify-center gap-x-5 gap-y-1 text-xs text-gray-600">
        <Legend color={c.muted} label="quieter than usual" />
        <Legend color={c.soft} label="usual day" />
        <Legend color={c.accent} label="busy day" />
      </div>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-3 w-3 rounded-full" style={{ background: color }} />
      {label}
    </span>
  )
}

function TodaysDeliveries({ data, onOpen }: { data: DashboardData; onOpen: () => void }) {
  const d = data.deliveries
  return (
    <Panel title="Today's Deliveries" action={
      <button onClick={onOpen} aria-label="Open today's deliveries"
        className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100">
        <ArrowIcon />
      </button>
    }>
      <div className="mb-3 flex flex-wrap gap-2">
        <CountPill label="Pending" count={d.pending} active />
        <CountPill label="Delivered" count={d.delivered} />
        <CountPill label="Total" count={d.total_today} />
      </div>
      {data.meals_today.length > 0 ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
              <th className="pb-2 font-normal">Meal</th>
              <th className="pb-2 text-right font-normal">To cook &amp; deliver</th>
            </tr>
          </thead>
          <tbody>
            {data.meals_today.map((m) => (
              <tr key={m.meal__name} className="border-b border-gray-200 last:border-0">
                <td className="py-2.5 text-gray-900">{m.meal__name}</td>
                <td className="py-2.5 text-right">
                  <span className="inline-flex min-w-12 justify-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-900">
                    {m.count}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="py-6 text-center text-sm text-gray-500">No meals to deliver today.</p>
      )}
    </Panel>
  )
}

function CountPill({ label, count, active }: { label: string; count: number; active?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full py-1 pl-4 pr-1 text-sm ${
      active ? 'bg-accent text-accent-ink' : 'border border-gray-300 text-gray-700'
    }`}>
      {label}
      <span className={`flex h-7 min-w-7 items-center justify-center rounded-full px-1.5 text-xs font-semibold ${
        active ? 'bg-accent-ink text-accent' : 'bg-gray-900 text-white'
      }`}>
        {count}
      </span>
    </span>
  )
}

const PILL_TONES = {
  danger: 'bg-red-100 text-red-700',
  warning: 'bg-orange-100 text-orange-700',
  soft: 'bg-yellow-100 text-yellow-700',
  muted: 'bg-gray-100 text-gray-600',
  accent: 'bg-accent text-accent-ink',
}

function PillRow({ label, count, tone }: { label: string; count: number; tone: keyof typeof PILL_TONES }) {
  return (
    <div className="flex items-center justify-between rounded-full border border-gray-200 py-1 pl-4 pr-1">
      <span className="text-sm text-gray-700">{label}</span>
      <span className={`flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-xs font-semibold ${PILL_TONES[tone]}`}>{count}</span>
    </div>
  )
}

function QuickAction({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="group flex items-center justify-between gap-2 whitespace-nowrap rounded-full border border-gray-300 py-1 pl-3.5 pr-1 text-xs font-medium text-gray-800 sm:text-sm transition-colors hover:border-transparent hover:bg-accent hover:text-accent-ink">
      {label}
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-700 group-hover:bg-accent-ink group-hover:text-accent">
        <ArrowIcon className="h-3.5 w-3.5" />
      </span>
    </button>
  )
}
