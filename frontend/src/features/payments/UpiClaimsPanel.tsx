import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'
import { confirmDialog, promptDialog } from '../../components/ui/dialog'
import { notify } from '../../utils/notify'

interface UpiClaim {
  id: string
  customer_name: string
  customer_phone: string
  subscription_plan: string
  subscription_status: string
  amount: string
  utr: string
  created_at: string
}

const formatINR = (v: string) => `₹${Number(v).toLocaleString('en-IN')}`
const formatWhen = (iso: string) =>
  new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })

const REJECT_REASONS = ['Not received in my account', 'Wrong amount received', 'Paid in cash instead']

/** UPI payments customers say they made, waiting for the owner to check their account.
 * Renders nothing when there are none. */
export function UpiClaimsPanel({ onReviewed }: { onReviewed: () => void }) {
  const [claims, setClaims] = useState<UpiClaim[]>([])
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(() => {
    apiClient
      .get('/upi-claims/', { params: { status: 'PENDING', ordering: 'created_at', page_size: 100 } })
      .then(({ data }) => setClaims(data.results))
      .catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  async function review(claim: UpiClaim, action: 'confirm' | 'reject') {
    let body: { reason?: string } = {}
    if (action === 'confirm') {
      const ok = await confirmDialog({
        title: `Confirm ${formatINR(claim.amount)} from ${claim.customer_name}?`,
        message: (
          <>
            Only confirm if this money is in your bank or UPI app
            {claim.utr ? <> (UPI ref <span className="font-mono">{claim.utr}</span>)</> : null}. It is then recorded as
            paid{claim.subscription_status === 'PENDING' ? ' and their meals start' : ''}.
          </>
        ),
        confirmText: 'Yes, I received it',
        tone: 'success',
      })
      if (!ok) return
    } else {
      const reason = await promptDialog({
        title: `Reject ${formatINR(claim.amount)} from ${claim.customer_name}?`,
        message: 'Nothing is recorded. The customer sees your reason and can pay again.',
        options: REJECT_REASONS,
        placeholder: 'Reason (shown to the customer)',
        required: false,
        confirmText: 'Reject',
        tone: 'danger',
      })
      if (reason === null) return
      body = { reason }
    }

    setBusyId(claim.id)
    try {
      await apiClient.post(`/upi-claims/${claim.id}/${action}/`, body)
      notify.success(action === 'confirm' ? 'Payment recorded' : 'Payment rejected')
      onReviewed()
    } catch (e) {
      notify.error(e, 'Could not update the payment')
    } finally {
      setBusyId(null)
      load()
    }
  }

  if (claims.length === 0) return null

  return (
    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <h2 className="text-sm font-semibold text-amber-900">
        UPI payments to confirm ({claims.length})
      </h2>
      <p className="mt-0.5 text-xs text-amber-800">
        These customers say they paid your UPI ID. Check your bank or UPI app, then confirm or reject.
      </p>
      <ul className="mt-3 divide-y divide-amber-100 overflow-hidden rounded-lg border border-amber-100 bg-white">
        {claims.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 p-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900">
                {formatINR(c.amount)} · {c.customer_name}
                <span className="font-normal text-gray-500"> · {c.subscription_plan}</span>
              </p>
              <p className="text-xs text-gray-500">
                {formatWhen(c.created_at)}
                {c.customer_phone ? ` · ${c.customer_phone}` : ''}
                {c.utr ? <> · UPI ref <span className="font-mono">{c.utr}</span></> : ' · no reference given'}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button type="button" onClick={() => review(c, 'reject')} disabled={busyId !== null}
                className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                Reject
              </button>
              <button type="button" onClick={() => review(c, 'confirm')} disabled={busyId !== null}
                className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
                {busyId === c.id ? 'Saving…' : 'Confirm'}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
