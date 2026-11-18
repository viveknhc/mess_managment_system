import { useCallback, useEffect, useMemo, useState } from 'react'
import { promptDialog } from '../../components/ui/dialog'
import { notify } from '../../utils/notify'
import { NOT_DELIVERED_REASONS, canUndo, deliveryApi, isOpen, mapsLink, type DeliveryItem } from './deliveryApi'

/**
 * Delivery staff home: today's route as big, phone-friendly cards.
 * One tap = Delivered (with Undo); "Not delivered" asks for a reason.
 */

type Tab = 'todo' | 'done'

function time(iso: string | null) {
  return iso ? new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''
}

function Icon({ d, className = 'h-5 w-5' }: { d: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={d} />
    </svg>
  )
}

const ICONS = {
  check: 'M5 13l4 4L19 7',
  x: 'M6 18L18 6M6 6l12 12',
  phone: 'M3 5a2 2 0 012-2h3.3a1 1 0 01.95.68l1.5 4.49a1 1 0 01-.5 1.21l-2.26 1.13a11 11 0 005.52 5.52l1.13-2.26a1 1 0 011.21-.5l4.49 1.5a1 1 0 01.68.95V19a2 2 0 01-2 2h-1C9.72 21 3 14.28 3 6V5z',
  pin: 'M17.66 16.66L13.41 20.9a2 2 0 01-2.83 0l-4.24-4.24a8 8 0 1111.31 0zM15 11a3 3 0 11-6 0 3 3 0 016 0z',
  refresh: 'M4 4v5h.58m15.36 2A8 8 0 004.58 9m0 0H9m11 11v-5h-.58m0 0a8 8 0 01-15.36-2m15.36 2H15',
  search: 'M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z',
  undo: 'M3 10h10a5 5 0 010 10H9m-6-10l4-4m-4 4l4 4',
}

function ProgressRing({ done, total }: { done: number; total: number }) {
  const pct = total ? done / total : 0
  const r = 26
  const c = 2 * Math.PI * r
  return (
    <div className="relative h-16 w-16 shrink-0">
      <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="currentColor" strokeWidth="6" className="text-white/25" />
        <circle
          cx="32" cy="32" r={r} fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
          className="text-white transition-[stroke-dashoffset] duration-500"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
        {Math.round(pct * 100)}%
      </span>
    </div>
  )
}

function DeliveryCard({
  d,
  busy,
  onDelivered,
  onNotDelivered,
  onUndo,
}: {
  d: DeliveryItem
  busy: boolean
  onDelivered: () => void
  onNotDelivered: () => void
  onUndo: () => void
}) {
  const open = isOpen(d.status)
  const delivered = d.status === 'DELIVERED'
  const failed = d.status === 'NOT_DELIVERED'

  return (
    <li
      className={`overflow-hidden rounded-2xl border bg-white shadow-sm transition ${
        delivered ? 'border-green-200' : failed ? 'border-red-200' : 'border-gray-200'
      } ${busy ? 'opacity-60' : ''}`}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold text-gray-900">{d.customer_name}</p>
            <span className="mt-1 inline-block rounded-full bg-orange-50 px-2.5 py-0.5 text-xs font-semibold text-orange-700">
              {d.meal_name}
            </span>
          </div>
          {delivered && (
            <span className="flex shrink-0 items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-semibold text-green-700">
              <Icon d={ICONS.check} className="h-4 w-4" /> {time(d.delivered_at) || 'Delivered'}
            </span>
          )}
          {failed && (
            <span className="shrink-0 rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-700">Not delivered</span>
          )}
          {!open && !delivered && !failed && (
            <span className="shrink-0 rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-600">
              {d.status === 'SKIPPED' ? 'Skipped' : 'Cancelled'}
            </span>
          )}
        </div>

        {open && d.customer_address && (
          <p className="mt-3 flex gap-2 text-sm text-gray-600">
            <Icon d={ICONS.pin} className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
            <span>{d.customer_address}</span>
          </p>
        )}
        {d.notes && <p className="mt-2 rounded-lg bg-yellow-50 px-3 py-2 text-sm text-yellow-800">{d.notes}</p>}

        {/* Call / directions — only while it still needs delivering */}
        {open && (d.customer_phone || d.customer_address) && (
          <div className="mt-3 flex gap-2">
            {d.customer_phone && (
              <a
                href={`tel:${d.customer_phone}`}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-200 py-1.5 text-xs font-medium text-gray-700 active:bg-gray-100"
              >
                <Icon d={ICONS.phone} className="h-3.5 w-3.5" /> Call
              </a>
            )}
            {d.customer_address && (
              <a
                href={mapsLink(d.customer_address)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-200 py-1.5 text-xs font-medium text-gray-700 active:bg-gray-100"
              >
                <Icon d={ICONS.pin} className="h-3.5 w-3.5" /> Directions
              </a>
            )}
          </div>
        )}
      </div>

      {open ? (
        <div className="grid grid-cols-[1fr_auto] gap-2 border-t border-gray-100 bg-gray-50 px-3 py-2.5">
          <button
            type="button"
            onClick={onDelivered}
            disabled={busy}
            className="flex items-center justify-center gap-1.5 rounded-lg bg-green-600 py-2.5 text-sm font-semibold text-white shadow-sm active:scale-[0.98] active:bg-green-700 disabled:opacity-60"
          >
            <Icon d={ICONS.check} className="h-4 w-4" /> Delivered
          </button>
          <button
            type="button"
            onClick={onNotDelivered}
            disabled={busy}
            aria-label={`Not delivered to ${d.customer_name}`}
            className="flex items-center justify-center gap-1 rounded-lg border border-red-200 bg-white px-3 text-sm font-medium text-red-600 active:bg-red-50 disabled:opacity-60"
          >
            <Icon d={ICONS.x} className="h-4 w-4" /> Not delivered
          </button>
        </div>
      ) : (
        canUndo(d) && (
          <div className="border-t border-gray-100 px-4 py-2 text-right">
            <button type="button" onClick={onUndo} disabled={busy} className="inline-flex items-center gap-1 text-sm font-medium text-gray-500 active:text-gray-800">
              <Icon d={ICONS.undo} className="h-4 w-4" /> Undo
            </button>
          </div>
        )
      )}
    </li>
  )
}

export function DeliveryRunPage({ initialTab = 'todo' }: { initialTab?: Tab }) {
  const [items, setItems] = useState<DeliveryItem[] | null>(null)
  const [tab, setTab] = useState<Tab>(initialTab)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState<Set<string>>(new Set())
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true)
    try {
      setItems(await deliveryApi.allToday())
    } catch (err) {
      notify.error(err, "Couldn't load today's deliveries")
      setItems((prev) => prev ?? [])
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
    const onFocus = () => document.visibilityState === 'visible' && load()
    document.addEventListener('visibilitychange', onFocus)
    return () => document.removeEventListener('visibilitychange', onFocus)
  }, [load])

  function replace(updated: DeliveryItem) {
    setItems((prev) => prev?.map((d) => (d.id === updated.id ? updated : d)) ?? prev)
  }

  async function run(id: string, action: () => Promise<void>) {
    setBusy((b) => new Set(b).add(id))
    try {
      await action()
    } catch (err) {
      notify.error(err, 'Could not update. Check your internet and try again.')
      load()
    } finally {
      setBusy((b) => {
        const next = new Set(b)
        next.delete(id)
        return next
      })
    }
  }

  function undo(d: DeliveryItem) {
    return run(d.id, async () => {
      replace(await deliveryApi.undo(d.id))
      notify.info(`${d.customer_name} moved back to "To deliver"`)
    })
  }

  function markDelivered(d: DeliveryItem) {
    navigator.vibrate?.(30)
    return run(d.id, async () => {
      replace(await deliveryApi.setStatus(d.id, 'DELIVERED'))
      notify.undoable(`Delivered to ${d.customer_name}`, () => undo(d))
    })
  }

  async function markNotDelivered(d: DeliveryItem) {
    const reason = await promptDialog({
      title: `Couldn't deliver to ${d.customer_name}?`,
      message: 'Pick a reason or type one. The owner will see it.',
      options: NOT_DELIVERED_REASONS,
      placeholder: 'Reason',
      confirmText: 'Mark not delivered',
      tone: 'danger',
    })
    if (reason === null) return
    await run(d.id, async () => {
      replace(await deliveryApi.setStatus(d.id, 'NOT_DELIVERED', reason))
      notify.undoable(`Marked not delivered: ${d.customer_name}`, () => undo(d), reason)
    })
  }

  const counts = useMemo(() => {
    const list = items ?? []
    const relevant = list.filter((d) => d.status !== 'SKIPPED' && d.status !== 'CANCELLED')
    return {
      todo: list.filter((d) => isOpen(d.status)).length,
      done: list.length - list.filter((d) => isOpen(d.status)).length,
      delivered: list.filter((d) => d.status === 'DELIVERED').length,
      failed: list.filter((d) => d.status === 'NOT_DELIVERED').length,
      total: relevant.length,
    }
  }, [items])

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (items ?? [])
      .filter((d) => (tab === 'todo' ? isOpen(d.status) : !isOpen(d.status)))
      .filter(
        (d) =>
          !q ||
          d.customer_name.toLowerCase().includes(q) ||
          d.customer_address.toLowerCase().includes(q) ||
          d.meal_name.toLowerCase().includes(q),
      )
  }, [items, tab, query])

  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className="px-4 pb-8">
      {/* Progress */}
      <section className="rounded-2xl bg-gradient-to-br from-primary-600 to-primary-800 p-5 text-white shadow-md">
        <div className="flex items-center gap-4">
          <ProgressRing done={counts.delivered + counts.failed} total={counts.total} />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-white/80">{today}</p>
            <p className="text-xl font-bold">
              {items === null
                ? 'Loading...'
                : counts.todo === 0 && counts.total > 0
                  ? 'All done for today!'
                  : `${counts.todo} left to deliver`}
            </p>
            <p className="text-sm text-white/80">
              {counts.delivered} delivered{counts.failed ? ` · ${counts.failed} not delivered` : ''}
            </p>
          </div>
          <button
            type="button"
            onClick={() => load(true)}
            aria-label="Refresh"
            className="rounded-full bg-white/15 p-2.5 active:bg-white/25"
          >
            <Icon d={ICONS.refresh} className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </section>

      {/* Tabs + search */}
      <div className="sticky top-0 z-10 -mx-4 mt-4 bg-gray-50/95 px-4 pt-1 pb-3 backdrop-blur">
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-gray-200/70 p-1" role="tablist">
          {(
            [
              ['todo', 'To deliver', counts.todo],
              ['done', 'Done', counts.done],
            ] as const
          ).map(([key, label, n]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`rounded-lg py-2.5 text-sm font-semibold transition ${
                tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
              }`}
            >
              {label} <span className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{n}</span>
            </button>
          ))}
        </div>
        {(items?.length ?? 0) > 5 && (
          <label className="relative mt-3 block">
            <Icon d={ICONS.search} className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name, address or meal"
              className="w-full rounded-xl border border-gray-300 bg-white py-2.5 pr-3 pl-9 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
            />
          </label>
        )}
      </div>

      {/* List */}
      {items === null ? (
        <ul className="space-y-3" aria-label="Loading">
          {[0, 1, 2].map((i) => (
            <li key={i} className="h-44 animate-pulse rounded-2xl bg-gray-200/70" />
          ))}
        </ul>
      ) : shown.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-10 text-center">
          <p className="text-4xl" aria-hidden="true">{tab === 'todo' ? (counts.total ? '🎉' : '🍱') : '📋'}</p>
          <p className="mt-2 font-semibold text-gray-900">
            {query
              ? 'No matches'
              : tab === 'todo'
                ? counts.total
                  ? 'Everything is delivered'
                  : 'No deliveries today'
                : 'Nothing marked yet'}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {query ? 'Try a different name or address.' : tab === 'todo' && counts.total ? 'Great job today!' : ''}
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {shown.map((d) => (
            <DeliveryCard
              key={d.id}
              d={d}
              busy={busy.has(d.id)}
              onDelivered={() => markDelivered(d)}
              onNotDelivered={() => markNotDelivered(d)}
              onUndo={() => undo(d)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
