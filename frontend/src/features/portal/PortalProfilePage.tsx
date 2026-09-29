import { useEffect, useState } from 'react'
import type { PortalProfile } from './portalApi'
import { portalApi } from './portalApi'

export function PortalProfilePage() {
  const [profile, setProfile] = useState<PortalProfile | null>(null)
  const [form, setForm] = useState({ phone: '', email: '', address: '', location: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  const flash = (kind: 'ok' | 'err', msg: string) => {
    setToast({ kind, msg })
    setTimeout(() => setToast(null), 3500)
  }

  useEffect(() => {
    portalApi
      .profile()
      .then((res) => {
        setProfile(res.data)
        setForm({
          phone: res.data.phone ?? '',
          email: res.data.email ?? '',
          address: res.data.address ?? '',
          location: res.data.location ?? '',
        })
      })
      .catch(() => flash('err', 'Failed to load profile'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const { data } = await portalApi.updateProfile(form)
      setProfile(data)
      flash('ok', 'Profile updated')
    } catch {
      flash('err', 'Could not update profile')
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

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900 sm:text-2xl">My Profile</h1>

      {toast && (
        <div
          className={`mb-4 rounded-lg px-4 py-3 text-sm ${
            toast.kind === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
            value={profile?.name ?? ''}
            disabled
            className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
          />
          <p className="mt-1 text-xs text-gray-400">Contact your mess to change your name.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Phone</label>
          <input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Address</label>
          <textarea
            rows={2}
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Location / Landmark</label>
          <input
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 sm:w-auto"
        >
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </form>
    </div>
  )
}
