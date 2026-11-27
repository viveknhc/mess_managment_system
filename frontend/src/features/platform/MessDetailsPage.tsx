import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { NavLink, useNavigate, useParams } from 'react-router-dom'
import { platformApi, type MessOverview, type PlatformBusiness } from './platformApi'
import { CustomizeBusinessModal } from './CustomizeBusinessModal'
import { METHOD_LABEL, STATUS_LABEL, dayBefore, formatDate, rupees } from './billingFormat'
import { StatusBadge } from '../../components/ui/StatusBadge'

const ROLE_LABEL: Record<string, string> = {
  OWNER: 'Owner',
  MANAGER: 'Manager',
  DELIVERY_STAFF: 'Delivery',
  KITCHEN_STAFF: 'Kitchen',
}

const SOURCE_LABEL = { plan: 'From plan', default: 'Standard', override: 'Changed for this mess' } as const

function Card({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  )
}

function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-bold text-gray-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
    </div>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-gray-100 py-2 text-sm last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="text-right font-medium text-gray-900">{children}</span>
    </div>
  )
}

function OnOff({ on }: { on: boolean }) {
  return (
    <StatusBadge status={on ? 'ON' : 'OFF'} label={on ? 'On' : 'Off'} />
  )
}

function limit(used: number, max: number) {
  return max === 0 ? `${used} / unlimited` : `${used} / ${max}`
}

function time(t: string | null) {
  return t ? t.slice(0, 5) : '—'
}

function MessList({ businesses, selectedId }: { businesses: PlatformBusiness[]; selectedId?: string }) {
  const [query, setQuery] = useState('')
  const shown = businesses.filter((b) => b.name.toLowerCase().includes(query.trim().toLowerCase()))
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-gray-200 bg-white md:flex">
      <div className="border-b border-gray-200 p-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`Search ${businesses.length} messes`}
          aria-label="Search messes"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      </div>
      <nav aria-label="Messes" className="flex-1 space-y-1 overflow-y-auto p-2">
        {shown.map((b) => (
          <NavLink
            key={b.id}
            to={`/platform/messes/${b.id}`}
            className={`block rounded-lg px-3 py-2 ${b.id === selectedId ? 'bg-purple-50 ring-1 ring-purple-200' : 'hover:bg-gray-50'}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className={`truncate text-sm font-medium ${b.id === selectedId ? 'text-purple-700' : 'text-gray-900'}`}>{b.name}</span>
              {b.status === 'SUSPENDED' && <span className="h-2 w-2 shrink-0 rounded-full bg-red-500" title="Suspended" />}
            </div>
            <p className="mt-0.5 truncate text-xs text-gray-500">
              {b.plan_name ?? 'No plan'} · {b.customer_count} customers
            </p>
          </NavLink>
        ))}
        {shown.length === 0 && <p className="p-3 text-sm text-gray-500">No messes match.</p>}
      </nav>
    </aside>
  )
}

function MessOverviewPanel({ data, onCustomize }: { data: MessOverview; onCustomize: () => void }) {
  const { business, billing, customers, subscriptions, payments, deliveries_today: today } = data
  const plan = billing.plan_details
  const activeSubs = subscriptions.by_status.ACTIVE ?? 0
  const staffCount = data.team.length

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">{business.name}</h1>
            <StatusBadge status={billing.status} label={STATUS_LABEL[billing.status]} />
            {business.status === 'SUSPENDED' && <StatusBadge status="SUSPENDED" label="Suspended" />}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {[business.address, business.phone, business.email].filter(Boolean).join(' · ') || 'No contact details'}
          </p>
          <p className="text-xs text-gray-400">Joined {formatDate(business.created_at)}</p>
        </div>
        <button
          onClick={onCustomize}
          className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
        >
          Customize features & workflows
        </button>
      </div>

      {/* Numbers */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Customers" value={customers.total} hint={`${customers.portal_logins} with portal login`} />
        <Stat
          label="Active subscriptions"
          value={activeSubs}
          hint={subscriptions.expiring ? `${subscriptions.expiring} expiring in 3 days` : 'None expiring soon'}
        />
        <Stat label="Collected (30 days)" value={rupees(payments.last_30_days)} hint={`${rupees(payments.total_collected)} all time`} />
        <Stat label="Customer dues" value={rupees(subscriptions.amount_pending)} hint="Unpaid on live subscriptions" />
        <Stat label="Today's deliveries" value={today.total} hint={`${today.delivered} delivered · ${today.pending} pending`} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        {/* MessDeck plan & billing */}
        <Card title="MessDeck plan & billing">
          {plan ? (
            <>
              <div className="mb-3 flex items-baseline justify-between">
                <p className="text-lg font-semibold text-gray-900">{plan.name}</p>
                <p className="text-sm text-gray-600">
                  {rupees(plan.price_monthly)}/month · setup {rupees(plan.setup_fee)}
                </p>
              </div>
              <Row label="Customers used">{limit(customers.total, plan.max_customers)}</Row>
              <Row label="Staff used">{limit(staffCount, plan.max_staff)}</Row>
              <Row label="Setup fee">{billing.setup_fee_paid ? 'Paid' : 'Not paid yet'}</Row>
              <Row label="Paid until">{billing.current_period_end ? formatDate(dayBefore(billing.current_period_end)) : '—'}</Row>
              <Row label="Next payment">
                {rupees(billing.amount_due.total)} due {formatDate(billing.amount_due.due_date)}
              </Row>
            </>
          ) : (
            <p className="text-sm text-gray-500">No plan assigned.</p>
          )}
          <p className="mt-4 mb-1 text-xs font-semibold text-gray-500">Recent payments to MessDeck</p>
          {billing.recent_payments.length === 0 ? (
            <p className="text-sm text-gray-500">None yet.</p>
          ) : (
            <ul className="divide-y divide-gray-100 text-sm">
              {billing.recent_payments.map((p) => (
                <li key={p.id} className="flex justify-between py-1.5">
                  <span className="text-gray-600">
                    {formatDate(p.created_at)} · {METHOD_LABEL[p.method] ?? p.method}
                  </span>
                  <span className={p.status === 'PAID' ? 'font-medium text-gray-900' : 'text-red-600'}>
                    {rupees(p.amount)} {p.status !== 'PAID' && `(${p.status.toLowerCase()})`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Features */}
        <Card
          title="Features"
          action={<button onClick={onCustomize} className="text-xs font-medium text-purple-600 hover:text-purple-700">Change</button>}
        >
          <ul className="divide-y divide-gray-100">
            {data.features.map((f) => (
              <li key={f.key} className="flex items-center justify-between gap-4 py-2.5">
                <div>
                  <p className="text-sm font-medium text-gray-900">{f.label}</p>
                  <p className="text-xs text-gray-500">{f.description}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <OnOff on={f.enabled} />
                  <span className={`text-[11px] ${f.source === 'override' ? 'font-medium text-amber-700' : 'text-gray-400'}`}>
                    {SOURCE_LABEL[f.source]}
                    {f.source === 'override' && ` (plan: ${f.inherited ? 'on' : 'off'})`}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* Workflows */}
        <Card
          title="Workflows"
          action={<button onClick={onCustomize} className="text-xs font-medium text-purple-600 hover:text-purple-700">Change</button>}
        >
          <ul className="divide-y divide-gray-100">
            {data.policies.map((p) => (
              <li key={p.point} className="py-2.5">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-gray-500">{p.point_label}</p>
                  <StatusBadge status={p.is_default ? 'DEFAULT' : 'CUSTOM'} label={p.is_default ? 'Default' : 'Custom'} />
                </div>
                <p className="text-sm font-medium text-gray-900">{p.policy_label}</p>
                <p className="text-xs text-gray-500">{p.description}</p>
              </li>
            ))}
          </ul>
        </Card>

        {/* Owner's settings */}
        <Card title="Mess settings (set by owner)">
          {data.settings ? (
            <>
              <Row label="Kitchen closed on">
                {data.settings.weekly_off_days.length
                  ? data.settings.weekly_off_days.map((d) => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d]).join(', ')
                  : 'Open every day'}
              </Row>
              <Row label="Pause length">
                {data.settings.min_pause_days}–{data.settings.max_pause_days} days
              </Row>
              <Row label="Delivery window">
                {data.settings.delivery_start_time || data.settings.delivery_end_time
                  ? `${time(data.settings.delivery_start_time)} – ${time(data.settings.delivery_end_time)}`
                  : 'Not set'}
              </Row>
              <Row label="Online payments">
                {data.settings.online_payments_enabled ? 'Switched on' : 'Switched off'}
                {' · '}
                {data.settings.razorpay_configured ? 'Razorpay keys saved' : 'No Razorpay keys'}
              </Row>
              <Row label="Owner notified on">
                {[
                  data.settings.notify_on_payment && 'payments',
                  data.settings.notify_on_expiring && 'expiring subscriptions',
                  data.settings.notify_on_delivery && 'deliveries',
                ]
                  .filter(Boolean)
                  .join(', ') || 'nothing'}
              </Row>
            </>
          ) : (
            <p className="text-sm text-gray-500">The owner hasn't opened Settings yet; defaults apply.</p>
          )}
        </Card>

        {/* Subscriptions */}
        <Card title="Customer subscriptions">
          <div className="flex flex-wrap gap-2">
            {Object.keys(subscriptions.by_status).length === 0 && <p className="text-sm text-gray-500">No subscriptions yet.</p>}
            {Object.entries(subscriptions.by_status).map(([status, n]) => (
              <StatusBadge
                key={status}
                status={status}
                size="md"
                label={
                  <>
                    <span className="font-semibold">{n}</span> {status.toLowerCase()}
                  </>
                }
              />
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Customers: {Object.entries(customers.by_status).map(([s, n]) => `${n} ${s.toLowerCase()}`).join(' · ') || 'none'} ·{' '}
            {payments.count} payments recorded
          </p>
        </Card>

        {/* Team */}
        <Card title={`Owner & staff (${staffCount})`}>
          <ul className="divide-y divide-gray-100">
            {data.team.map((u) => (
              <li key={u.id} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {u.name || u.username}{' '}
                    {!u.is_active && <span className="text-xs font-normal text-red-600">(inactive)</span>}
                  </p>
                  <p className="truncate text-xs text-gray-500">
                    @{u.username}
                    {u.email && ` · ${u.email}`}
                    {u.phone && ` · ${u.phone}`}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{ROLE_LABEL[u.role] ?? u.role}</span>
                  <p className="mt-0.5 text-[11px] text-gray-400">
                    {u.last_login ? `Last login ${formatDate(u.last_login)}` : 'Never logged in'}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Meal plans */}
      <Card title={`Meal plans (${data.meal_plans.length})`}>
        {data.meal_plans.length === 0 ? (
          <p className="text-sm text-gray-500">No meal plans yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500">
                  <th className="py-2 pr-4 font-medium">Plan</th>
                  <th className="py-2 pr-4 font-medium">Meal</th>
                  <th className="py-2 pr-4 text-right font-medium">Price</th>
                  <th className="py-2 pr-4 text-right font-medium">Days / meals</th>
                  <th className="py-2 pr-4 font-medium">Skip / pause</th>
                  <th className="py-2 text-right font-medium">Active subs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.meal_plans.map((p) => (
                  <tr key={p.id} className={p.is_active ? '' : 'text-gray-400'}>
                    <td className="py-2 pr-4 font-medium">
                      {p.name} {!p.is_active && <span className="text-xs font-normal">(inactive)</span>}
                    </td>
                    <td className="py-2 pr-4">{p.meal}</td>
                    <td className="py-2 pr-4 text-right">{rupees(p.price)}</td>
                    <td className="py-2 pr-4 text-right">
                      {p.duration_days} / {p.total_meals}
                    </td>
                    <td className="py-2 pr-4">
                      {p.skip_allowed ? 'Skip' : 'No skip'} · {p.pause_allowed ? 'Pause' : 'No pause'}
                    </td>
                    <td className="py-2 text-right">{p.active_subscriptions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Activity */}
      <Card title="Recent activity">
        {data.recent_activity.length === 0 ? (
          <p className="text-sm text-gray-500">Nothing recorded yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {data.recent_activity.map((a, i) => (
              <li key={i} className="flex justify-between gap-4 py-2 text-sm">
                <span className="text-gray-700">
                  <span className="font-medium">{a.action.toLowerCase().replace(/_/g, ' ')}</span>
                  {a.description && ` · ${a.description}`}
                </span>
                <span className="shrink-0 text-xs text-gray-400">
                  {a.user ? `${a.user} · ` : ''}
                  {formatDate(a.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

export function MessDetailsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [businesses, setBusinesses] = useState<PlatformBusiness[] | null>(null)
  const [overview, setOverview] = useState<MessOverview | null>(null)
  const [error, setError] = useState('')
  const [customizing, setCustomizing] = useState(false)

  useEffect(() => {
    platformApi
      .getBusinesses({ page_size: '100', ordering: 'name' })
      .then((d) => setBusinesses(d.results))
      .catch(() => setError('Could not load messes.'))
  }, [])

  // No mess picked → open the first one.
  useEffect(() => {
    if (!id && businesses?.length) navigate(`/platform/messes/${businesses[0].id}`, { replace: true })
  }, [id, businesses, navigate])

  const loadOverview = useCallback(async (messId: string) => {
    setError('')
    try {
      setOverview(await platformApi.getMessOverview(messId))
    } catch {
      setError('Could not load this mess.')
    }
  }, [])

  useEffect(() => {
    if (id) loadOverview(id)
  }, [id, loadOverview])

  const shown = overview && overview.business.id === id ? overview : null
  const selected = useMemo(() => businesses?.find((b) => b.id === id), [businesses, id])

  return (
    <div className="flex h-full">
      {businesses ? (
        <MessList businesses={businesses} selectedId={id} />
      ) : (
        <aside className="hidden w-72 shrink-0 border-r border-gray-200 bg-white p-4 text-sm text-gray-500 md:block">Loading...</aside>
      )}
      <div className="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6">
        {/* Phones: the mess list sidebar is hidden, pick from a dropdown instead. */}
        {businesses && businesses.length > 0 && (
          <select
            value={id ?? ''}
            onChange={(e) => navigate(`/platform/messes/${e.target.value}`)}
            aria-label="Choose mess"
            className="mb-4 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm md:hidden"
          >
            {businesses.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
                {b.status === 'SUSPENDED' ? ' (suspended)' : ''}
              </option>
            ))}
          </select>
        )}
        {error && <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        {businesses?.length === 0 && <p className="text-sm text-gray-500">No messes yet.</p>}
        {shown ? (
          <MessOverviewPanel data={shown} onCustomize={() => setCustomizing(true)} />
        ) : (
          id && !error && <p className="text-sm text-gray-500">Loading {selected?.name ?? 'mess'}...</p>
        )}
      </div>
      {customizing && shown && (
        <CustomizeBusinessModal
          biz={{ id: shown.business.id, name: shown.business.name }}
          onClose={() => {
            setCustomizing(false)
            loadOverview(shown.business.id)
          }}
        />
      )}
    </div>
  )
}
