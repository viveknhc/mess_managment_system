import { useEffect, useState } from 'react'
import type { PortalSubscription } from './portalApi'
import { portalApi } from './portalApi'
import { payOnline } from '../../utils/razorpay'
import { notify } from '../../utils/notify'

const formatINR = (v: string) => `₹${Number(v).toLocaleString('en-IN')}`

/** "₹X due · Pay" cards for unpaid balances the customer can settle online
 * (a renewal waiting for payment, or a part-paid plan). Renders nothing if the mess has no online payments. */
export function PaymentDueList({ subs, onChange }: { subs: PortalSubscription[]; onChange: () => void }) {
  const [onlineEnabled, setOnlineEnabled] = useState(false)
  const [payingId, setPayingId] = useState<string | null>(null)

  useEffect(() => {
    portalApi.onlinePayment().then(({ data }) => setOnlineEnabled(data.enabled)).catch(() => {})
  }, [])

  async function handlePay(sub: PortalSubscription) {
    setPayingId(sub.id)
    const res = await payOnline(
      () => portalApi.startPayment(sub.id),
      (result) => portalApi.verifyPayment(sub.id, result),
    )
    setPayingId(null)
    if (res.outcome === 'paid') notify.success('Payment received', 'Thank you!')
    if (res.outcome === 'error') notify.error(res.error)
    onChange()
  }

  const payable = onlineEnabled
    ? subs.filter((s) => ['PENDING', 'ACTIVE', 'PAUSED'].includes(s.status) && Number(s.pending_amount) > 0)
    : []

  return (
    <>
      {payable.map((s) => (
        <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-orange-200 bg-orange-50 p-4">
          <div>
            <p className="text-sm font-semibold text-gray-900">{formatINR(s.pending_amount)} due · {s.plan_name}</p>
            <p className="text-xs text-gray-600">
              {s.status === 'PENDING' ? 'Pay to start your meals.' : `${s.start_date} → ${s.end_date}`}
            </p>
          </div>
          <button
            onClick={() => handlePay(s)}
            disabled={payingId !== null}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {payingId === s.id ? 'Opening…' : `Pay ${formatINR(s.pending_amount)}`}
          </button>
        </div>
      ))}
    </>
  )
}
