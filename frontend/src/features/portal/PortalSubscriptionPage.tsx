import { useCallback, useEffect, useState } from 'react'
import type { PortalSubscription } from './portalApi'
import { portalApi } from './portalApi'

type DialogKind = 'skip' | 'pause' | 'renew' | null

const STATUS_STYLES: Record<string, string> = {
  ACTIVE: 'bg-green-50 text-green-700',
  PAUSED: 'bg-yellow-50 text-yellow-700',
  EXPIRED: 'bg-gray-100 text-gray-600',
  PENDING: 'bg-blue-50 text-blue-700',
  CANCELLED: 'bg-red-50 text-red-700',
}

export function PortalSubscriptionPage() {
  const [subs, setSubs] = useState<PortalSubscription[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)
  const [dialog, setDialog] = useState<DialogKind>(null)
  const [busy, setBusy] = useState(false)

  // dialog inputs
  const [skipDate, setSkipDate] = useState('')
  const [skipReason, setSkipReason] = useState('')
  const [pauseStart, setPauseStart] = useState('')
  const [pauseEnd, setPauseEnd] = useState('')
  const [pauseReason, setPauseReason] = useState('')

  const flash = (kind: 'ok' | 'err', msg: string) => {
    setToast({ kind, msg })
    setTimeout(() => setToast(null), 3500)
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await portalApi.subscriptions()
      setSubs(data)
    } catch {
      flash('err', 'Failed to load subscriptions')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const current = subs.find((s) => s.status === 'ACTIVE' || s.status === 'PAUSED') ?? subs[0]

  function openDialog(kind: DialogKind) {
    if (!current) return
    setSkipDate('')
    setSkipReason('')
    setPauseStart('')
    setPauseEnd('')
    setPauseReason('')
    setDialog(kind)
  }

  async function handleSkip() {
    if (!current) return
    setBusy(true)
    const res = await portalApi.skipMeal(current.id, skipDate || undefined, skipReason || undefined)
    setBusy(false)
    if (res.ok) {
      setDialog(null)
      flash('ok', 'Meal skipped successfully')
      load()
    } else {
      flash('err', res.error)
    }
  }

  async function handlePause() {
    if (!current) return
    setBusy(true)
    const res = await portalApi.pauseRequest(current.id, pauseStart, pauseEnd || undefined, pauseReason || undefined)
    setBusy(false)
    if (res.ok) {
      setDialog(null)
      flash('ok', 'Subscription paused')
      load()
    } else {
      flash('err', res.error)
    }
  }

  async function handleRenew() {
    if (!current) return
    setBusy(true)
    const res = await portalApi.renew(current.id)
    setBusy(false)
    if (res.ok) {
      setDialog(null)
      flash('ok', 'Renewal requested — your new subscription is pending payment')
      load()
    } else {
      flash('err', res.error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4 sm:p-6">
      <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">My Subscription</h1>

      {toast && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            toast.kind === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {subs.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-500">No subscriptions yet</p>
        </div>
      ) : (
        <>
          {current && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{current.plan_name}</h2>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {current.start_date} → {current.end_date}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    STATUS_STYLES[current.status] ?? 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {current.status}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-blue-50 p-3 text-center">
                  <p className="text-xl font-bold text-blue-700">{current.remaining_days}</p>
                  <p className="text-xs text-blue-600">Days Left</p>
                </div>
                <div className="rounded-lg bg-green-50 p-3 text-center">
                  <p className="text-xl font-bold text-green-700">{current.remaining_meals}</p>
                  <p className="text-xs text-green-600">Meals Left</p>
                </div>
                <div className="rounded-lg bg-orange-50 p-3 text-center">
                  <p className="text-xl font-bold text-orange-700">₹{current.pending_amount}</p>
                  <p className="text-xs text-orange-600">Due</p>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <button
              onClick={() => openDialog('skip')}
              disabled={current?.status !== 'ACTIVE'}
              className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-800 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              🍽️ Skip Meal
            </button>
            <button
              onClick={() => openDialog('pause')}
              disabled={current?.status !== 'ACTIVE'}
              className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-800 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ⏸️ Pause Subscription
            </button>
            <button
              onClick={() => openDialog('renew')}
              disabled={current?.status !== 'EXPIRED' && current?.status !== 'CANCELLED'}
              className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-800 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              🔄 Renew
            </button>
          </div>

          {subs.length > 1 && (
            <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
              <p className="border-b border-gray-100 px-5 py-3 text-sm font-medium text-gray-700">History</p>
              <ul className="divide-y divide-gray-100">
                {subs.map((s) => (
                  <li key={s.id} className="flex items-center justify-between px-5 py-3 text-sm">
                    <div>
                      <p className="font-medium text-gray-900">{s.plan_name}</p>
                      <p className="text-xs text-gray-500">
                        {s.start_date} → {s.end_date}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        STATUS_STYLES[s.status] ?? 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {s.status}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Skip dialog */}
      {dialog === 'skip' && (
        <DialogShell title="Skip a Meal" onClose={() => setDialog(null)}>
          <label className="block text-sm font-medium text-gray-700">Date (optional — defaults to today)</label>
          <input
            type="date"
            min={new Date().toISOString().slice(0, 10)}
            value={skipDate}
            onChange={(e) => setSkipDate(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <label className="mt-3 block text-sm font-medium text-gray-700">Reason (optional)</label>
          <input
            value={skipReason}
            onChange={(e) => setSkipReason(e.target.value)}
            placeholder="e.g. Going out of town"
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <DialogActions onCancel={() => setDialog(null)} onConfirm={handleSkip} busy={busy} label="Skip Meal" />
        </DialogShell>
      )}

      {/* Pause dialog */}
      {dialog === 'pause' && (
        <DialogShell title="Pause Subscription" onClose={() => setDialog(null)}>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">From</label>
              <input
                type="date"
                min={new Date().toISOString().slice(0, 10)}
                value={pauseStart}
                onChange={(e) => setPauseStart(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">To (optional)</label>
              <input
                type="date"
                min={pauseStart || undefined}
                value={pauseEnd}
                onChange={(e) => setPauseEnd(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <label className="mt-3 block text-sm font-medium text-gray-700">Reason (optional)</label>
          <input
            value={pauseReason}
            onChange={(e) => setPauseReason(e.target.value)}
            placeholder="e.g. Travelling"
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <DialogActions onCancel={() => setDialog(null)} onConfirm={handlePause} busy={busy} label="Pause" />
        </DialogShell>
      )}

      {/* Renew dialog */}
      {dialog === 'renew' && (
        <DialogShell title="Renew Subscription" onClose={() => setDialog(null)}>
          <p className="text-sm text-gray-600">
            This creates a new <strong>pending</strong> subscription for {current?.plan_name} starting today. Pay at
            the mess to activate it.
          </p>
          <DialogActions onCancel={() => setDialog(null)} onConfirm={handleRenew} busy={busy} label="Renew" />
        </DialogShell>
      )}
    </div>
  )
}

function DialogShell({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function DialogActions({
  onCancel,
  onConfirm,
  busy,
  label,
}: {
  onCancel: () => void
  onConfirm: () => void
  busy: boolean
  label: string
}) {
  return (
    <div className="mt-5 flex justify-end gap-2">
      <button
        onClick={onCancel}
        className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        Cancel
      </button>
      <button
        onClick={onConfirm}
        disabled={busy}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {busy ? 'Working…' : label}
      </button>
    </div>
  )
}
