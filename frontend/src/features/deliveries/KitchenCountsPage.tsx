import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'

interface MealCount {
  meal_id: string
  meal__name: string
  count: number
  /** Food customizations to prepare today, e.g. "Extra chicken 100g" ×5. */
  extras?: { label: string; count: number }[]
  /** Customizations with an amount, added up per food: "Extra chicken 100g" ×5 → Chicken 500 g. */
  extra_food?: { food: string; unit: string; total: number; customers: number; labels: string[] }[]
}

interface FoodTotal {
  food: string
  unit: string
  total: number
  customers: number
  byMeal: { meal: string; total: number }[]
}

/** The same extra food across meals (chicken at lunch + dinner) becomes one line. */
function extraFoodTotals(counts: MealCount[]): FoodTotal[] {
  const lines = new Map<string, FoodTotal>()
  for (const c of counts) {
    for (const f of c.extra_food ?? []) {
      const key = `${f.food.toLowerCase()}|${f.unit}`
      const line = lines.get(key) ?? { food: f.food, unit: f.unit, total: 0, customers: 0, byMeal: [] }
      line.total += f.total
      line.customers += f.customers
      line.byMeal.push({ meal: c.meal__name, total: f.total })
      lines.set(key, line)
    }
  }
  return [...lines.values()].sort((a, b) => a.food.localeCompare(b.food))
}

/** 1500 g → "1.5 kg", 500 g → "500 g", 2000 ml → "2 L", 6 pcs → "6 pcs". */
function formatQty(value: number, unit: string) {
  const fmt = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  if (unit === 'g' && value >= 1000) return `${fmt(value / 1000)} kg`
  if (unit === 'ml' && value >= 1000) return `${fmt(value / 1000)} L`
  return `${fmt(value)} ${unit}`
}

/** Customizations that aren't an amount of food ("No rice", "Less spicy"). */
function requestsOf(c: MealCount) {
  const food = new Set((c.extra_food ?? []).flatMap((f) => f.labels))
  return (c.extras ?? []).filter((x) => !food.has(x.label))
}

interface StatusSummary {
  delivered: number
  pending: number
  skipped: number
  not_delivered: number
}

export function KitchenCountsPage({ showSummary = false }: { showSummary?: boolean }) {
  const [counts, setCounts] = useState<MealCount[]>([])
  const [summary, setSummary] = useState<StatusSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        // today_summary returns status counts only — kitchen staff can't (and needn't) see the delivery list.
        const [countsRes, summaryRes] = await Promise.all([
          apiClient.get('/deliveries/kitchen_counts/'),
          apiClient.get<StatusSummary>('/deliveries/today_summary/'),
        ])
        setCounts(countsRes.data)
        setSummary(summaryRes.data)
      } catch {
        // empty state
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const total = counts.reduce((sum, c) => sum + c.count, 0)
  const extraFood = extraFoodTotals(counts)
  const withRequests = counts.filter((c) => requestsOf(c).length > 0)

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">
        {showSummary ? 'Meal Summary' : "Today's Meals"}
      </h1>
      <p className="mt-1 text-sm text-gray-500">Meals to prepare today</p>

      {counts.length > 0 && (
        <div className="mt-6 rounded-xl bg-primary-600 p-5 text-white shadow-sm">
          <p className="text-sm font-medium opacity-90">Total plates today</p>
          <p className="mt-1 text-4xl font-bold">{total}</p>
          <p className="mt-1 text-xs opacity-80">
            {counts.map((c) => `${c.meal__name} ${c.count}`).join(' · ')}
          </p>
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {counts.map((c) => (
          <Link
            key={c.meal_id}
            to={`/staff/kitchen/meals/${c.meal_id}`}
            className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow-sm transition hover:border-primary-300 hover:shadow"
          >
            <p className="text-3xl font-bold text-primary-700">{c.count}</p>
            <p className="mt-1 text-sm font-medium text-gray-600">{c.meal__name}</p>
            <p className="mt-2 text-xs font-medium text-primary-600">View customers →</p>
          </Link>
        ))}
        {counts.length === 0 && (
          <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm sm:col-span-3">
            <p className="text-gray-500">No meals scheduled for today</p>
          </div>
        )}
      </div>

      {extraFood.length > 0 && (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-700">Extra food to cook</p>
          <p className="mt-0.5 text-xs text-gray-500">On top of the plates above, from customers' customizations</p>
          <ul className="mt-3 divide-y divide-gray-100">
            {extraFood.map((f) => (
              <li key={`${f.food}|${f.unit}`} className="flex items-start justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">{f.food}</p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {f.customers} {f.customers === 1 ? 'customer' : 'customers'}
                    {f.byMeal.length > 1 &&
                      ` · ${f.byMeal.map((m) => `${m.meal} ${formatQty(m.total, f.unit)}`).join(' · ')}`}
                    {f.byMeal.length === 1 && ` · ${f.byMeal[0].meal}`}
                  </p>
                </div>
                <span className="shrink-0 text-lg font-bold text-orange-600">{formatQty(f.total, f.unit)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {withRequests.length > 0 && (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-700">Special requests</p>
          <p className="mt-0.5 text-xs text-gray-500">Included in the plate counts above</p>
          {withRequests.map((c) => (
            <div key={c.meal__name} className="mt-4">
              <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">{c.meal__name}</p>
              <ul className="mt-2 divide-y divide-gray-100">
                {requestsOf(c).map((x) => (
                  <li key={x.label} className="flex items-center justify-between py-2 text-sm">
                    <span className="text-gray-800">{x.label}</span>
                    <span className="rounded-full bg-gray-100 px-2.5 py-0.5 font-semibold text-gray-700">×{x.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {showSummary && summary && (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="mb-3 text-sm font-medium text-gray-700">Today's delivery outcomes</p>
          <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
            <div className="rounded-lg bg-green-50 p-3">
              <p className="text-xl font-bold text-green-700">{summary.delivered}</p>
              <p className="text-xs text-green-600">Delivered</p>
            </div>
            <div className="rounded-lg bg-yellow-50 p-3">
              <p className="text-xl font-bold text-yellow-700">{summary.pending}</p>
              <p className="text-xs text-yellow-600">Pending</p>
            </div>
            <div className="rounded-lg bg-gray-100 p-3">
              <p className="text-xl font-bold text-gray-600">{summary.skipped}</p>
              <p className="text-xs text-gray-500">Skipped</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3">
              <p className="text-xl font-bold text-red-700">{summary.not_delivered}</p>
              <p className="text-xs text-red-600">Not Delivered</p>
            </div>
          </div>
          <p className="mt-3 text-right text-xs text-gray-400">Total: {total} meals</p>
        </div>
      )}
    </div>
  )
}
