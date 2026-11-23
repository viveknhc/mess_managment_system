import { useState, type FormEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { notify } from '../../utils/notify'

/** A food customization on a subscription (feature custom_subscriptions). */
export interface CustomItem {
  label: string
  price_per_meal: string
}

/** Quick picks — free text is the norm, these just save typing. */
const SUGGESTIONS = ['Extra chicken 100g', 'Extra egg', 'No rice', 'Less spicy', 'Extra chapati']

const inputCls =
  'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none'

export const inr = (v: number | string) =>
  `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export function extrasPerMeal(items: CustomItem[]) {
  return items.filter((i) => i.label.trim()).reduce((sum, i) => sum + (Number(i.price_per_meal) || 0), 0)
}

/** Only rows with a label are sent; blank prices count as free. */
export function cleanItems(items: CustomItem[]) {
  return items
    .filter((i) => i.label.trim())
    .map((i) => ({ label: i.label.trim(), price_per_meal: i.price_per_meal || '0' }))
}

/** Editable list of extras: label + ₹ per meal. */
export function ItemsEditor({ items, onChange }: { items: CustomItem[]; onChange: (items: CustomItem[]) => void }) {
  function update(i: number, patch: Partial<CustomItem>) {
    onChange(items.map((item, j) => (j === i ? { ...item, ...patch } : item)))
  }
  const used = new Set(items.map((i) => i.label.trim().toLowerCase()))

  return (
    <div>
      {items.length > 0 && (
        <div className="space-y-2">
          <div className="grid grid-cols-[1fr_7rem_2rem] gap-2 text-xs font-medium text-gray-500">
            <span>Customization</span>
            <span>₹ per meal</span>
          </div>
          {items.map((item, i) => (
            <div key={i} className="grid grid-cols-[1fr_7rem_2rem] items-center gap-2">
              <input value={item.label} onChange={(e) => update(i, { label: e.target.value })} maxLength={120}
                placeholder="e.g. Extra chicken 100g" aria-label={`Customization ${i + 1}`} className={inputCls} />
              <input type="number" min="0" step="0.01" inputMode="decimal" value={item.price_per_meal}
                onChange={(e) => update(i, { price_per_meal: e.target.value })} placeholder="0"
                aria-label={`Price per meal for customization ${i + 1}`} className={inputCls} />
              <button type="button" onClick={() => onChange(items.filter((_, j) => j !== i))}
                aria-label={`Remove customization ${i + 1}`}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600">
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        <button type="button" onClick={() => onChange([...items, { label: '', price_per_meal: '' }])}
          className="rounded-lg border border-dashed border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50">
          + Add customization
        </button>
        {SUGGESTIONS.filter((s) => !used.has(s.toLowerCase())).map((s) => (
          <button key={s} type="button" onClick={() => onChange([...items, { label: s, price_per_meal: '' }])}
            className="rounded-lg bg-gray-100 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-200">
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

export interface CustomizableSubscription {
  id: string
  customer_name: string
  plan_name: string
  status: string
  total_amount: string
  paid_amount: string
  remaining_meals: number
  custom_price: string | null
  items: CustomItem[]
}

/**
 * Change a subscription's extras (and, while unpaid, its price). Mirrors the backend rule:
 * before it starts the total is recomputed; once running, extras are charged for meals left.
 */
export function CustomizeSubscriptionModal({
  sub,
  planPrice,
  totalMeals,
  onClose,
  onSaved,
}: {
  sub: CustomizableSubscription
  /** The plan's price and meals — only needed to preview a PENDING total. */
  planPrice: number | null
  totalMeals: number | null
  onClose: () => void
  onSaved: () => void
}) {
  const pending = sub.status === 'PENDING'
  const [items, setItems] = useState<CustomItem[]>(sub.items.map((i) => ({ ...i })))
  const [customPrice, setCustomPrice] = useState(sub.custom_price ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const oldExtras = extrasPerMeal(sub.items)
  const newExtras = extrasPerMeal(items)
  let newTotal: number | null = null
  if (pending) {
    if (planPrice !== null && totalMeals !== null) {
      const base = customPrice === '' ? planPrice : Number(customPrice)
      newTotal = base + newExtras * totalMeals
    }
  } else {
    newTotal = Number(sub.total_amount) + (newExtras - oldExtras) * sub.remaining_meals
  }
  const owed = newTotal === null ? null : newTotal - Number(sub.paid_amount)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    const body: Record<string, unknown> = { items: cleanItems(items) }
    if (pending) body.custom_price = customPrice === '' ? null : customPrice
    try {
      await apiClient.post(`/subscriptions/${sub.id}/customize/`, body)
      notify.success('Customizations saved', `${sub.customer_name} — ${sub.plan_name}`)
      onSaved()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { error?: { message?: string; fields?: Record<string, unknown> } } } })
        ?.response?.data?.error
      setError(data?.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4">
      <div className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 shadow-lg sm:rounded-xl sm:p-6">
        <h2 className="text-lg font-bold text-gray-900">Customize subscription</h2>
        <p className="mt-0.5 mb-4 text-sm text-gray-500">{sub.customer_name} · {sub.plan_name}</p>

        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          {pending ? (
            <div>
              <label htmlFor="custom_price" className="mb-1 block text-sm font-medium text-gray-700">Custom price</label>
              <input id="custom_price" type="number" min="0" step="0.01" inputMode="decimal" value={customPrice}
                onChange={(e) => setCustomPrice(e.target.value)}
                placeholder={planPrice !== null ? `Plan price ${inr(planPrice)}` : 'Plan price'} className={inputCls} />
              <p className="mt-1 text-xs text-gray-500">Leave empty to use the plan price.</p>
            </div>
          ) : (
            <p className="rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-800">
              This subscription is running, so its price is fixed. A change in paid extras is charged (or taken off)
              for the {sub.remaining_meals} meals left.
            </p>
          )}

          <ItemsEditor items={items} onChange={setItems} />

          {newTotal !== null && (
            <div className="rounded-lg bg-gray-50 p-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">New total</span>
                <span className="font-semibold text-gray-900">{inr(newTotal)}</span>
              </div>
              <div className="mt-1 flex justify-between text-xs text-gray-500">
                <span>Paid {inr(sub.paid_amount)}</span>
                <span className={owed !== null && owed < 0 ? 'font-medium text-red-600' : ''}>
                  {owed !== null && owed < 0 ? 'Less than already paid' : `Pending ${inr(Math.max(owed ?? 0, 0))}`}
                </span>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
