import { useState, useEffect, useCallback, useMemo } from 'react'
import { platformApi, type SaasPlan } from './platformApi'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

type PlanWithAdmin = SaasPlan & { razorpay_plan_id: string; is_active: boolean }

const emptyPlan: Partial<PlanWithAdmin> = {
  name: '',
  price_monthly: '',
  setup_fee: '0',
  reactivation_fee: '0',
  max_customers: 0,
  max_staff: 0,
  features: [],
  razorpay_plan_id: '',
  is_active: true,
}

export function PlatformPlansPage() {
  const [plans, setPlans] = useState<PlanWithAdmin[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingPlan, setEditingPlan] = useState<Partial<PlanWithAdmin>>(emptyPlan)
  const [editId, setEditId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [featuresText, setFeaturesText] = useState('')
  const table = useServerTable()
  const { params: tableParams } = table

  const fetchPlans = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.getPlans(tableParams)
      setPlans(data.results)
      setCount(data.count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  function openCreate() {
    setEditId(null)
    setEditingPlan(emptyPlan)
    setFeaturesText('')
    setShowForm(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const payload = {
      ...editingPlan,
      features: featuresText.split('\n').filter((l) => l.trim()),
    }

    const result = editId
      ? await platformApi.updatePlan(editId, payload)
      : await platformApi.createPlan(payload)

    if (!result.ok) {
      setError(result.error)
      return
    }

    setShowForm(false)
    fetchPlans()
  }

  const columns = useMemo<Column<PlanWithAdmin>[]>(() => {
    function openEdit(plan: PlanWithAdmin) {
      setEditId(plan.id)
      setEditingPlan(plan)
      setFeaturesText(plan.features.join('\n'))
      setShowForm(true)
    }

    async function handleDelete(id: string) {
      if (!confirm('Delete this plan?')) return
      await platformApi.deletePlan(id)
      fetchPlans()
    }

    return [
      {
        key: 'name',
        header: 'Name',
        sortable: true,
        className: 'font-medium text-gray-900',
        render: (plan) => plan.name,
      },
      {
        key: 'price_monthly',
        header: 'Price / month',
        sortable: true,
        align: 'right',
        className: 'whitespace-nowrap font-medium text-gray-900',
        render: (plan) => <>&#8377;{plan.price_monthly}</>,
      },
      {
        key: 'setup_fee',
        header: 'Setup Fee',
        sortable: true,
        align: 'right',
        className: 'whitespace-nowrap text-gray-700',
        render: (plan) => <>&#8377;{plan.setup_fee}</>,
      },
      {
        key: 'reactivation_fee',
        header: 'Reactivation Fee',
        sortable: true,
        align: 'right',
        className: 'whitespace-nowrap text-gray-700',
        render: (plan) => <>&#8377;{plan.reactivation_fee}</>,
      },
      {
        key: 'max_customers',
        header: 'Max Customers',
        sortable: true,
        align: 'right',
        className: 'text-gray-700',
        render: (plan) => (plan.max_customers === 0 ? 'Unlimited' : plan.max_customers),
      },
      {
        key: 'max_staff',
        header: 'Max Staff',
        sortable: true,
        align: 'right',
        className: 'text-gray-700',
        render: (plan) => (plan.max_staff === 0 ? 'Unlimited' : plan.max_staff),
      },
      {
        key: 'features',
        header: 'Features',
        className: 'max-w-xs text-xs text-gray-600',
        render: (plan) =>
          plan.features.length === 0 ? (
            <span className="text-gray-400">—</span>
          ) : (
            <span className="line-clamp-2" title={plan.features.join('\n')}>
              {plan.features.join(', ')}
            </span>
          ),
      },
      {
        key: 'is_active',
        header: 'Status',
        sortable: true,
        render: (plan) => (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              plan.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
            }`}
          >
            {plan.is_active ? 'Active' : 'Inactive'}
          </span>
        ),
      },
      {
        key: 'actions',
        header: 'Actions',
        render: (plan) => (
          <div className="flex gap-2">
            <button
              onClick={() => openEdit(plan)}
              className="rounded bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
            >
              Edit
            </button>
            <button
              onClick={() => handleDelete(plan.id)}
              className="rounded bg-red-100 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
            >
              Delete
            </button>
          </div>
        ),
      },
    ]
  }, [fetchPlans])

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">SaaS Plans</h1>
        <button
          onClick={openCreate}
          className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
        >
          Add Plan
        </button>
      </div>

      <DataTable
        columns={columns}
        rows={plans}
        rowKey={(plan) => plan.id}
        loading={loading}
        emptyMessage="No plans yet."
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

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-bold text-gray-900">
              {editId ? 'Edit Plan' : 'New Plan'}
            </h2>
            {error && (
              <div className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>
            )}
            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                type="text"
                required
                placeholder="Plan name"
                value={editingPlan.name || ''}
                onChange={(e) => setEditingPlan({ ...editingPlan, name: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
              <input
                type="number"
                required
                step="0.01"
                placeholder="Monthly price"
                value={editingPlan.price_monthly || ''}
                onChange={(e) => setEditingPlan({ ...editingPlan, price_monthly: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs text-gray-600">
                  One-time setup fee
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Setup fee"
                    value={editingPlan.setup_fee ?? '0'}
                    onChange={(e) => setEditingPlan({ ...editingPlan, setup_fee: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="text-xs text-gray-600">
                  Reactivation fee (back after 3+ months)
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Reactivation fee"
                    value={editingPlan.reactivation_fee ?? '0'}
                    onChange={(e) => setEditingPlan({ ...editingPlan, reactivation_fee: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  placeholder="Max customers (0=unlimited)"
                  value={editingPlan.max_customers ?? 0}
                  onChange={(e) =>
                    setEditingPlan({ ...editingPlan, max_customers: parseInt(e.target.value) || 0 })
                  }
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="Max staff (0=unlimited)"
                  value={editingPlan.max_staff ?? 0}
                  onChange={(e) =>
                    setEditingPlan({ ...editingPlan, max_staff: parseInt(e.target.value) || 0 })
                  }
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <textarea
                placeholder="Features (one per line)"
                value={featuresText}
                onChange={(e) => setFeaturesText(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                placeholder="Razorpay Plan ID (optional)"
                value={editingPlan.razorpay_plan_id || ''}
                onChange={(e) =>
                  setEditingPlan({ ...editingPlan, razorpay_plan_id: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editingPlan.is_active ?? true}
                  onChange={(e) =>
                    setEditingPlan({ ...editingPlan, is_active: e.target.checked })
                  }
                />
                Active
              </label>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 rounded-lg bg-purple-600 py-2 text-sm font-medium text-white hover:bg-purple-700"
                >
                  {editId ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 rounded-lg border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
