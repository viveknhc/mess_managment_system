import { useState, useEffect, type FormEvent } from 'react'
import { apiClient } from '../../services/apiClient'

interface Customer { id: string; name: string; customer_code: string }
interface Plan { id: string; name: string; price: string; duration_days: number; total_meals: number; meal_name: string }

interface Props {
  onClose: () => void
  onSaved: () => void
}

export function SubscriptionForm({ onClose, onSaved }: Props) {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [customerId, setCustomerId] = useState('')
  const [planId, setPlanId] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([
      apiClient.get('/customers/', { params: { status: 'ACTIVE' } }),
      apiClient.get('/plans/', { params: { is_active: 'true' } }),
    ]).then(([custRes, planRes]) => {
      setCustomers(custRes.data.results)
      setPlans(planRes.data.results)
      if (custRes.data.results.length) setCustomerId(custRes.data.results[0].id)
      if (planRes.data.results.length) setPlanId(planRes.data.results[0].id)
    })
  }, [])

  const selectedPlan = plans.find((p) => p.id === planId)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await apiClient.post('/subscriptions/', {
        customer: customerId,
        plan: planId,
        start_date: startDate,
      })
      onSaved()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { error?: { message?: string; fields?: Record<string, string[]> } } } })
        ?.response?.data?.error
      if (data?.fields) {
        setError(Object.values(data.fields).flat().join(', ') || data.message || 'Failed')
      } else {
        setError(data?.message || 'Failed to create subscription')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-bold text-gray-900">New Subscription</h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="customer" className="mb-1 block text-sm font-medium text-gray-700">Customer *</label>
            <select id="customer" value={customerId} onChange={(e) => setCustomerId(e.target.value)} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none">
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.customer_code})</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="plan" className="mb-1 block text-sm font-medium text-gray-700">Plan *</label>
            <select id="plan" value={planId} onChange={(e) => setPlanId(e.target.value)} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none">
              {plans.map((p) => (
                <option key={p.id} value={p.id}>{p.name} — ₹{Number(p.price).toLocaleString('en-IN')}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="start_date" className="mb-1 block text-sm font-medium text-gray-700">Start Date *</label>
            <input id="start_date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
          </div>

          {/* Plan preview */}
          {selectedPlan && (
            <div className="rounded-lg bg-gray-50 p-4 text-sm">
              <div className="font-medium text-gray-900">{selectedPlan.name}</div>
              <div className="mt-1 text-xs text-gray-500">
                {selectedPlan.meal_name} · {selectedPlan.duration_days} days · {selectedPlan.total_meals} meals
              </div>
              <div className="mt-2 text-lg font-bold text-gray-900">
                ₹{Number(selectedPlan.price).toLocaleString('en-IN')}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={saving || !customerId || !planId}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Creating...' : 'Create Subscription'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
