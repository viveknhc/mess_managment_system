import { useCallback, useEffect, useState } from 'react'
import type { OnlinePaymentInfo, PortalSubscription, UpiPayStart } from './portalApi'
import { portalApi } from './portalApi'
import { UpiPayModal } from './UpiPayModal'
import { payOnline } from '../../utils/razorpay'
import { notify } from '../../utils/notify'

const formatINR = (v: string) => `₹${Number(v).toLocaleString('en-IN')}`

/** "₹X due · Pay" cards for unpaid balances the customer can settle online
 * (a renewal waiting for payment, or a part-paid plan). The mess decides how: Razorpay
 * (automatic) or its UPI ID (the mess confirms). Renders nothing if the mess has neither. */
export function PaymentDueList({ subs, onChange }: { subs: PortalSubscription[]; onChange: () => void }) {
  const [info, setInfo] = useState<OnlinePaymentInfo | null>(null)
  const [payingId, setPayingId] = useState<string | null>(null)
  const [upi, setUpi] = useState<{ subId: string; start: UpiPayStart } | null>(null)

  const loadInfo = useCallback(() => {
    portalApi.onlinePayment().then(({ data }) => setInfo(data)).catch(() => {})
  }, [])

  useEffect(() => { loadInfo() }, [loadInfo])

  async function handlePay(sub: PortalSubscription) {
    setPayingId(sub.id)
    const started = await portalApi.startPayment(sub.id)
    if (!started.ok) {
      setPayingId(null)
      notify.error(started.error)
      return
    }
    const start = started.data
    if (start.status === 'UPI') {
      setPayingId(null)
      setUpi({ subId: sub.id, start })
      return
    }
    const res = await payOnline(
      async () => ({ ok: true, data: start }),
      (result) => portalApi.verifyPayment(sub.id, result),
    )
    setPayingId(null)
    if (res.outcome === 'paid') notify.success('Payment received', 'Thank you!')
    if (res.outcome === 'error') notify.error(res.error)
    onChange()
  }

  const payable = info?.enabled
    ? subs.filter((s) => ['PENDING', 'ACTIVE', 'PAUSED'].includes(s.status) && Number(s.pending_amount) > 0)
    : []
  const claimFor = (subId: string, status: 'PENDING' | 'REJECTED') =>
    info?.upi_claims.find((c) => c.subscription === subId && c.status === status)

  return (
    <>
      {payable.map((s) => {
        const waiting = claimFor(s.id, 'PENDING')
        const rejected = waiting ? undefined : claimFor(s.id, 'REJECTED')
        return (
          <div key={s.id} className={`rounded-xl border p-4 ${waiting ? 'border-amber-200 bg-amber-50' : 'border-orange-200 bg-orange-50'}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">{formatINR(s.pending_amount)} due · {s.plan_name}</p>
                <p className="text-xs text-gray-600">
                  {waiting
                    ? `You sent ${formatINR(waiting.amount)} by UPI. Waiting for the mess to confirm it.`
                    : s.status === 'PENDING' ? 'Pay to start your meals.' : `${s.start_date} → ${s.end_date}`}
                </p>
              </div>
              {!waiting && (
                <button
                  onClick={() => handlePay(s)}
                  disabled={payingId !== null}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {payingId === s.id ? 'Opening…' : `Pay ${formatINR(s.pending_amount)}`}
                </button>
              )}
            </div>
            {rejected && (
              <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
                Your UPI payment of {formatINR(rejected.amount)} wasn't confirmed: {rejected.reject_reason}
              </p>
            )}
          </div>
        )
      })}

      {upi && (
        <UpiPayModal
          subId={upi.subId}
          start={upi.start}
          onClose={() => setUpi(null)}
          onClaimed={() => { setUpi(null); loadInfo(); onChange() }}
        />
      )}
    </>
  )
}
