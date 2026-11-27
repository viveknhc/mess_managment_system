import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'

interface KitchenCustomer {
  delivery_id: string
  name: string
  customer_code: string
  location: string
  route_name: string | null
  status: string
  customizations: string[]
}

interface KitchenMeal {
  meal_id: string
  meal_name: string
  count: number
  extra_food: { food: string; unit: string; total: number; customers: number; labels: string[] }[]
  customers: KitchenCustomer[]
}

function formatQty(value: number, unit: string) {
  const fmt = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  if (unit === 'g' && value >= 1000) return `${fmt(value / 1000)} kg`
  if (unit === 'ml' && value >= 1000) return `${fmt(value / 1000)} L`
  return `${fmt(value)} ${unit}`
}

/** Kitchen drill-down: everyone getting one meal today, with what to add or leave out per plate. */
export function KitchenMealPage() {
  const { mealId } = useParams<{ mealId: string }>()
  const [data, setData] = useState<KitchenMeal | null>(null)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [onlyCustom, setOnlyCustom] = useState(false)

  useEffect(() => {
    apiClient
      .get<KitchenMeal>('/deliveries/kitchen_meal/', { params: { meal: mealId } })
      .then((res) => setData(res.data))
      .catch(() => setError('Could not load this meal.'))
  }, [mealId])

  const foodLabels = useMemo(() => new Set(data?.extra_food.flatMap((f) => f.labels) ?? []), [data])
  const customized = data?.customers.filter((c) => c.customizations.length > 0).length ?? 0
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (data?.customers ?? []).filter(
      (c) =>
        (!onlyCustom || c.customizations.length > 0) &&
        (!q ||
          c.name.toLowerCase().includes(q) ||
          c.customer_code.toLowerCase().includes(q) ||
          c.location.toLowerCase().includes(q)),
    )
  }, [data, search, onlyCustom])

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <Link to="/staff" className="text-sm font-medium text-primary-700 hover:underline">
        ← Today's meals
      </Link>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {!data && !error && (
        <div className="flex items-center justify-center p-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {data && (
        <>
          <div className="mt-3 flex items-end justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">{data.meal_name}</h1>
              <p className="mt-1 text-sm text-gray-500">
                {customized} of {data.count} {data.count === 1 ? 'plate has' : 'plates have'} customizations
              </p>
            </div>
            <p className="text-right">
              <span className="block text-3xl font-bold text-primary-700">{data.count}</span>
              <span className="text-xs text-gray-500">plates</span>
            </p>
          </div>

          {data.extra_food.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {data.extra_food.map((f) => (
                <span
                  key={`${f.food}|${f.unit}`}
                  className="rounded-full bg-orange-50 px-3 py-1 text-sm font-medium text-orange-700"
                >
                  {f.food} {formatQty(f.total, f.unit)}
                </span>
              ))}
            </div>
          )}

          <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, code or room/area"
              aria-label="Search customers"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none sm:flex-1"
            />
            <div className="flex shrink-0 rounded-lg border border-gray-300 p-0.5 text-sm">
              {[
                { on: false, label: `All (${data.count})` },
                { on: true, label: `Customized (${customized})` },
              ].map((t) => (
                <button
                  key={t.label}
                  onClick={() => setOnlyCustom(t.on)}
                  className={`flex-1 rounded-md px-3 py-1.5 font-medium whitespace-nowrap ${
                    onlyCustom === t.on ? 'bg-primary-600 text-white' : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <ul className="mt-4 divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white shadow-sm">
            {rows.map((c) => (
              <li key={c.delivery_id} className="px-4 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="font-medium text-gray-900">{c.name}</p>
                  <span className="shrink-0 text-xs text-gray-400">{c.customer_code}</span>
                </div>
                {(c.location || c.route_name) && (
                  <p className="mt-0.5 text-xs text-gray-500">
                    {[c.location, c.route_name && `Route: ${c.route_name}`].filter(Boolean).join(' · ')}
                  </p>
                )}
                {c.customizations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {c.customizations.map((label) => (
                      <span
                        key={label}
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          foodLabels.has(label) ? 'bg-orange-50 text-orange-700' : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
            {rows.length === 0 && (
              <li className="px-4 py-8 text-center text-sm text-gray-500">
                {data.count === 0 ? 'Nobody left to cook for.' : 'No customers match.'}
              </li>
            )}
          </ul>
        </>
      )}
    </div>
  )
}
