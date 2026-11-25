import { useState, type FormEvent } from 'react'
import { Logo } from '../../components/ui/Logo'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/app')
    } catch {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  const input =
    'w-full rounded-full border border-gray-300 bg-gray-50 px-5 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-accent focus:ring-2 focus:ring-accent/30 focus:outline-none'

  return (
    <div className="relative flex min-h-screen bg-canvas p-3 sm:p-4">
      <Showcase />

      {/* Form side */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-10">
        {/* soft glow behind the form on phones, where the showcase is hidden */}
        <div aria-hidden="true" className="pointer-events-none absolute -top-32 left-1/2 h-80 w-80 -translate-x-1/2 rounded-full bg-accent/15 blur-3xl lg:hidden" />

        <div className="relative w-full max-w-sm">
          <h1 className="mb-10 flex justify-center lg:justify-start"><Logo size="lg" light /></h1>

          <h2 className="text-3xl font-light tracking-tight text-gray-900">Welcome back</h2>
          <p className="mt-1.5 mb-8 text-sm text-gray-500">Sign in to your account to manage your mess.</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div role="alert" className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="username" className="mb-1.5 block pl-1 text-sm font-medium text-gray-700">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                placeholder="Your username or phone"
                className={input}
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between pl-1">
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  Password
                </label>
                <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={`${input} pr-12`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  aria-controls="password"
                  className="absolute inset-y-0 right-0 flex items-center px-4 text-gray-500 hover:text-gray-700 focus:text-gray-700 focus:outline-none"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49" />
                      <path d="M14.084 14.158a3 3 0 0 1-4.242-4.242" />
                      <path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143" />
                      <path d="m2 2 20 20" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group flex w-full items-center justify-between rounded-full bg-blue-600 py-1.5 pr-1.5 pl-6 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign in'}
              <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-ink text-accent transition-transform group-hover:translate-x-0.5">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 17 17 7M8 7h9v9" />
                </svg>
              </span>
            </button>
          </form>

          <p className="mt-10 text-center text-xs text-gray-500 lg:text-left">
            New to MessDeck? <Link to="/" className="font-medium text-gray-700 underline-offset-2 hover:underline">See how it works</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

/** Decorative brand panel (desktop only): glow, dot grid, headline and a mini dashboard made of the app's own pieces. */
function Showcase() {
  const bars = [38, 52, 46, 70, 88, 64, 96]
  return (
    <aside aria-hidden="true"
      className="relative hidden w-[52%] max-w-3xl flex-col justify-between overflow-hidden rounded-[2rem] border border-gray-200 bg-white p-10 lg:flex xl:p-14">
      {/* glow + dot grid */}
      <div className="pointer-events-none absolute -top-40 -right-40 h-[28rem] w-[28rem] rounded-full bg-accent/25 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-48 -left-32 h-96 w-96 rounded-full bg-accent/10 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(var(--color-gray-300)_1px,transparent_1px)] [background-size:22px_22px] [mask-image:linear-gradient(to_bottom,black,transparent_85%)]" />

      <div className="relative">
        <span className="inline-flex items-center gap-2 rounded-full border border-gray-300 px-3.5 py-1.5 text-xs text-gray-700">
          <span className="h-2 w-2 rounded-full bg-accent" />
          Mess management, made simple
        </span>
        <p className="mt-6 max-w-md text-4xl leading-tight font-light tracking-tight text-gray-900 xl:text-5xl">
          Run your mess <span className="text-accent">like clockwork.</span>
        </p>
        <p className="mt-4 max-w-sm text-sm leading-relaxed text-gray-500">
          Customers, plans, payments and every day's deliveries — in one place, for owners, staff and customers.
        </p>
      </div>

      {/* mini dashboard */}
      <div className="relative mt-10 grid grid-cols-5 gap-3">
        <div className="col-span-2 flex flex-col justify-between rounded-3xl bg-accent p-5 text-accent-ink">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium">Meals today</span>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-ink text-accent">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-3.5 w-3.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 17 17 7M8 7h9v9" />
              </svg>
            </span>
          </div>
          <p className="mt-8 text-4xl font-light">128 <span className="text-xs opacity-70">+12 vs last week</span></p>
        </div>

        <div className="col-span-3 rounded-3xl border border-gray-200 bg-gray-50/60 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm text-gray-900">Activity</span>
            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[10px] text-gray-600">This week</span>
          </div>
          <div className="flex h-24 items-end gap-2">
            {bars.map((h, i) => (
              <div key={i} className={`flex-1 rounded-t-md ${h > 80 ? 'bg-accent' : h > 50 ? 'bg-gray-700' : 'bg-gray-300'}`} style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>

        {/* floating chips */}
        <div className="col-span-3 flex items-center gap-3 rounded-full border border-gray-200 bg-gray-50/80 py-2 pr-4 pl-2 backdrop-blur">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-green-100 text-green-700">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="m5 12 5 5L20 7" />
            </svg>
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm text-gray-900">₹2,500 received</span>
            <span className="block text-[11px] text-gray-500">UPI · Monthly Lunch</span>
          </span>
        </div>
        <div className="col-span-2 flex items-center gap-3 rounded-full border border-gray-200 bg-gray-50/80 py-2 pr-4 pl-2 backdrop-blur">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-ink">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h11v9H3zM14 10h4l3 3v3h-7M7 19a2 2 0 1 0 0-.01M17 19a2 2 0 1 0 0-.01" />
            </svg>
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm text-gray-900">Delivered</span>
            <span className="block text-[11px] text-gray-500">42 of 45 today</span>
          </span>
        </div>
      </div>

      <p className="relative mt-10 text-xs text-gray-400">© MessDeck</p>
    </aside>
  )
}
