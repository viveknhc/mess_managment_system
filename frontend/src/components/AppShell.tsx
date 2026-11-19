import { useEffect, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

interface Props {
  /** Sidebar brand line, e.g. "Mess Manager". */
  brand: ReactNode
  /** Nav links. Rendered in the fixed sidebar on desktop and a slide-in drawer on phones. */
  nav: ReactNode
  /** Header title (left side). */
  title: ReactNode
  /** Header actions (right side). */
  actions: ReactNode
  /** Extra items shown at the bottom of the drawer on phones (e.g. user name + logout). */
  drawerFooter?: ReactNode
  children: ReactNode
}

/**
 * Sidebar + header frame shared by the Admin and Platform layouts.
 * lg and up: permanent 16rem sidebar. Below lg: hamburger opens the sidebar as a drawer.
 */
export function AppShell({ brand, nav, title, actions, drawerFooter, children }: Props) {
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

  return (
    <div className="flex h-dvh">
      {open && (
        <div className="fixed inset-0 z-40 bg-gray-900/50 lg:hidden" onClick={() => setOpen(false)} aria-hidden="true" />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? 'translate-x-0 shadow-xl' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 px-6">
          {brand}
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="-mr-2 rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
            aria-label="Close menu"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden="true">
              <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-4">{nav}</nav>
        {drawerFooter && <div className="border-t border-gray-200 p-4 lg:hidden">{drawerFooter}</div>}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-gray-200 bg-white px-3 sm:h-16 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 lg:hidden"
              aria-label="Open menu"
              aria-expanded={open}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6" aria-hidden="true">
                <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="truncate text-base font-semibold text-gray-800 sm:text-lg">{title}</h2>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-4">{actions}</div>
        </header>
        <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
      </div>
    </div>
  )
}
