import { useState, useEffect, useCallback } from 'react'
import { platformApi, type SaasPayment } from './platformApi'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'
import { METHOD_LABEL } from './billingFormat'

const columns: Column<SaasPayment>[] = [
  {
    key: 'business__name',
    header: 'Business',
    sortable: true,
    className: 'font-medium text-gray-900',
    render: (p) => p.business_name,
  },
  {
    key: 'plan__name',
    header: 'Plan',
    sortable: true,
    className: 'text-gray-700',
    render: (p) => p.plan_name || '—',
  },
  {
    key: 'amount',
    header: 'Amount',
    sortable: true,
    align: 'right',
    className: 'font-medium text-gray-900',
    render: (p) => (
      <>
        &#8377;{p.amount}
        {Number(p.setup_fee) > 0 && <span className="block text-xs font-normal text-gray-500">incl. &#8377;{p.setup_fee} setup</span>}
        {Number(p.reactivation_fee) > 0 && (
          <span className="block text-xs font-normal text-gray-500">incl. &#8377;{p.reactivation_fee} reactivation</span>
        )}
      </>
    ),
  },
  {
    key: 'method',
    header: 'Method',
    sortable: true,
    className: 'text-gray-700',
    render: (p) => (
      <>
        {METHOD_LABEL[p.method] ?? p.method}
        {p.reference && <span className="block text-xs text-gray-500">{p.reference}</span>}
      </>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (p) => (
      <span
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
          p.status === 'PAID'
            ? 'bg-green-100 text-green-700'
            : p.status === 'FAILED'
              ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-700'
        }`}
      >
        {p.status}
      </span>
    ),
  },
  {
    key: 'period_start',
    header: 'Period',
    sortable: true,
    className: 'whitespace-nowrap text-xs text-gray-500',
    render: (p) =>
      p.period_start && p.period_end
        ? `${new Date(p.period_start).toLocaleDateString('en-IN')} — ${new Date(p.period_end).toLocaleDateString('en-IN')}`
        : '—',
  },
  {
    key: 'created_at',
    header: 'Date',
    sortable: true,
    className: 'whitespace-nowrap text-xs text-gray-500',
    render: (p) => new Date(p.created_at).toLocaleDateString('en-IN'),
  },
]

export function PlatformPaymentsPage() {
  const [payments, setPayments] = useState<SaasPayment[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const table = useServerTable()
  const { params: tableParams } = table

  const fetchPayments = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.getPayments(tableParams)
      setPayments(data.results)
      setCount(data.count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchPayments()
  }, [fetchPayments])

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Payment History ({count})</h1>

      <DataTable
        columns={columns}
        rows={payments}
        rowKey={(p) => p.id}
        loading={loading}
        emptyMessage="No payments recorded yet."
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
    </div>
  )
}
