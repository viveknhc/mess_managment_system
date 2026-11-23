import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { fetchAll } from '../../services/fetchAll'
import { notify } from '../../utils/notify'
import { confirmDialog } from '../../components/ui/dialog'
import { routeApi, type DeliveryRoute } from './routeApi'

interface StaffMember {
  id: string
  name: string
  username: string
  role: string
  is_active: boolean
}

interface CustomerRow {
  id: string
  name: string
  customer_code: string
  location: string
  route: string | null
  route_name: string | null
}

const inputCls =
  'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none'

function RouteForm({
  route,
  riders,
  customers,
  onClose,
  onSaved,
}: {
  route: DeliveryRoute | null
  riders: StaffMember[]
  customers: CustomerRow[]
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(route?.name ?? '')
  const [staff, setStaff] = useState(route?.staff ?? '')
  const [notes, setNotes] = useState(route?.notes ?? '')
  const [selected, setSelected] = useState<Set<string>>(new Set(route?.customers.map((c) => c.id) ?? []))
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = customers.filter(
      (c) =>
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.customer_code.toLowerCase().includes(q) ||
        c.location.toLowerCase().includes(q),
    )
    // Customers on this route first, then by name.
    return list.sort((a, b) => Number(selected.has(b.id)) - Number(selected.has(a.id)) || a.name.localeCompare(b.name))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customers, query])

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    const input = { name, staff: staff || null, notes, customer_ids: [...selected] }
    try {
      if (route) await routeApi.update(route.id, input)
      else await routeApi.create(input)
      notify.success(route ? 'Route updated' : 'Route created', `${name} · ${selected.size} customers`)
      onSaved()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { error?: { message?: string; fields?: Record<string, string[]> } } } })
        ?.response?.data?.error
      setError(Object.values(data?.fields ?? {}).flat().join(', ') || data?.message || 'Failed to save the route')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4">
      <div className="flex max-h-[92dvh] w-full max-w-lg flex-col rounded-t-2xl bg-white shadow-lg sm:rounded-xl">
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="space-y-4 overflow-y-auto p-5 sm:p-6">
            <h2 className="text-lg font-bold text-gray-900">{route ? 'Edit Route' : 'New Route'}</h2>
            {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

            <div>
              <label htmlFor="route-name" className="mb-1 block text-sm font-medium text-gray-700">Route name *</label>
              <input id="route-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100}
                placeholder="e.g. Kakkanad, Infopark side" className={inputCls} />
            </div>

            <div>
              <label htmlFor="route-staff" className="mb-1 block text-sm font-medium text-gray-700">Delivery staff</label>
              <select id="route-staff" value={staff} onChange={(e) => setStaff(e.target.value)} className={inputCls}>
                <option value="">Nobody yet (any delivery staff can take these)</option>
                {riders.map((r) => (
                  <option key={r.id} value={r.id}>{r.name || r.username}</option>
                ))}
              </select>
              {riders.length === 0 && (
                <p className="mt-1 text-xs text-gray-500">Add a staff member with the Delivery role on the Staff page first.</p>
              )}
            </div>

            <div>
              <label htmlFor="route-notes" className="mb-1 block text-sm font-medium text-gray-700">Notes</label>
              <input id="route-notes" value={notes} onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional" className={inputCls} />
            </div>

            <div>
              <div className="mb-1 flex items-baseline justify-between">
                <span className="text-sm font-medium text-gray-700">Customers on this route</span>
                <span className="text-xs text-gray-500">{selected.size} selected</span>
              </div>
              <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
                placeholder="Search name, code or location" aria-label="Search customers" className={inputCls} />
              <ul className="mt-2 max-h-72 divide-y divide-gray-100 overflow-y-auto rounded-lg border border-gray-200">
                {shown.map((c) => {
                  const elsewhere = c.route && c.route !== route?.id && !selected.has(c.id) ? c.route_name : null
                  const moving = c.route && c.route !== route?.id && selected.has(c.id) ? c.route_name : null
                  return (
                    <li key={c.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-gray-50">
                        <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)}
                          className="h-4 w-4 rounded border-gray-300 text-blue-600" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-gray-900">{c.name}</span>
                          <span className="block truncate text-xs text-gray-500">
                            {c.customer_code}{c.location ? ` · ${c.location}` : ''}
                          </span>
                        </span>
                        {elsewhere && <span className="shrink-0 text-xs text-gray-400">{elsewhere}</span>}
                        {moving && <span className="shrink-0 text-xs text-amber-600">moves from {moving}</span>}
                      </label>
                    </li>
                  )
                })}
                {shown.length === 0 && <li className="px-3 py-6 text-center text-sm text-gray-500">No customers found</li>}
              </ul>
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-gray-100 p-4">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={saving || !name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : route ? 'Save Route' : 'Create Route'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/** Owner/manager: group customers into routes, each delivered by one staff member. */
export function RoutesPage() {
  const [routes, setRoutes] = useState<DeliveryRoute[] | null>(null)
  const [riders, setRiders] = useState<StaffMember[]>([])
  const [customers, setCustomers] = useState<CustomerRow[]>([])
  const [editing, setEditing] = useState<DeliveryRoute | null | undefined>(undefined)

  const load = useCallback(async () => {
    try {
      const [r, staff, cust] = await Promise.all([
        routeApi.list(),
        fetchAll<StaffMember>('/staff/'),
        fetchAll<CustomerRow>('/customers/', { status: 'ACTIVE', ordering: 'name' }),
      ])
      setRoutes(r)
      setRiders(staff.filter((s) => s.role === 'DELIVERY_STAFF' && s.is_active))
      setCustomers(cust)
    } catch (err) {
      notify.error(err, "Couldn't load routes")
      setRoutes((prev) => prev ?? [])
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleDelete(route: DeliveryRoute) {
    const ok = await confirmDialog({
      title: `Delete ${route.name}?`,
      message: `Its ${route.customer_count} customers will be on no route, and their upcoming deliveries can be taken by any delivery staff.`,
      confirmText: 'Delete route',
      tone: 'danger',
    })
    if (!ok) return
    try {
      await routeApi.remove(route.id)
      notify.success('Route deleted', route.name)
      load()
    } catch (err) {
      notify.error(err, 'Could not delete the route')
    }
  }

  const unrouted = customers.filter((c) => !c.route).length

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Delivery Routes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Each delivery person sees only their route's customers, plus customers on no route.
          </p>
        </div>
        <button onClick={() => setEditing(null)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          New Route
        </button>
      </div>

      {routes === null ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1].map((i) => <div key={i} className="h-32 animate-pulse rounded-xl bg-gray-200/70" />)}
        </div>
      ) : routes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center">
          <p className="font-semibold text-gray-900">No routes yet</p>
          <p className="mt-1 text-sm text-gray-500">
            Create a route, pick its delivery person, and tick the customers they deliver to.
          </p>
        </div>
      ) : (
        <>
          <ul className="grid gap-3 sm:grid-cols-2">
            {routes.map((r) => (
              <li key={r.id} className="flex flex-col rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-gray-900">{r.name}</p>
                    <p className={`mt-0.5 text-sm ${r.staff_name ? 'text-gray-600' : 'text-amber-600'}`}>
                      {r.staff_name ?? 'No delivery staff assigned'}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
                    {r.customer_count} customer{r.customer_count === 1 ? '' : 's'}
                  </span>
                </div>
                {r.customers.length > 0 && (
                  <p className="mt-2 line-clamp-2 text-xs text-gray-500">{r.customers.map((c) => c.name).join(', ')}</p>
                )}
                {r.notes && <p className="mt-2 text-xs text-gray-400">{r.notes}</p>}
                <div className="mt-auto flex justify-end gap-1 pt-3">
                  <button onClick={() => setEditing(r)} className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(r)} className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {unrouted > 0 && (
            <p className="mt-4 text-sm text-gray-500">
              {unrouted} active customer{unrouted === 1 ? ' is' : 's are'} on no route. Any delivery staff can take their deliveries.
            </p>
          )}
        </>
      )}

      {editing !== undefined && (
        <RouteForm
          route={editing}
          riders={riders}
          customers={customers}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined)
            load()
          }}
        />
      )}
    </div>
  )
}
