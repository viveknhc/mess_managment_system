import { useEffect, useState, type FormEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'

interface Settings {
  max_skip_days: number
  min_pause_days: number
  max_pause_days: number
  skip_rule: string
  delivery_start_time: string | null
  delivery_end_time: string | null
  notify_on_payment: boolean
  notify_on_expiring: boolean
  notify_on_delivery: boolean
}

const SKIP_RULES = [
  { value: 'NONE', label: 'No adjustment' },
  { value: 'EXTEND', label: 'Extend subscription end date' },
  { value: 'CREDIT', label: 'Meal credit' },
]

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const user = useAuthStore((s) => s.user)
  const isOwner = user?.role === 'OWNER'

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
      const { data } = await apiClient.put('/settings/', settings)
      setSettings(data)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch {
      setError('Failed to save settings')
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
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">Business Settings</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {success && <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">Settings saved</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Skip/Pause rules */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900 uppercase tracking-wide">Skip & Pause Rules</h2>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Skip Rule</label>
              <select value={settings.skip_rule} onChange={(e) => setSettings({ ...settings, skip_rule: e.target.value })}
                disabled={!isOwner} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:opacity-50">
                {SKIP_RULES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Max Skip Days</label>
                <input type="number" min="0" value={settings.max_skip_days}
                  onChange={(e) => setSettings({ ...settings, max_skip_days: Number(e.target.value) })}
                  disabled={!isOwner} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:opacity-50" />
              </div>
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
