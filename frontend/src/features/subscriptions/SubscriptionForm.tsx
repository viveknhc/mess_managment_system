import { useState, useEffect, type FormEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { fetchAll } from '../../services/fetchAll'
import { notify } from '../../utils/notify'
import { FEATURES, useFeature } from '../../hooks/useFeature'
import { ItemsEditor, cleanItems, extrasPerMeal, inr, type CustomItem } from './CustomizationEditor'

interface Customer { id: string; name: string; customer_code: string; phone: string }
interface Plan { id: string; name: string; price: string; duration_days: number; total_meals: number; meal_name: string }

interface Props {
  onClose: () => void
  onSaved: () => void
}

export function SubscriptionForm({ onClose, onSaved }: Props) {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [customerId, setCustomerId] = useState('')
  const [customerQuery, setCustomerQuery] = useState('')
  const [loadError, setLoadError] = useState('')
  const [planId, setPlanId] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const customOn = useFeature(FEATURES.CUSTOM_SUBSCRIPTIONS)
  const [customPrice, setCustomPrice] = useState('')
  const [items, setItems] = useState<CustomItem[]>([])

  useEffect(() => {
    // Every active customer and plan — a single request would only return the first 20.
    Promise.all([
      fetchAll<Customer>('/customers/', { status: 'ACTIVE', ordering: 'name' }),
      fetchAll<Plan>('/plans/', { is_active: 'true', ordering: 'name' }),
    ])
      .then(([custs, planList]) => {
        setCustomers(custs)
        setPlans(planList)
        if (custs.length) setCustomerId(custs[0].id)
        if (planList.length) setPlanId(planList[0].id)
      })
      .catch(() => setLoadError("Couldn't load customers and plans. Close and try again."))
  }, [])

  const selectedPlan = plans.find((p) => p.id === planId)
  const q = customerQuery.trim().toLowerCase()
  const shownCustomers = q
    ? customers.filter(
        (c) =>
          c.id === customerId ||
          c.name.toLowerCase().includes(q) ||
          c.customer_code.toLowerCase().includes(q) ||
          (c.phone ?? '').includes(q),
      )
    : customers

  function searchCustomers(value: string) {
    setCustomerQuery(value)
    const v = value.trim().toLowerCase()
    const first = customers.find(
      (c) => c.name.toLowerCase().includes(v) || c.customer_code.toLowerCase().includes(v) || (c.phone ?? '').includes(v),
    )
    if (v && first) setCustomerId(first.id)
  }
  const basePrice = selectedPlan ? (customPrice === '' ? Number(selectedPlan.price) : Number(customPrice)) : 0
  const extras = extrasPerMeal(items)
  const total = selectedPlan ? basePrice + extras * selectedPlan.total_meals : 0

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const body: Record<string, unknown> = { customer: customerId, plan: planId, start_date: startDate }
      if (customOn) {
        body.items = cleanItems(items)
        if (customPrice !== '') body.custom_price = customPrice
      }
      await apiClient.post('/subscriptions/', body)
      const customer = customers.find((c) => c.id === customerId)
      notify.success('Subscription created', customer ? `${customer.name} — awaiting payment` : 'Awaiting payment')
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
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4">
      <div className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 shadow-lg sm:rounded-xl sm:p-6">
        <h2 className="mb-4 text-lg font-bold text-gray-900">New Subscription</h2>

        {(error || loadError) && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error || loadError}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="customer" className="mb-1 block text-sm font-medium text-gray-700">
              Customer * <span className="font-normal text-gray-400">({customers.length} active)</span>
            </label>
            {customers.length > 10 && (
              <input type="search" value={customerQuery} onChange={(e) => searchCustomers(e.target.value)}
                placeholder="Search name, code or phone" aria-label="Search customers"
                className="mb-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
            )}
            <select id="customer" value={customerId} onChange={(e) => setCustomerId(e.target.value)} required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none">
              {shownCustomers.map((c) => (
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

          {customOn && selectedPlan && (
            <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
              <legend className="px-1 text-sm font-medium text-gray-700">Customize for this customer</legend>
              <div>
                <label htmlFor="custom_price" className="mb-1 block text-xs font-medium text-gray-600">Custom price</label>
                <input id="custom_price" type="number" min="0" step="0.01" inputMode="decimal" value={customPrice}
                  onChange={(e) => setCustomPrice(e.target.value)} placeholder={`Plan price ${inr(selectedPlan.price)}`}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
              </div>
              <ItemsEditor items={items} onChange={setItems} />
              <p className="text-xs text-gray-500">Extras are charged per meal. The kitchen and delivery staff see them every day.</p>
            </fieldset>
          )}

          {/* Plan preview */}
          {selectedPlan && (
            <div className="rounded-lg bg-gray-50 p-4 text-sm">
              <div className="font-medium text-gray-900">{selectedPlan.name}</div>
              <div className="mt-1 text-xs text-gray-500">
                {selectedPlan.meal_name} · {selectedPlan.duration_days} days · {selectedPlan.total_meals} meals
              </div>
              <div className="mt-2 text-lg font-bold text-gray-900">{inr(total)}</div>
              {(customPrice !== '' || extras > 0) && (
                <div className="mt-1 text-xs text-gray-500">
                  {customPrice !== '' ? `Custom ${inr(basePrice)}` : `Plan ${inr(selectedPlan.price)}`}
                  {extras > 0 && ` + extras ${inr(extras)} × ${selectedPlan.total_meals} meals`}
                </div>
              )}
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
