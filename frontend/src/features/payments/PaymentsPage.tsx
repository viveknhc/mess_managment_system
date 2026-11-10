import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { RecordPaymentForm } from './RecordPaymentForm'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

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

const columns: Column<Payment>[] = [
  { key: 'payment_date', header: 'Date', sortable: true, className: 'whitespace-nowrap text-gray-600', render: (p) => p.payment_date },
  { key: 'customer__name', header: 'Customer', sortable: true, className: 'font-medium text-gray-900', render: (p) => p.customer_name },
  { key: 'subscription__plan__name', header: 'Plan', sortable: true, className: 'text-gray-600', render: (p) => p.subscription_plan },
  {
    key: 'method',
    header: 'Method',
    sortable: true,
    render: (p) => (
      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
        {METHOD_LABELS[p.method] || p.method}
      </span>
    ),
  },
  {
    key: 'transaction_reference',
    header: 'Reference',
    className: 'font-mono text-xs text-gray-500',
    render: (p) => p.transaction_reference || '—',
  },
  {
    key: 'amount',
    header: 'Amount',
    sortable: true,
    align: 'right',
    className: 'font-semibold text-gray-900',
    render: (p) => `₹${Number(p.amount).toLocaleString('en-IN')}`,
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (p) => (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        p.status === 'PAID' ? 'bg-green-50 text-green-700' :
        p.status === 'FAILED' ? 'bg-red-50 text-red-700' :
        'bg-gray-100 text-gray-600'
      }`}>
        {p.status}
      </span>
    ),
  },
]

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const table = useServerTable()
  const { params: tableParams } = table
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [payRes, sumRes] = await Promise.all([
        apiClient.get('/payments/', { params: tableParams }),
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
  }, [tableParams, canWrite])

  useEffect(() => { fetchData() }, [fetchData])

  if (loading && payments.length === 0 && !summary) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Customer Payments</h1>
          <p className="mt-1 text-sm text-gray-500">
            Money your customers pay you for their meal plans. What you pay MessDeck is under{' '}
            <Link to="/app/billing" className="text-blue-600 underline">MessDeck Billing</Link>.
          </p>
        </div>
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

      <DataTable
        columns={columns}
        rows={payments}
        rowKey={(p) => p.id}
        loading={loading}
        emptyMessage="No payments recorded yet"
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

      {showForm && (
        <RecordPaymentForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchData() }}
        />
      )}
    </div>
  )
}
