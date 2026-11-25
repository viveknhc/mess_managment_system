import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Logo } from './ui/Logo'
import { NavIcon, type NavIconName } from './ui/NavIcon'

export interface ShellNavItem {
  to: string
  label: string
  icon: NavIconName
  end?: boolean
  /** Shown greyed out with this explanation instead of a link (e.g. while the account is locked). */
  disabledReason?: string
}

interface Props {
  nav: ShellNavItem[]
  /** Header title (left side), e.g. the business name. */
  title: ReactNode
  /** Small line under the title. */
  subtitle?: ReactNode
  /** Signed-in person, shown as an avatar chip in the header. */
  user: { name: string; role: string }
  onLogout: () => void
  /** Extra header buttons (e.g. notifications), left of the avatar. */
  actions?: ReactNode
  children: ReactNode
}

const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('') || '?'

/**
 * Frame shared by the owner/manager and platform layouts.
 * lg and up: permanent sidebar with icons and labels. Below lg: the same sidebar opens as a drawer.
 */
export function AppShell({ nav, title, subtitle, user, onLogout, actions, children }: Props) {
  const { pathname } = useLocation()
  // The drawer remembers the page it was opened on, so navigating closes it.
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === pathname
  const setOpen = (v: boolean) => setOpenOn(v ? pathname : null)

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpenOn(null)
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])

  const itemBase = 'flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium transition-colors'

  return (
    <div className="flex h-dvh bg-canvas">
      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setOpen(false)} aria-hidden="true" />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-canvas transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 shrink-0 items-center justify-between px-6">
          <Logo light />
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="-mr-2 rounded-full p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
            aria-label="Close menu"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden="true">
              <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-2">
          {nav.map((item) =>
            item.disabledReason ? (
              <span key={item.to} title={item.disabledReason} aria-disabled="true"
                className={`${itemBase} cursor-not-allowed text-gray-300`}>
                <NavIcon name={item.icon} />
                <span className="truncate">{item.label}</span>
              </span>
            ) : (
              <NavLink key={item.to} to={item.to} end={item.end}
                className={({ isActive }) =>
                  `${itemBase} ${isActive ? 'bg-accent text-accent-ink' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-900'}`
                }>
                <NavIcon name={item.icon} />
                <span className="truncate">{item.label}</span>
              </NavLink>
            ),
          )}
        </nav>

        <div className="shrink-0 border-t border-gray-200 px-4 py-4">
          <button type="button" onClick={onLogout}
            className={`${itemBase} w-full text-gray-500 hover:bg-gray-100 hover:text-gray-900`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-5 w-5 shrink-0" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l4-4-4-4M14 12H4" />
            </svg>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 px-3 sm:h-20 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button type="button" onClick={() => setOpen(true)} aria-label="Open menu" aria-expanded={open}
              className="rounded-full p-2 text-gray-600 hover:bg-gray-100 lg:hidden">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6" aria-hidden="true">
                <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="min-w-0">
              <h2 className="truncate text-lg font-semibold text-gray-900 sm:text-xl">{title}</h2>
              {subtitle && <p className="truncate text-xs text-gray-500">{subtitle}</p>}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            {actions}
            <div className="flex items-center gap-2.5">
              <span aria-hidden="true"
                className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-sm font-bold text-accent-ink">
                {initials(user.name)}
              </span>
              <span className="hidden leading-tight md:block">
                <span className="block text-sm font-medium text-gray-900">{user.name}</span>
                <span className="block text-xs text-gray-500">{user.role}</span>
              </span>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
