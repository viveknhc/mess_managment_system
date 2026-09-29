import { useEffect, useState } from 'react'
import type { PortalPayment } from './portalApi'
import { portalApi } from './portalApi'

const METHOD_LABELS: Record<string, string> = {
  CASH: 'Cash',
  UPI: 'UPI',
  BANK_TRANSFER: 'Bank Transfer',
  CARD: 'Card',
  ONLINE: 'Online',
  OTHER: 'Other',
}

export function PortalPaymentsPage() {
  const [payments, setPayments] = useState<PortalPayment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    portalApi
      .payments()
      .then((res) => setPayments(res.data))
      .catch(() => setPayments([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900 sm:text-2xl">Payments</h1>

      {payments.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-500">No payments yet</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {payments.map((p) => (
            <li key={p.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-lg font-bold text-gray-900">₹{p.amount}</p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {p.payment_date} · {METHOD_LABELS[p.method] ?? p.method}
                    {p.subscription_plan ? ` · ${p.subscription_plan}` : ''}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    p.status === 'PAID' ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {p.status}
                </span>
              </div>
              {p.transaction_reference && (
                <p className="mt-2 truncate border-t border-gray-100 pt-2 text-xs text-gray-400">
                  Ref: {p.transaction_reference}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
