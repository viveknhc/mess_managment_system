import { useEffect, useState, type FormEvent, type ChangeEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'

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
  const [meals, setMeals] = useState<Meal[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Plan | null>(null)
  const [error, setError] = useState('')
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  async function fetchData() {
    setLoading(true)
    try {
      const [plansRes, mealsRes] = await Promise.all([
        apiClient.get('/plans/'),
        apiClient.get('/meals/', { params: { is_active: 'true' } }),
      ])
      setPlans(plansRes.data.results)
      setMeals(mealsRes.data.results)
    } catch {
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  async function handleToggleActive(plan: Plan) {
    try {
      await apiClient.patch(`/plans/${plan.id}/`, { is_active: !plan.is_active })
      await fetchData()
    } catch {
      setError('Failed to update plan')
    }
  }

  if (loading && plans.length === 0) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
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

      {plans.length === 0 ? (
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
        <div className="grid gap-4 sm:grid-cols-2">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`rounded-xl border bg-white p-5 shadow-sm ${
                plan.is_active ? 'border-gray-200' : 'border-gray-100 opacity-60'
              }`}
            >
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{plan.name}</h3>
                  <p className="mt-0.5 text-xs text-gray-500">{plan.meal_name}</p>
                </div>
                <span className="text-lg font-bold text-gray-900">
                  ₹{Number(plan.price).toLocaleString('en-IN')}
                </span>
              </div>

              {plan.description && (
                <p className="mb-3 text-xs text-gray-500">{plan.description}</p>
              )}

              <div className="mb-3 flex gap-4 text-xs text-gray-600">
                <span>{plan.duration_days} days</span>
                <span>{plan.total_meals} meals</span>
              </div>

              {/* Skip/pause badges (P-06) */}
              <div className="mb-3 flex gap-2">
                {plan.skip_allowed && (
                  <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                    Skip allowed
                  </span>
                )}
                {plan.pause_allowed && (
                  <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                    Pause allowed
                  </span>
                )}
                {!plan.is_active && (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                    Inactive
                  </span>
                )}
              </div>

              {canWrite && (
                <div className="flex gap-2 border-t border-gray-100 pt-3">
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
              )}
            </div>
          ))}
        </div>
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
