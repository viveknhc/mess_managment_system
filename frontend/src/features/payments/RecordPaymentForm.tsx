import { useState, useEffect, type FormEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { notify } from '../../utils/notify'
import { fetchAll } from '../../services/fetchAll'

interface Sub {
  id: string
  customer_name: string
  plan_name: string
  pending_amount: string
  status: string
}

const METHODS = [
  { value: 'CASH', label: 'Cash' },
  { value: 'UPI', label: 'UPI' },
  { value: 'BANK_TRANSFER', label: 'Bank Transfer' },
  { value: 'CARD', label: 'Card' },
  { value: 'ONLINE', label: 'Online' },
  { value: 'OTHER', label: 'Other' },
]

interface Props {
  onClose: () => void
  onSaved: () => void
}

export function RecordPaymentForm({ onClose, onSaved }: Props) {
  const [subs, setSubs] = useState<Sub[]>([])
  const [subId, setSubId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('CASH')
  const [reference, setReference] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    // Every unpaid subscription: PENDING ones, plus ACTIVE/PAUSED ones still owing
    // (e.g. a part payment, or an extra added mid-month).
    const byName = { ordering: 'customer__name' }
    let stale = false
    Promise.all([
      fetchAll<Sub>('/subscriptions/', { ...byName, status: 'PENDING' }),
      fetchAll<Sub>('/subscriptions/', { ...byName, status: 'ACTIVE' }),
      fetchAll<Sub>('/subscriptions/', { ...byName, status: 'PAUSED' }),
    ])
      .then(([pending, active, paused]) => {
        if (stale) return
        const all = [...pending, ...[...active, ...paused].filter((s) => Number(s.pending_amount) > 0)]
        setSubs(all)
        // Default to the first one, but never override a subscription the user already picked:
        // a late response switching the selection would record the payment for the wrong customer.
        setSubId((cur) => (cur && all.some((s) => s.id === cur) ? cur : (all[0]?.id ?? '')))
      })
      .catch((err) => { if (!stale) notify.error(err, "Couldn't load subscriptions") })
    return () => { stale = true }
  }, [])

  const selectedSub = subs.find((s) => s.id === subId)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await apiClient.post('/payments/', {
        subscription: subId,
        amount,
        method,
        transaction_reference: reference,
        notes,
      })
      notify.success(
        `Payment of ₹${Number(amount).toLocaleString('en-IN')} recorded`,
        selectedSub ? `${selectedSub.customer_name} — ${selectedSub.plan_name}` : undefined,
      )
      onSaved()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || 'Failed to record payment'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4">
      <div className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 shadow-lg sm:rounded-xl sm:p-6">
        <h2 className="mb-4 text-lg font-bold text-gray-900">Record Payment</h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="subscription" className="mb-1 block text-sm font-medium text-gray-700">Subscription *</label>
            <select id="subscription" value={subId} onChange={(e) => setSubId(e.target.value)} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none">
              {subs.length === 0 && <option value="">No subscriptions with pending amounts</option>}
              {subs.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.customer_name} — {s.plan_name} (₹{Number(s.pending_amount).toLocaleString('en-IN')} pending)
                </option>
              ))}
            </select>
          </div>

          {selectedSub && (
            <div className="rounded-lg bg-gray-50 p-3 text-sm">
              <span className="font-medium">Pending: </span>
              <span className="text-red-600 font-bold">₹{Number(selectedSub.pending_amount).toLocaleString('en-IN')}</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="amount" className="mb-1 block text-sm font-medium text-gray-700">Amount (₹) *</label>
              <input id="amount" type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label htmlFor="method" className="mb-1 block text-sm font-medium text-gray-700">Method *</label>
              <select id="method" value={method} onChange={(e) => setMethod(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none">
                {METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="reference" className="mb-1 block text-sm font-medium text-gray-700">Transaction Reference</label>
            <input id="reference" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="UPI ID, cheque no., etc."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
          </div>

          <div>
            <label htmlFor="notes" className="mb-1 block text-sm font-medium text-gray-700">Notes</label>
            <input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={saving || !subId}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Recording...' : 'Record Payment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
