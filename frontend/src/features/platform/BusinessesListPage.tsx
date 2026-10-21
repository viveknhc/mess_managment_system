import { useState, useEffect, useCallback } from 'react'
import { platformApi, type PlatformBusiness } from './platformApi'

export function BusinessesListPage() {
  const [businesses, setBusinesses] = useState<PlatformBusiness[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  const fetchBusinesses = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.getBusinesses(page)
      setBusinesses(data.results)
      setCount(data.count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    fetchBusinesses()
  }, [fetchBusinesses])

  async function handleSuspend(id: string) {
    if (!confirm('Suspend this business?')) return
    const result = await platformApi.suspendBusiness(id)
    if (result.ok) fetchBusinesses()
  }

  async function handleReactivate(id: string) {
    const result = await platformApi.reactivateBusiness(id)
    if (result.ok) fetchBusinesses()
  }

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

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Businesses ({count})</h1>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 font-medium text-gray-700">Business</th>
                <th className="px-4 py-3 font-medium text-gray-700">Owner</th>
                <th className="px-4 py-3 font-medium text-gray-700">Status</th>
                <th className="px-4 py-3 font-medium text-gray-700">Plan</th>
                <th className="px-4 py-3 font-medium text-gray-700">Customers</th>
                <th className="px-4 py-3 font-medium text-gray-700">Staff</th>
                <th className="px-4 py-3 font-medium text-gray-700">Created</th>
                <th className="px-4 py-3 font-medium text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {businesses.map((biz) => (
                <tr key={biz.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{biz.name}</p>
                    <p className="text-xs text-gray-500">{biz.email || biz.phone}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-gray-700">{biz.owner_name || '—'}</p>
                    <p className="text-xs text-gray-500">{biz.owner_email}</p>
                  </td>
                  <td className="px-4 py-3">{statusBadge(biz.saas_status)}</td>
                  <td className="px-4 py-3 text-gray-700">{biz.plan_name || 'Trial'}</td>
                  <td className="px-4 py-3 text-gray-700">{biz.customer_count}</td>
                  <td className="px-4 py-3 text-gray-700">{biz.staff_count}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(biz.created_at).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3">
                    {biz.status === 'SUSPENDED' ? (
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
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {count > 20 && (
        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {page} of {Math.ceil(count / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 20 >= count}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
