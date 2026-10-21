import { useCallback, useEffect, useState, type FormEvent, type ChangeEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

interface Meal {
  id: string
  name: string
}

interface Plan {
  id: string
  name: string
  description: string
  meal: string
  meal_name: string
  duration_days: number
  total_meals: number
  price: string
  skip_allowed: boolean
  pause_allowed: boolean
  is_active: boolean
}

export function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [count, setCount] = useState(0)
  const [meals, setMeals] = useState<Meal[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Plan | null>(null)
  const [error, setError] = useState('')
  const table = useServerTable()
  const { params: tableParams } = table
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [plansRes, mealsRes] = await Promise.all([
        apiClient.get('/plans/', { params: tableParams }),
        apiClient.get('/meals/', { params: { is_active: 'true', page_size: '100' } }),
      ])
      setPlans(plansRes.data.results)
      setCount(plansRes.data.count)
      setMeals(mealsRes.data.results)
    } catch {
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  async function handleToggleActive(plan: Plan) {
    try {
      await apiClient.patch(`/plans/${plan.id}/`, { is_active: !plan.is_active })
      await fetchData()
    } catch {
      setError('Failed to update plan')
    }
  }

  const columns: Column<Plan>[] = [
    {
      key: 'name',
      header: 'Plan',
      sortable: true,
      render: (plan) => (
        <>
          <div className="font-medium text-gray-900">{plan.name}</div>
          {plan.description && <div className="max-w-xs truncate text-xs text-gray-500" title={plan.description}>{plan.description}</div>}
        </>
      ),
    },
    { key: 'meal__name', header: 'Meal', sortable: true, className: 'text-gray-600', render: (plan) => plan.meal_name },
    { key: 'duration_days', header: 'Days', sortable: true, align: 'right', className: 'text-gray-600', render: (plan) => plan.duration_days },
    { key: 'total_meals', header: 'Meals', sortable: true, align: 'right', className: 'text-gray-600', render: (plan) => plan.total_meals },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      align: 'right',
      className: 'font-semibold text-gray-900',
      render: (plan) => `₹${Number(plan.price).toLocaleString('en-IN')}`,
    },
    {
      key: 'rules',
      header: 'Rules',
      render: (plan) => (
        <div className="flex gap-1.5">
          {plan.skip_allowed && (
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium whitespace-nowrap text-blue-700">Skip</span>
          )}
          {plan.pause_allowed && (
            <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium whitespace-nowrap text-purple-700">Pause</span>
          )}
          {!plan.skip_allowed && !plan.pause_allowed && <span className="text-gray-400">—</span>}
        </div>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      sortable: true,
      render: (plan) => (
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            plan.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {plan.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
  ]

  if (canWrite) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (plan) => (
        <div className="flex justify-end gap-2">
          <button
            onClick={() => { setEditing(plan); setShowForm(true) }}
            className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
          >
            Edit
          </button>
          <button
            onClick={() => handleToggleActive(plan)}
            className={`rounded px-2 py-1 text-xs font-medium ${
              plan.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'
            }`}
          >
            {plan.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      ),
    })
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Plans</h1>
          <p className="mt-1 text-sm text-gray-500">Subscription plans for your customers</p>
        </div>
        {canWrite && (
          <button
            onClick={() => { setEditing(null); setShowForm(true) }}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Add Plan
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {!loading && count === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No plans yet</p>
          {canWrite && (
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Create your first plan
            </button>
          )}
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={plans}
          rowKey={(plan) => plan.id}
          loading={loading}
          rowClassName={(plan) => (plan.is_active ? '' : 'opacity-60')}
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
      )}

      {showForm && (
        <PlanForm
          plan={editing}
          meals={meals}
          onClose={() => { setShowForm(false); setEditing(null) }}
          onSaved={() => { setShowForm(false); setEditing(null); fetchData() }}
        />
      )}
    </div>
  )
}

// ── Plan form modal ──────────────────────────────────────────────────────

function PlanForm({
  plan,
  meals,
  onClose,
  onSaved,
}: {
  plan: Plan | null
  meals: Meal[]
  onClose: () => void
  onSaved: () => void
}) {
  const isEdit = !!plan
  const [form, setForm] = useState({
    name: plan?.name ?? '',
    description: plan?.description ?? '',
    meal: plan?.meal ?? (meals[0]?.id ?? ''),
    duration_days: plan?.duration_days?.toString() ?? '30',
    total_meals: plan?.total_meals?.toString() ?? '30',
    price: plan?.price ?? '',
    skip_allowed: plan?.skip_allowed ?? false,
    pause_allowed: plan?.pause_allowed ?? false,
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function handleChange(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const target = e.target
    const value = target instanceof HTMLInputElement && target.type === 'checkbox' ? target.checked : target.value
    setForm((prev) => ({ ...prev, [target.name]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const payload = {
        name: form.name,
        description: form.description,
        meal: form.meal,
        duration_days: Number(form.duration_days),
        total_meals: Number(form.total_meals),
        price: form.price,
        skip_allowed: form.skip_allowed,
        pause_allowed: form.pause_allowed,
      }
      if (isEdit) {
        await apiClient.patch(`/plans/${plan.id}/`, payload)
      } else {
        await apiClient.post('/plans/', payload)
      }
      onSaved()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { error?: { message?: string; fields?: Record<string, string[]> } } } })
        ?.response?.data?.error
      if (data?.fields) {
        setError(Object.values(data.fields).flat().join(', ') || data.message || 'Failed to save')
      } else {
        setError(data?.message || 'Failed to save')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-bold text-gray-900">
          {isEdit ? 'Edit Plan' : 'Add Plan'}
        </h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700">Name *</label>
            <input id="name" name="name" value={form.name} onChange={handleChange} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
          </div>

          <div>
            <label htmlFor="meal" className="mb-1 block text-sm font-medium text-gray-700">Meal Type *</label>
            <select id="meal" name="meal" value={form.meal} onChange={handleChange} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none">
              {meals.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label htmlFor="duration_days" className="mb-1 block text-sm font-medium text-gray-700">Days</label>
              <input id="duration_days" name="duration_days" type="number" min="1" value={form.duration_days} onChange={handleChange} required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label htmlFor="total_meals" className="mb-1 block text-sm font-medium text-gray-700">Meals</label>
              <input id="total_meals" name="total_meals" type="number" min="1" value={form.total_meals} onChange={handleChange} required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label htmlFor="price" className="mb-1 block text-sm font-medium text-gray-700">Price (₹) *</label>
              <input id="price" name="price" type="number" step="0.01" min="0" value={form.price} onChange={handleChange} required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
            </div>
          </div>

          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-medium text-gray-700">Description</label>
            <textarea id="description" name="description" value={form.description} onChange={handleChange} rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" name="skip_allowed" checked={form.skip_allowed} onChange={handleChange}
                className="h-4 w-4 rounded border-gray-300 text-blue-600" />
              Allow skip
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" name="pause_allowed" checked={form.pause_allowed} onChange={handleChange}
                className="h-4 w-4 rounded border-gray-300 text-blue-600" />
              Allow pause
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
