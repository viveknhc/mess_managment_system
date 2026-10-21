import { useState, useEffect, useCallback, useMemo } from 'react'
import { platformApi, type PlatformBusiness } from './platformApi'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

function statusBadge(status: string | null) {
  const colors: Record<string, string> = {
    TRIAL: 'bg-blue-100 text-blue-700',
    ACTIVE: 'bg-green-100 text-green-700',
    PAST_DUE: 'bg-yellow-100 text-yellow-700',
    SUSPENDED: 'bg-red-100 text-red-700',
    CANCELLED: 'bg-gray-100 text-gray-700',
  }
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status || ''] || 'bg-gray-100 text-gray-700'}`}>
      {status || '—'}
    </span>
  )
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleDateString('en-IN') : '—'
}

export function BusinessesListPage() {
  const [businesses, setBusinesses] = useState<PlatformBusiness[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const table = useServerTable()
  const { params: tableParams } = table

  const fetchBusinesses = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.getBusinesses(tableParams)
      setBusinesses(data.results)
      setCount(data.count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchBusinesses()
  }, [fetchBusinesses])

  const columns = useMemo<Column<PlatformBusiness>[]>(() => {
    async function handleSuspend(id: string) {
      if (!confirm('Suspend this business?')) return
      const result = await platformApi.suspendBusiness(id)
      if (result.ok) fetchBusinesses()
    }

    async function handleReactivate(id: string) {
      const result = await platformApi.reactivateBusiness(id)
      if (result.ok) fetchBusinesses()
    }

    return [
      {
        key: 'name',
        header: 'Business',
        sortable: true,
        render: (biz) => (
          <>
            <p className="font-medium text-gray-900">{biz.name}</p>
            <p className="text-xs text-gray-500">{biz.email || biz.phone}</p>
          </>
        ),
      },
      {
        key: 'owner',
        header: 'Owner',
        render: (biz) => (
          <>
            <p className="text-gray-700">{biz.owner_name || '—'}</p>
            <p className="text-xs text-gray-500">{biz.owner_email}</p>
          </>
        ),
      },
      {
        key: 'saas_subscription__status',
        header: 'Status',
        sortable: true,
        render: (biz) => statusBadge(biz.saas_status),
      },
      {
        key: 'saas_subscription__plan__name',
        header: 'Plan',
        sortable: true,
        className: 'text-gray-700',
        render: (biz) => biz.plan_name || 'Trial',
      },
      {
        key: 'saas_subscription__trial_end_date',
        header: 'Trial Ends',
        sortable: true,
        className: 'whitespace-nowrap text-xs text-gray-500',
        render: (biz) => formatDate(biz.trial_end_date),
      },
      {
        key: 'customer_count',
        header: 'Customers',
        align: 'right',
        className: 'text-gray-700',
        render: (biz) => biz.customer_count,
      },
      {
        key: 'staff_count',
        header: 'Staff',
        align: 'right',
        className: 'text-gray-700',
        render: (biz) => biz.staff_count,
      },
      {
        key: 'created_at',
        header: 'Created',
        sortable: true,
        className: 'whitespace-nowrap text-xs text-gray-500',
        render: (biz) => formatDate(biz.created_at),
      },
      {
        key: 'actions',
        header: 'Actions',
        render: (biz) =>
          biz.status === 'SUSPENDED' ? (
            <button
              onClick={() => handleReactivate(biz.id)}
              className="rounded bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-200"
            >
              Reactivate
            </button>
          ) : (
            <button
              onClick={() => handleSuspend(biz.id)}
              className="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
            >
              Suspend
            </button>
          ),
      },
    ]
  }, [fetchBusinesses])

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Businesses ({count})</h1>
      </div>

      <DataTable
        columns={columns}
        rows={businesses}
        rowKey={(biz) => biz.id}
        loading={loading}
        emptyMessage="No businesses yet."
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
