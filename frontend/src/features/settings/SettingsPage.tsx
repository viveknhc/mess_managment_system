import { useEffect, useState, type FormEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { FEATURES, useFeature } from '../../hooks/useFeature'
import { getApiErrorMessage } from '../../utils/apiError'
import { notify } from '../../utils/notify'

interface Settings {
  min_pause_days: number
  max_pause_days: number
  /** Chosen by MessDeck (SUPER_ADMIN) per business — read-only here. */
  skip_policy: { key: string; label: string; description: string }
  /** Days the kitchen is closed every week: 0=Monday … 6=Sunday. */
  weekly_off_days: number[]
  delivery_start_time: string | null
  delivery_end_time: string | null
  notify_on_payment: boolean
  notify_on_expiring: boolean
  notify_on_delivery: boolean
  online_payments_enabled: boolean
  razorpay_key_id: string
  razorpay_configured: boolean
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [keySecret, setKeySecret] = useState('') // write-only; never loaded back
  const user = useAuthStore((s) => s.user)
  const refreshUser = useAuthStore((s) => s.refreshUser)
  const isOwner = user?.role === 'OWNER'
  const onlinePayments = useFeature(FEATURES.ONLINE_PAYMENTS)
  // Razorpay calls this when a customer pays, so payments are recorded even if they close the app first
  const webhookUrl = user?.business_id
    ? new URL(`${apiClient.defaults.baseURL}/webhooks/razorpay/mess/${user.business_id}/`, window.location.origin).href
    : ''

  async function copyWebhookUrl() {
    try {
      await navigator.clipboard.writeText(webhookUrl)
      notify.success('Webhook URL copied')
    } catch {
      notify.error('Could not copy. Select the URL and copy it yourself.')
    }
  }

  useEffect(() => {
    apiClient.get('/settings/').then((res) => {
      setSettings(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!settings) return
    setSaving(true)
    setError('')
    try {
      const body = keySecret ? { ...settings, razorpay_key_secret: keySecret } : settings
      const { data } = await apiClient.put('/settings/', body)
      setSettings(data)
      setKeySecret('')
      notify.success('Settings saved')
      refreshUser() // the "kitchen closed" notice in the header reads the closed days from the user
    } catch (e) {
      // Inline banner sits at the top of a long form; the toast makes sure it's noticed.
      setError(getApiErrorMessage(e, 'Failed to save settings'))
      notify.error(e, 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!settings) return <div className="p-6 text-gray-500">Failed to load settings</div>

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">Business Settings</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Kitchen closed days */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-1 text-sm font-semibold text-gray-900 uppercase tracking-wide">Kitchen Closed On</h2>
          <p className="mb-4 text-sm text-gray-500">
            No meals are delivered on these days. Customers still get every meal in their plan: the plan ends later instead.
            Changing this moves upcoming meals of current subscriptions too.
          </p>
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map((label, i) => {
              const closed = settings.weekly_off_days.includes(i)
              return (
                <label key={label}
                  className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm has-[:disabled]:cursor-default has-[:disabled]:opacity-50 ${
                    closed ? 'border-red-300 bg-red-50 text-red-700' : 'border-gray-300 text-gray-700'
                  }`}>
                  <input type="checkbox" checked={closed} disabled={!isOwner}
                    onChange={(e) => setSettings({
                      ...settings,
                      weekly_off_days: e.target.checked
                        ? [...settings.weekly_off_days, i].sort((a, b) => a - b)
                        : settings.weekly_off_days.filter((d) => d !== i),
                    })}
                    className="h-4 w-4 rounded border-gray-300 text-red-600" />
                  {label}
                </label>
              )
            })}
          </div>
          {settings.weekly_off_days.length === 7 && (
            <p className="mt-2 text-xs text-red-600">The kitchen must be open at least one day a week.</p>
          )}
        </div>

        {/* Skip/Pause rules */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Skip & Pause Rules</h2>
          <div className="space-y-4">
            <div>
              <p className="mb-1 text-sm font-medium text-gray-700">When a meal is skipped</p>
              <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-800">
                <span className="font-medium">{settings.skip_policy.label}</span>: {settings.skip_policy.description}
              </p>
              <p className="mt-1 text-xs text-gray-500">Set up by MessDeck for your mess. Contact support to change it.</p>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Min Pause Days</label>
                <input type="number" min="1" value={settings.min_pause_days}
                  onChange={(e) => setSettings({ ...settings, min_pause_days: Number(e.target.value) })}
                  disabled={!isOwner} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:opacity-50" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Max Pause Days</label>
                <input type="number" min="1" value={settings.max_pause_days}
                  onChange={(e) => setSettings({ ...settings, max_pause_days: Number(e.target.value) })}
                  disabled={!isOwner} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:opacity-50" />
              </div>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Notification Preferences</h2>
          <div className="space-y-3">
            {[
              { key: 'notify_on_payment' as const, label: 'Payment received' },
              { key: 'notify_on_expiring' as const, label: 'Subscription expiring' },
              { key: 'notify_on_delivery' as const, label: 'Delivery updates' },
            ].map((item) => (
              <label key={item.key} className="flex items-center gap-3 text-sm text-gray-700">
                <input type="checkbox" checked={settings[item.key]}
                  onChange={(e) => setSettings({ ...settings, [item.key]: e.target.checked })}
                  disabled={!isOwner} className="h-4 w-4 rounded border-gray-300 text-blue-600" />
                {item.label}
              </label>
            ))}
          </div>
        </div>

        {/* Online payments */}
        {!onlinePayments ? (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-1 text-sm font-semibold text-gray-900 uppercase tracking-wide">Online Payments</h2>
            <p className="text-sm text-gray-500">Not included for your mess. Contact MessDeck support to enable it.</p>
          </div>
        ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-1 text-sm font-semibold text-gray-900 uppercase tracking-wide">Online Payments</h2>
          <p className="mb-4 text-sm text-gray-500">
            Let customers pay for their subscription in the app. Money goes straight to your own Razorpay account.
            Get your keys in the Razorpay Dashboard → Account &amp; Settings → API Keys.
          </p>
          <div className="space-y-4">
            <div>
              <label htmlFor="rzp-key-id" className="mb-1 block text-sm font-medium text-gray-700">Key ID</label>
              <input id="rzp-key-id" value={settings.razorpay_key_id} placeholder="rzp_live_…"
                onChange={(e) => setSettings({ ...settings, razorpay_key_id: e.target.value.trim() })}
                disabled={!isOwner} autoComplete="off"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm disabled:opacity-50" />
            </div>
            {isOwner && (
              <div>
                <label htmlFor="rzp-key-secret" className="mb-1 block text-sm font-medium text-gray-700">Key Secret</label>
                <input id="rzp-key-secret" type="password" value={keySecret} autoComplete="new-password"
                  placeholder={settings.razorpay_configured ? 'Saved. Type a new one to replace it' : 'Paste your key secret'}
                  onChange={(e) => setKeySecret(e.target.value.trim())}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm" />
                <p className="mt-1 text-xs text-gray-500">Stored encrypted and never shown again. Clear the Key ID and save to remove your keys.</p>
              </div>
            )}
            <label className="flex items-center gap-3 text-sm text-gray-700">
              <input type="checkbox" checked={settings.online_payments_enabled}
                onChange={(e) => setSettings({ ...settings, online_payments_enabled: e.target.checked })}
                disabled={!isOwner} className="h-4 w-4 rounded border-gray-300 text-blue-600" />
              Customers can pay online
            </label>
            {isOwner && webhookUrl && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <p className="text-sm font-medium text-gray-700">Webhook (recommended)</p>
                <p className="mt-1 text-xs text-gray-500">
                  Records a payment even if the customer closes the app before it finishes. In the Razorpay Dashboard →
                  Account &amp; Settings → Webhooks, add this URL with the events <b>payment.captured</b> and{' '}
                  <b>order.paid</b>. Leave the secret blank.
                </p>
                <div className="mt-2 flex gap-2">
                  <input readOnly value={webhookUrl} onFocus={(e) => e.target.select()} aria-label="Webhook URL"
                    className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-xs" />
                  <button type="button" onClick={copyWebhookUrl}
                    className="shrink-0 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">
                    Copy
                  </button>
                </div>
              </div>
            )}
            {settings.razorpay_key_id.startsWith('rzp_test_') && settings.online_payments_enabled && (
              <p className="rounded-lg bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
                Test keys: payments are simulated and no real money is collected.
              </p>
            )}
          </div>
        </div>
        )}

        {isOwner && (
          <button type="submit" disabled={saving}
            className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        )}
      </form>
    </div>
  )
}
