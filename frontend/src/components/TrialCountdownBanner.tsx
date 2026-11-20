import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const DAY = 86_400_000

function pad(n: number) {
  return String(n).padStart(2, '0')
}

/** "6d 23h 59m 08s" */
function formatLeft(ms: number) {
  const total = Math.max(0, Math.floor(ms / 1000))
  const d = Math.floor(total / 86_400)
  const h = Math.floor((total % 86_400) / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${d}d ${pad(h)}h ${pad(m)}m ${pad(s)}s`
}

/**
 * Live countdown for the 7-day free trial a SUPER_ADMIN started. Ticks every second on its own
 * (so the rest of the layout doesn't re-render) and calls onEnd once when time runs out.
 */
export function TrialCountdownBanner({ endsAt, onEnd }: { endsAt: string; onEnd: () => void }) {
  const end = Date.parse(endsAt)
  const [now, setNow] = useState(() => Date.now())
  const left = end - now

  useEffect(() => {
    if (left <= 0) {
      onEnd()
      return
    }
    const id = window.setTimeout(() => setNow(Date.now()), Math.min(1000, left))
    return () => window.clearTimeout(id)
  }, [left, onEnd])

  if (left <= 0) return null
  const lastDay = left < DAY
  const endsLabel = new Date(end).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })

  return (
    <div
      role="status"
      className={`flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-b px-4 py-2.5 text-center text-sm sm:px-6 ${
        lastDay ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-blue-200 bg-blue-50 text-blue-800'
      }`}
    >
      <span className="font-medium">Free trial</span>
      <span className="rounded-md bg-white/70 px-2 py-0.5 font-mono font-semibold tabular-nums" aria-label="Time left in free trial">
        {formatLeft(left)}
      </span>
      <span>
        left (ends {endsLabel}).{' '}
        <Link to="/app/billing#pay" className="font-medium underline">
          Complete your first payment
        </Link>{' '}
        to keep using MessDeck after the trial.
      </span>
    </div>
  )
}
