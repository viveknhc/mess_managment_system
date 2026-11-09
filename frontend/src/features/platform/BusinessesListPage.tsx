import { useState, useEffect, useCallback, useMemo } from 'react'
import { platformApi, type CreateBusinessInput, type ManualPaymentMethod, type PlatformBusiness } from './platformApi'
import { STATUS_COLOR, STATUS_LABEL, dayBefore, formatDate, rupees } from './billingFormat'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

const CANCELLABLE = ['PENDING', 'TRIAL', 'ACTIVE', 'PAST_DUE']
const inputClass = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm'

function statusBadge(biz: PlatformBusiness) {
  if (!biz.saas_status) return <span className="text-gray-400">—</span>
  return (
    <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[biz.saas_status]}`}>
      {STATUS_LABEL[biz.saas_status]}
    </span>
  )
}

const emptyBusiness: CreateBusinessInput = {
  business_name: '',
  phone: '',
  email: '',
  address: '',
  owner_username: '',
  owner_password: '',
  owner_name: '',
  owner_email: '',
  owner_phone: '',
}

function AddBusinessModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<CreateBusinessInput>(emptyBusiness)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const set = (key: keyof CreateBusinessInput) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    const result = await platformApi.createBusiness(form)
    setSaving(false)
    if (!result.ok) {
      setError(result.error)
      return
    }
    onCreated()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="max-h-full w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-bold text-gray-900">Add Business</h2>
        <p className="mt-1 text-sm text-gray-500">
          The business starts with its first payment (setup fee + first month) due. Default meals are added.
        </p>
        {error && <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <input required placeholder="Business name" value={form.business_name} onChange={set('business_name')} className={inputClass} />
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Business phone" value={form.phone} onChange={set('phone')} className={inputClass} />
            <input type="email" placeholder="Business email" value={form.email} onChange={set('email')} className={inputClass} />
          </div>
          <input placeholder="Address" value={form.address} onChange={set('address')} className={inputClass} />
          <p className="pt-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Owner login</p>
          <input placeholder="Owner name" value={form.owner_name} onChange={set('owner_name')} className={inputClass} />
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Owner phone" value={form.owner_phone} onChange={set('owner_phone')} className={inputClass} />
            <input type="email" placeholder="Owner email" value={form.owner_email} onChange={set('owner_email')} className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input required placeholder="Owner username" value={form.owner_username} onChange={set('owner_username')} className={inputClass} />
            <input required type="password" minLength={8} placeholder="Owner password (min 8)" value={form.owner_password} onChange={set('owner_password')} className={inputClass} />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={saving} className="flex-1 rounded-lg bg-purple-600 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
              {saving ? 'Creating...' : 'Create Business'}
            </button>
            <button type="button" onClick={onClose} className="flex-1 rounded-lg border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function RecordPaymentModal({ biz, onClose, onRecorded }: { biz: PlatformBusiness; onClose: () => void; onRecorded: () => void }) {
  const due = biz.amount_due
  const [amount, setAmount] = useState(due?.total ?? '')
  const [method, setMethod] = useState<ManualPaymentMethod>('UPI')
  const [reference, setReference] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    const result = await platformApi.recordPayment(biz.id, { amount, method, reference })
    setSaving(false)
    if (!result.ok) {
      setError(result.error)
      return
    }
    onRecorded()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-bold text-gray-900">Record Payment</h2>
        <p className="mt-1 text-sm text-gray-500">{biz.name}</p>
        {due && (
          <dl className="mt-4 space-y-1 rounded-lg bg-gray-50 p-3 text-sm">
            {Number(due.setup_fee) > 0 && (
              <div className="flex justify-between"><dt className="text-gray-600">Setup fee</dt><dd>{rupees(due.setup_fee)}</dd></div>
            )}
            {Number(due.reactivation_fee) > 0 && (
              <div className="flex justify-between"><dt className="text-gray-600">Reactivation fee</dt><dd>{rupees(due.reactivation_fee)}</dd></div>
            )}
            <div className="flex justify-between"><dt className="text-gray-600">Monthly fee</dt><dd>{rupees(due.monthly_fee)}</dd></div>
            <div className="flex justify-between border-t border-gray-200 pt-1 font-semibold"><dt>Amount due</dt><dd>{rupees(due.total)}</dd></div>
          </dl>
        )}
        {error && <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <label className="block text-sm text-gray-700">
            Amount received
            <input required type="number" step="0.01" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} className={`mt-1 ${inputClass}`} />
          </label>
          <label className="block text-sm text-gray-700">
            Method
            <select value={method} onChange={(e) => setMethod(e.target.value as ManualPaymentMethod)} className={`mt-1 ${inputClass}`}>
              <option value="UPI">UPI</option>
              <option value="CASH">Cash</option>
              <option value="BANK_TRANSFER">Bank transfer</option>
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            Reference (optional)
            <input placeholder="UPI / bank reference" value={reference} onChange={(e) => setReference(e.target.value)} className={`mt-1 ${inputClass}`} />
          </label>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={saving} className="flex-1 rounded-lg bg-purple-600 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Record Payment'}
            </button>
            <button type="button" onClick={onClose} className="flex-1 rounded-lg border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function BusinessesListPage() {
  const [businesses, setBusinesses] = useState<PlatformBusiness[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [paying, setPaying] = useState<PlatformBusiness | null>(null)
  const [actionError, setActionError] = useState('')
  const table = useServerTable()
  const { params: tableParams } = table

  const fetchBusinesses = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.getBusinesses(tableParams)
      setBusinesses(data.results)
      setCount(data.count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchBusinesses()
  }, [fetchBusinesses])

  const columns = useMemo<Column<PlatformBusiness>[]>(() => {
    async function handleSuspend(id: string) {
      if (!confirm('Suspend this business?')) return
      setActionError('')
      const result = await platformApi.suspendBusiness(id)
      if (result.ok) fetchBusinesses()
      else setActionError(result.error)
    }

    async function handleReactivate(id: string) {
      if (!confirm('Restore access without a payment? To bring back a lapsed business, use Record Payment instead.')) return
      setActionError('')
      const result = await platformApi.reactivateBusiness(id)
      // 400 when money is owed (setup unpaid / reactivation fee) — the message says to record a payment instead.
      if (result.ok) fetchBusinesses()
      else setActionError(result.error)
    }

    async function handleCancel(biz: PlatformBusiness) {
      if (!confirm(`Cancel the monthly plan for ${biz.name}? They keep access until the paid month ends.`)) return
      setActionError('')
      const result = await platformApi.cancelBusiness(biz.id)
      if (result.ok) fetchBusinesses()
      else setActionError(result.error)
    }

    return [
      {
        key: 'name',
        header: 'Business',
        sortable: true,
        render: (biz) => (
          <>
            <p className="font-medium text-gray-900">{biz.name}</p>
            <p className="text-xs text-gray-500">{biz.email || biz.phone}</p>
          </>
        ),
      },
      {
        key: 'owner',
        header: 'Owner',
        render: (biz) => (
          <>
            <p className="text-gray-700">{biz.owner_name || '—'}</p>
            <p className="text-xs text-gray-500">{biz.owner_email}</p>
          </>
        ),
      },
      {
        key: 'saas_subscription__status',
        header: 'Status',
        sortable: true,
        render: (biz) => statusBadge(biz),
      },
      {
        key: 'saas_subscription__plan__name',
        header: 'Plan',
        sortable: true,
        className: 'text-gray-700',
        render: (biz) => biz.plan_name || '—',
      },
      {
        key: 'saas_subscription__current_period_end',
        header: 'Paid Until',
        sortable: true,
        className: 'whitespace-nowrap text-xs text-gray-500',
        render: (biz) => (biz.paid_until ? formatDate(dayBefore(biz.paid_until)) : '—'),
      },
      {
        key: 'amount_due',
        header: 'Next Payment',
        className: 'whitespace-nowrap text-xs',
        render: (biz) =>
          biz.amount_due ? (
            <>
              <p className="font-medium text-gray-900">{rupees(biz.amount_due.total)}</p>
              <p className="text-gray-500">due {formatDate(biz.amount_due.due_date)}</p>
            </>
          ) : (
            '—'
          ),
      },
      {
        key: 'customer_count',
        header: 'Customers',
        align: 'right',
        className: 'text-gray-700',
        render: (biz) => biz.customer_count,
      },
      {
        key: 'staff_count',
        header: 'Staff',
        align: 'right',
        className: 'text-gray-700',
        render: (biz) => biz.staff_count,
      },
      {
        key: 'created_at',
        header: 'Created',
        sortable: true,
        className: 'whitespace-nowrap text-xs text-gray-500',
        render: (biz) => formatDate(biz.created_at),
      },
      {
        key: 'actions',
        header: 'Actions',
        render: (biz) => (
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setPaying(biz)}
              className="whitespace-nowrap rounded bg-purple-100 px-2.5 py-1 text-xs font-medium text-purple-700 hover:bg-purple-200"
            >
              Record Payment
            </button>
            {biz.status === 'SUSPENDED' ? (
              <button
                onClick={() => handleReactivate(biz.id)}
                className="rounded bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-200"
              >
                Reactivate
              </button>
            ) : (
              <button
                onClick={() => handleSuspend(biz.id)}
                className="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
              >
                Suspend
              </button>
            )}
            {biz.saas_status && CANCELLABLE.includes(biz.saas_status) && (
              <button
                onClick={() => handleCancel(biz)}
                className="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
              >
                Cancel Plan
              </button>
            )}
          </div>
        ),
      },
    ]
  }, [fetchBusinesses])

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Businesses ({count})</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
        >
          Add Business
        </button>
      </div>

      {actionError && (
        <div role="alert" className="mb-4 flex items-start justify-between gap-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <span>{actionError}</span>
          <button onClick={() => setActionError('')} className="text-red-500 hover:text-red-700" aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}

      <DataTable
        columns={columns}
        rows={businesses}
        rowKey={(biz) => biz.id}
        loading={loading}
        emptyMessage="No businesses yet."
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

      {showAdd && (
        <AddBusinessModal
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false)
            fetchBusinesses()
          }}
        />
      )}
      {paying && (
        <RecordPaymentModal
          biz={paying}
          onClose={() => setPaying(null)}
          onRecorded={() => {
            setPaying(null)
            fetchBusinesses()
          }}
        />
      )}
    </div>
  )
}
