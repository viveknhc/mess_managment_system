import type { ReactNode } from 'react'

type Tone = 'green' | 'yellow' | 'blue' | 'red' | 'gray' | 'orange' | 'purple' | 'amber'

const TONES: Record<Tone, string> = {
  green: 'bg-green-50 text-green-700',
  yellow: 'bg-yellow-50 text-yellow-700',
  blue: 'bg-blue-50 text-blue-700',
  red: 'bg-red-50 text-red-700',
  gray: 'bg-gray-100 text-gray-600',
  orange: 'bg-orange-50 text-orange-700',
  purple: 'bg-purple-50 text-purple-700',
  amber: 'bg-amber-50 text-amber-800',
}

/** Lucide-style outline icons, 24×24 viewBox, stroke = currentColor. */
const ICONS = {
  check: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </>
  ),
  truck: (
    <>
      <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2" />
      <path d="M15 18H9" />
      <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14" />
      <circle cx="17" cy="18" r="2" />
      <circle cx="7" cy="18" r="2" />
    </>
  ),
  pause: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M10 15V9M14 15V9" />
    </>
  ),
  hourglass: (
    <>
      <path d="M5 22h14M5 2h14" />
      <path d="M17 22v-4.17a2 2 0 0 0-.59-1.42L12 12l-4.41 4.41A2 2 0 0 0 7 17.83V22" />
      <path d="M7 2v4.17a2 2 0 0 0 .59 1.42L12 12l4.41-4.41A2 2 0 0 0 17 6.17V2" />
    </>
  ),
  x: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m15 9-6 6M9 9l6 6" />
    </>
  ),
  alert: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" />
    </>
  ),
  ban: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m4.9 4.9 14.2 14.2" />
    </>
  ),
  skip: (
    <>
      <path d="m5 4 10 8-10 8V4z" />
      <path d="M19 5v14" />
    </>
  ),
  minus: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M8 12h8" />
    </>
  ),
  undo: (
    <>
      <path d="M3 7v6h6" />
      <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
    </>
  ),
  gift: (
    <>
      <rect x="3" y="8" width="18" height="4" rx="1" />
      <path d="M12 8v13M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7" />
      <path d="M7.5 8a2.5 2.5 0 0 1 0-5C9.5 3 12 8 12 8s2.5-5 4.5-5a2.5 2.5 0 0 1 0 5" />
    </>
  ),
  warning: (
    <>
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
      <path d="M12 9v4M12 17h.01" />
    </>
  ),
  dot: <circle cx="12" cy="12" r="4" />,
  sliders: (
    <>
      <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3" />
      <path d="M2 14h4M10 8h4M18 16h4" />
    </>
  ),
} satisfies Record<string, ReactNode>

type IconName = keyof typeof ICONS

/** One look per status, everywhere in the app. Keys are the API values (plus a few UI states). */
const STATUSES: Record<string, { tone: Tone; icon: IconName }> = {
  ACTIVE: { tone: 'green', icon: 'check' },
  PAID: { tone: 'green', icon: 'check' },
  DELIVERED: { tone: 'green', icon: 'check' },
  ON: { tone: 'green', icon: 'check' },
  PENDING: { tone: 'yellow', icon: 'clock' },
  OUT_FOR_DELIVERY: { tone: 'blue', icon: 'truck' },
  PAUSED: { tone: 'blue', icon: 'pause' },
  TRIAL: { tone: 'purple', icon: 'gift' },
  PAST_DUE: { tone: 'orange', icon: 'warning' },
  EXPIRED: { tone: 'gray', icon: 'hourglass' },
  CANCELLED: { tone: 'red', icon: 'x' },
  NOT_DELIVERED: { tone: 'red', icon: 'alert' },
  FAILED: { tone: 'red', icon: 'alert' },
  BLOCKED: { tone: 'red', icon: 'ban' },
  SUSPENDED: { tone: 'red', icon: 'ban' },
  SKIPPED: { tone: 'gray', icon: 'skip' },
  REFUNDED: { tone: 'purple', icon: 'undo' },
  INACTIVE: { tone: 'gray', icon: 'minus' },
  DISABLED: { tone: 'gray', icon: 'minus' },
  OFF: { tone: 'gray', icon: 'minus' },
  DEFAULT: { tone: 'gray', icon: 'dot' },
  CUSTOM: { tone: 'amber', icon: 'sliders' },
}

/**
 * Status pill with an icon: flat, borderless, rounded-full — never looks like a button
 * (see ActionButton). ``label`` defaults to the status with underscores as spaces.
 */
export function StatusBadge({
  status,
  label,
  size = 'sm',
  className = '',
}: {
  status: string
  label?: ReactNode
  size?: 'sm' | 'md'
  className?: string
}) {
  const look = STATUSES[status] ?? { tone: 'gray' as Tone, icon: 'dot' as IconName }
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full font-medium ${
        size === 'md' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-xs'
      } ${TONES[look.tone]} ${className}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.25}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-3.5 w-3.5 shrink-0"
        aria-hidden="true"
      >
        {ICONS[look.icon]}
      </svg>
      {label ?? status.replace(/_/g, ' ')}
    </span>
  )
}
