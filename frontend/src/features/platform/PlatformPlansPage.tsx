import { useState, useEffect, useCallback } from 'react'
import { platformApi, type SaasPlan } from './platformApi'

type PlanWithAdmin = SaasPlan & { razorpay_plan_id: string; is_active: boolean }

const emptyPlan: Partial<PlanWithAdmin> = {
  name: '',
  price_monthly: '',
  max_customers: 0,
  max_staff: 0,
  features: [],
  razorpay_plan_id: '',
  is_active: true,
}

export function PlatformPlansPage() {
  const [plans, setPlans] = useState<PlanWithAdmin[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingPlan, setEditingPlan] = useState<Partial<PlanWithAdmin>>(emptyPlan)
  const [editId, setEditId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [featuresText, setFeaturesText] = useState('')

  const fetchPlans = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.getPlans()
      setPlans(data.results)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  function openCreate() {
    setEditId(null)
    setEditingPlan(emptyPlan)
    setFeaturesText('')
    setShowForm(true)
  }

  function openEdit(plan: PlanWithAdmin) {
    setEditId(plan.id)
    setEditingPlan(plan)
    setFeaturesText(plan.features.join('\n'))
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

  async function handleDelete(id: string) {
    if (!confirm('Delete this plan?')) return
    await platformApi.deletePlan(id)
    fetchPlans()
  }

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

      {/* Plan Cards */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <div key={plan.id} className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    plan.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {plan.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                &#8377;{plan.price_monthly}
                <span className="text-sm font-normal text-gray-500">/mo</span>
              </p>
              <p className="mt-2 text-xs text-gray-500">
                {plan.max_customers === 0 ? 'Unlimited' : plan.max_customers} customers |{' '}
                {plan.max_staff === 0 ? 'Unlimited' : plan.max_staff} staff
              </p>
              {plan.features.length > 0 && (
                <ul className="mt-3 space-y-1">
                  {plan.features.map((f, i) => (
                    <li key={i} className="text-xs text-gray-600">
                      &#10003; {f}
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-4 flex gap-2">
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
            </div>
          ))}
        </div>
      )}

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
