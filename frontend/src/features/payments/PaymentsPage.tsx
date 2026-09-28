import { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { RecordPaymentForm } from './RecordPaymentForm'

interface Payment {
  id: string
  subscription: string
  customer: string
  customer_name: string
  subscription_plan: string
  amount: string
  method: string
  transaction_reference: string
  payment_date: string
  status: string
  notes: string
}

interface Summary {
  today: number
  month: number
  pending: number
}

const METHOD_LABELS: Record<string, string> = {
  CASH: 'Cash', UPI: 'UPI', BANK_TRANSFER: 'Bank', CARD: 'Card', ONLINE: 'Online', OTHER: 'Other',
}

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [payRes, sumRes] = await Promise.all([
        apiClient.get('/payments/', { params: { page: String(page) } }),
        canWrite ? apiClient.get('/payments/summary/') : Promise.resolve({ data: null }),
      ])
      setPayments(payRes.data.results)
      setCount(payRes.data.count)
      if (sumRes.data) setSummary(sumRes.data)
    } catch {
      // empty state
    } finally {
      setLoading(false)
    }
  }, [page, canWrite])

  useEffect(() => { fetchData() }, [fetchData])

  const totalPages = Math.ceil(count / 20)

  if (loading && payments.length === 0) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Payments</h1>
        {canWrite && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Record Payment
          </button>
        )}
      </div>

      {/* Summary cards (PAY-11) */}
      {summary && (
        <div className="mb-6 grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase">Today</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">₹{Number(summary.today).toLocaleString('en-IN')}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase">This Month</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">₹{Number(summary.month).toLocaleString('en-IN')}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-red-500 uppercase">Pending</p>
            <p className="mt-1 text-2xl font-bold text-red-600">₹{Number(summary.pending).toLocaleString('en-IN')}</p>
          </div>
        </div>
      )}

      {payments.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No payments recorded yet</p>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="px-4 py-3 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">Plan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">Method</th>
                  <th className="px-4 py-3 text-right text-xs font-medium tracking-wide text-gray-500 uppercase">Amount</th>
                  <th className="px-4 py-3 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {payments.map((p) => (
                  <tr key={p.id}>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.payment_date}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{p.customer_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.subscription_plan}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        {METHOD_LABELS[p.method] || p.method}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">
                      ₹{Number(p.amount).toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        p.status === 'PAID' ? 'bg-green-50 text-green-700' :
                        p.status === 'FAILED' ? 'bg-red-50 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">Previous</button>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">Next</button>
              </div>
            </div>
          )}
        </>
      )}

      {showForm && (
        <RecordPaymentForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchData() }}
        />
      )}
    </div>
  )
}
