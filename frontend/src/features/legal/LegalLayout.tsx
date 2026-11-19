import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from '../landing/Logo'
import { LEGAL_NAME } from '../../config/support'
import { LAST_UPDATED, LEGAL_LINKS } from './links'

/** Shared shell for the public policy pages that payment gateways review. */
export function LegalLayout({ title, children }: { title: string; children: React.ReactNode }) {
  useEffect(() => {
    document.title = `${title} · MessDeck`
    window.scrollTo(0, 0)
  }, [title])

  return (
    <div className="min-h-screen bg-cream">
      <header className="border-b border-brand-100 bg-cream/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4 sm:px-6">
          <Link to="/" aria-label="MessDeck home">
            <Logo />
          </Link>
          <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-brand-800">
            Login
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
        <h1 className="text-2xl font-bold text-brand-900 sm:text-3xl">{title}</h1>
        <p className="mt-2 text-sm text-gray-500">Last updated: {LAST_UPDATED}</p>
        <div className="mt-8 space-y-6 text-[15px] leading-relaxed text-gray-700">{children}</div>
      </main>

      <footer className="border-t border-brand-100 py-8">
        <div className="mx-auto max-w-3xl px-4 sm:px-6">
          <nav className="flex flex-wrap gap-x-5 gap-y-2">
            {LEGAL_LINKS.map((l) => (
              <Link key={l.to} to={l.to} className="text-sm text-gray-600 hover:text-brand-800">
                {l.label}
              </Link>
            ))}
          </nav>
          <p className="mt-4 text-xs text-gray-500">
            &copy; {new Date().getFullYear()} {LEGAL_NAME}. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold text-brand-900">{title}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  )
}

export function Bullets({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}
