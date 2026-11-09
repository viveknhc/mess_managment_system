import { useState, useEffect, useCallback } from 'react'
import { billingApi, type BillingData, type SaasSubscription } from './platformApi'
import { STATUS_COLOR, STATUS_LABEL, METHOD_LABEL, dayBefore, formatDate, rupees } from './billingFormat'
import { useAuthStore } from '../../store/authStore'
import { SUPPORT_EMAIL, supportEmailLink, whatsappLink } from '../../config/support'

const CANCELLABLE = ['PENDING', 'TRIAL', 'ACTIVE', 'PAST_DUE']

/** One-line explanation of where the business stands, per the monthly plan terms. */
function statusMessage(sub: SaasSubscription) {
  const due = sub.amount_due
  const end = sub.current_period_end
  switch (sub.status) {
    case 'PENDING':
    case 'TRIAL':
      return `Your first payment of ${rupees(due.total)} (${rupees(due.setup_fee)} setup + ${rupees(due.monthly_fee)} first month) is due.`
    case 'ACTIVE':
      return end ? `You're paid until ${formatDate(dayBefore(end))}. Next payment of ${rupees(due.total)} is due on ${formatDate(end)}.` : ''
    case 'PAST_DUE':
      return `${rupees(due.total)} was due on ${formatDate(end)}. Please pay before ${formatDate(sub.grace_ends)} to avoid suspension.`
    case 'CANCELLED':
      return sub.business_status === 'SUSPENDED' || !end
        ? `Your plan has ended. To come back, pay ${rupees(due.total)}.`
        : `You cancelled your plan. You can keep using MessDeck until ${formatDate(dayBefore(end))}.`
    case 'SUSPENDED':
      return `Your account is suspended. Pay ${rupees(due.total)} to restore access.`
  }
}

export function BillingPage() {
  const role = useAuthStore((s) => s.user?.role)
  const [billing, setBilling] = useState<BillingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cancelling, setCancelling] = useState(false)

  const fetchBilling = useCallback(async () => {
    setLoading(true)
    try {
      setBilling(await billingApi.getBilling())
    } catch {
      setError('Failed to load billing information.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBilling()
  }, [fetchBilling])

  if (loading && !billing) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!billing) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error || 'No billing information found.'}</div>
      </div>
    )
  }

  const sub = billing.subscription
  const plan = sub.plan_details
  const due = sub.amount_due
  const canCancel = role === 'OWNER' && CANCELLABLE.includes(sub.status)

  async function handleCancel() {
    const until = sub.current_period_end ? `You can keep using MessDeck until ${formatDate(dayBefore(sub.current_period_end))}. ` : ''
    const fee = plan && Number(plan.reactivation_fee) > 0
      ? `If you come back more than 3 months after that, a ${rupees(plan.reactivation_fee)} reactivation fee applies.`
      : ''
    if (!confirm(`Cancel the monthly plan?\n\n${until}The setup fee is non-refundable. ${fee}`)) return
    setCancelling(true)
    setError('')
    const result = await billingApi.cancel()
    if (!result.ok) setError(result.error)
    await fetchBilling()
    setCancelling(false)
  }

  const payMessage = `Hi, I've paid ${rupees(due.total)} for ${sub.business_name} (MessDeck). Payment reference: `

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Billing</h1>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {/* Current status */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm text-gray-500">Plan</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {sub.plan_name || 'Monthly Plan'}
              {plan && <span className="ml-2 text-sm font-normal text-gray-500">{rupees(plan.price_monthly)}/month</span>}
            </p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_COLOR[sub.status]}`}>
            {STATUS_LABEL[sub.status]}
          </span>
        </div>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-gray-500">Paid until</dt>
            <dd className="mt-0.5 font-medium text-gray-900">
              {sub.current_period_end ? formatDate(dayBefore(sub.current_period_end)) : 'Not paid yet'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Amount due</dt>
            <dd className="mt-0.5 font-medium text-gray-900">{rupees(due.total)} on {formatDate(due.due_date)}</dd>
          </div>
          {sub.grace_ends && (
            <div>
              <dt className="text-gray-500">Grace period ends</dt>
              <dd className="mt-0.5 font-medium text-red-700">{formatDate(sub.grace_ends)}</dd>
            </div>
          )}
        </dl>
        <p className="mt-4 text-sm text-gray-700">{statusMessage(sub)}</p>
      </div>

      {/* Amount due */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-800">
          {sub.status === 'CANCELLED' && sub.business_status !== 'SUSPENDED' ? 'To continue after your plan ends' : 'Next payment'}
        </h2>
        <dl className="mt-4 space-y-2 text-sm">
          {Number(due.setup_fee) > 0 && (
            <div className="flex justify-between"><dt className="text-gray-600">One-time setup fee</dt><dd className="text-gray-900">{rupees(due.setup_fee)}</dd></div>
          )}
          {Number(due.reactivation_fee) > 0 && (
            <div className="flex justify-between"><dt className="text-gray-600">Reactivation fee (away more than 3 months)</dt><dd className="text-gray-900">{rupees(due.reactivation_fee)}</dd></div>
          )}
          <div className="flex justify-between"><dt className="text-gray-600">Monthly fee</dt><dd className="text-gray-900">{rupees(due.monthly_fee)}</dd></div>
          <div className="flex justify-between border-t border-gray-100 pt-2 font-semibold">
            <dt className="text-gray-900">Total</dt><dd className="text-gray-900">{rupees(due.total)}</dd>
          </div>
          <div className="flex justify-between"><dt className="text-gray-600">Due on</dt><dd className="text-gray-900">{formatDate(due.due_date)}</dd></div>
        </dl>
        <div className="mt-5 rounded-lg bg-gray-50 p-4 text-sm text-gray-700">
          <p className="font-medium text-gray-900">How to pay</p>
          <p className="mt-1">Pay by UPI or cash and message us on WhatsApp with the payment reference. We'll update your account the same day.</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <a
              href={whatsappLink(payMessage)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              Send payment details on WhatsApp
            </a>
            <span className="text-gray-500">
              or email{' '}
              <a href={supportEmailLink(`MessDeck payment — ${sub.business_name}`)} className="text-blue-600 underline">
                {SUPPORT_EMAIL}
              </a>
            </span>
          </div>
        </div>
      </div>

      {/* Payment history */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Payment history</h2>
        {billing.payments.length === 0 ? (
          <p className="text-sm text-gray-500">No payments yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">Covers</th>
                  <th className="py-2 pr-4">Method</th>
                  <th className="py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {billing.payments.map((p) => (
                  <tr key={p.id} className="border-b border-gray-100 last:border-0">
                    <td className="py-2 pr-4 whitespace-nowrap">{formatDate(p.created_at)}</td>
                    <td className="py-2 pr-4 whitespace-nowrap text-gray-600">
                      {p.period_start && p.period_end ? `${formatDate(p.period_start)} – ${formatDate(dayBefore(p.period_end))}` : '—'}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">{METHOD_LABEL[p.method] ?? p.method}</td>
                    <td className="py-2 text-right whitespace-nowrap">
                      <span className="font-medium text-gray-900">{rupees(p.amount)}</span>
                      {(Number(p.setup_fee) > 0 || Number(p.reactivation_fee) > 0) && (
                        <span className="block text-xs text-gray-500">
                          {Number(p.setup_fee) > 0 && `incl. ${rupees(p.setup_fee)} setup`}
                          {Number(p.reactivation_fee) > 0 && `incl. ${rupees(p.reactivation_fee)} reactivation`}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Terms */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-800">Terms</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-gray-600">
          <li>Setup fee is non-refundable</li>
          <li>Cancel the monthly plan any time. You keep access until the end of the month you paid for.</li>
          <li>If a payment is more than 7 days late, the account is suspended until it's paid.</li>
          {plan && Number(plan.reactivation_fee) > 0 && (
            <li>If you cancel and come back after more than 3 months, a {rupees(plan.reactivation_fee)} reactivation fee applies</li>
          )}
          <li>Your data is private to your business</li>
        </ul>
        {canCancel && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="mt-5 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            {cancelling ? 'Cancelling...' : 'Cancel monthly plan'}
          </button>
        )}
      </div>
    </div>
  )
}
