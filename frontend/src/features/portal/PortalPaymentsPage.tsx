import { useEffect, useState } from 'react'
import { DataTable, type Column } from '../../components/ui/DataTable'
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

const columns: Column<PortalPayment>[] = [
  {
    key: 'payment_date',
    header: 'Date',
    sortable: true,
    render: (p) => <span className="whitespace-nowrap text-gray-700">{p.payment_date}</span>,
  },
  {
    key: 'subscription_plan',
    header: 'Plan',
    sortable: true,
    render: (p) => <span className="text-gray-900">{p.subscription_plan || '—'}</span>,
  },
  {
    key: 'method',
    header: 'Method',
    sortable: true,
    sortValue: (p) => METHOD_LABELS[p.method] ?? p.method,
    render: (p) => <span className="whitespace-nowrap text-gray-700">{METHOD_LABELS[p.method] ?? p.method}</span>,
  },
  {
    key: 'transaction_reference',
    header: 'Reference',
    sortable: true,
    render: (p) =>
      p.transaction_reference ? (
        <span className="block max-w-40 truncate text-xs text-gray-400" title={p.transaction_reference}>
          {p.transaction_reference}
        </span>
      ) : (
        <span className="text-gray-300">—</span>
      ),
  },
  {
    key: 'amount',
    header: 'Amount',
    sortable: true,
    align: 'right',
    render: (p) => (
      <span className="font-bold whitespace-nowrap text-gray-900">₹{Number(p.amount).toLocaleString('en-IN')}</span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (p) => (
      <span
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
          p.status === 'PAID' ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-600'
        }`}
      >
        {p.status}
      </span>
    ),
  },
]

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

      <DataTable
        columns={columns}
        rows={payments}
        rowKey={(p) => p.id}
        defaultSort={{ key: 'payment_date', dir: 'desc' }}
        emptyMessage="No payments yet"
      />
    </div>
  )
}
