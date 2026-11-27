import { useState } from 'react'
import { apiClient } from '../../services/apiClient'
import { notify } from '../../utils/notify'
import { confirmDialog } from '../../components/ui/dialog'
import { FEATURES, useFeature } from '../../hooks/useFeature'
import { StatusBadge } from '../../components/ui/StatusBadge'

export interface PortalLogin {
  username: string
  is_active: boolean
}

interface Credentials extends PortalLogin {
  password: string
}

interface Props {
  customerId: string
  customerName: string
  customerPhone: string
  businessName: string
  login: PortalLogin | null
  onChange: (login: PortalLogin | null) => void
}

/** wa.me link to the customer's own number (10-digit Indian numbers get +91). */
function customerWhatsappLink(phone: string, text: string) {
  let digits = phone.replace(/\D/g, '')
  if (digits.length === 10) digits = `91${digits}`
  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`
}

const inputClass =
  'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

/**
 * Owner/manager gives a customer a portal login: username (defaults to phone) + password
 * (typed or auto-generated). The password is shown once, to copy or send on WhatsApp.
 */
export function PortalLoginCard({ customerId, customerName, customerPhone, businessName, login, onChange }: Props) {
  const enabled = useFeature(FEATURES.CUSTOMER_PORTAL)
  const [username, setUsername] = useState(customerPhone)
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [shown, setShown] = useState<Credentials | null>(null)

  if (!enabled) return null

  const base = `/customers/${customerId}/portal-login/`

  async function run(fn: () => Promise<void>, fallback: string) {
    setBusy(true)
    try {
      await fn()
    } catch (err) {
      notify.error(err, fallback)
    } finally {
      setBusy(false)
    }
  }

  function create() {
    return run(async () => {
      const { data } = await apiClient.post<Credentials>(base, { username: username.trim(), password })
      setShown(data)
      setPassword('')
      onChange({ username: data.username, is_active: data.is_active })
      notify.success('Portal login created', 'Share the password with the customer now — it is shown only once.')
    }, 'Could not create the login')
  }

  async function resetPassword() {
    const ok = await confirmDialog({
      title: 'Reset password?',
      message: `${customerName} will be signed out and need the new password to log in again.`,
      confirmText: 'Reset password',
    })
    if (!ok) return
    await run(async () => {
      const { data } = await apiClient.post<Credentials>(`${base}reset-password/`, {})
      setShown(data)
      onChange({ username: data.username, is_active: data.is_active })
      notify.success('New password generated', 'Share it with the customer now — it is shown only once.')
    }, 'Could not reset the password')
  }

  async function setActive(active: boolean) {
    if (!active) {
      const ok = await confirmDialog({
        title: 'Disable portal login?',
        message: `${customerName} won't be able to log in until you enable it again.`,
        confirmText: 'Disable',
        tone: 'danger',
      })
      if (!ok) return
    }
    await run(async () => {
      const { data } = await apiClient.post<PortalLogin>(`${base}${active ? 'enable' : 'disable'}/`)
      onChange(data)
      if (!active) setShown(null)
      notify.success(active ? 'Portal login enabled' : 'Portal login disabled', customerName)
    }, 'Could not update the login')
  }

  const loginUrl = `${window.location.origin}/login`
  const shareText = shown
    ? `Hi ${customerName}, you can now check your meals, payments and skip meals online at ${businessName}.\n\n` +
      `Login: ${loginUrl}\nUsername: ${shown.username}\nPassword: ${shown.password}`
    : ''

  async function copy() {
    try {
      await navigator.clipboard.writeText(shareText)
      notify.success('Copied')
    } catch {
      notify.error(null, 'Could not copy — select the text and copy it manually')
    }
  }

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-gray-900">Customer portal login</h2>
        {login && (
          <StatusBadge status={login.is_active ? 'ACTIVE' : 'DISABLED'} label={login.is_active ? 'Active' : 'Disabled'} />
        )}
      </div>

      {shown && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="mb-2 text-sm font-medium text-amber-800">
            Share these details now — the password won't be shown again.
          </p>
          <dl className="space-y-1 font-mono text-sm text-gray-900">
            <div>
              <dt className="inline text-gray-500">Username: </dt>
              <dd className="inline break-all">{shown.username}</dd>
            </div>
            <div>
              <dt className="inline text-gray-500">Password: </dt>
              <dd className="inline break-all">{shown.password}</dd>
            </div>
          </dl>
          <div className="mt-3 flex flex-wrap gap-2">
            {customerPhone && (
              <a
                href={customerWhatsappLink(customerPhone, shareText)}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
              >
                Send on WhatsApp
              </a>
            )}
            <button
              onClick={copy}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
            >
              Copy
            </button>
            <button onClick={() => setShown(null)} className="px-2 py-1.5 text-xs text-gray-500 hover:underline">
              Done
            </button>
          </div>
        </div>
      )}

      {login ? (
        <div>
          <p className="text-sm text-gray-600">
            Username: <span className="font-mono text-gray-900">{login.username}</span>
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={resetPassword}
              disabled={busy}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Reset password
            </button>
            {login.is_active ? (
              <button
                onClick={() => setActive(false)}
                disabled={busy}
                className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
              >
                Disable login
              </button>
            ) : (
              <button
                onClick={() => setActive(true)}
                disabled={busy}
                className="rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
              >
                Enable login
              </button>
            )}
          </div>
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            create()
          }}
          className="space-y-3"
        >
          <p className="text-sm text-gray-500">
            Let {customerName} log in to see their plan, meals and payments, and skip or pause meals.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-600">Username</span>
              <input
                className={inputClass}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Phone number"
                autoComplete="off"
                required
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-600">Password</span>
              <input
                className={inputClass}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Leave blank to auto-generate"
                autoComplete="new-password"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create login'}
          </button>
        </form>
      )}
    </div>
  )
}
