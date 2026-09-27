import { useEffect, useState, type FormEvent, type ChangeEvent } from 'react'
import { useBusinessStore } from '../../store/businessStore'
import { useAuthStore } from '../../store/authStore'

export function BusinessProfilePage() {
  const { business, isLoading, error, fetchBusiness, updateBusiness, uploadLogo } =
    useBusinessStore()
  const user = useAuthStore((s) => s.user)
  const isOwner = user?.role === 'OWNER'

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', email: '', address: '' })
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    fetchBusiness()
  }, [fetchBusiness])

  useEffect(() => {
    if (business) {
      setForm({
        name: business.name,
        phone: business.phone,
        email: business.email,
        address: business.address,
      })
    }
  }, [business])

  function handleChange(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    await updateBusiness(form)
    setEditing(false)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  function handleCancel() {
    if (business) {
      setForm({
        name: business.name,
        phone: business.phone,
        email: business.email,
        address: business.address,
      })
    }
    setEditing(false)
  }

  async function handleLogoChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      await uploadLogo(file)
    }
  }

  if (isLoading && !business) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!business) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error || 'No business found'}
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Business Profile</h1>
        {isOwner && !editing && (
          <button
            onClick={() => setEditing(true)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Edit
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {saveSuccess && (
        <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
          Business profile updated successfully
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        {/* Logo section */}
        <div className="flex items-center gap-4 border-b border-gray-100 p-6">
          <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-xl bg-blue-50 text-2xl font-bold text-blue-600">
            {business.logo ? (
              <img
                src={business.logo}
                alt={business.name}
                className="h-full w-full object-cover"
              />
            ) : (
              business.name.charAt(0).toUpperCase()
            )}
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-gray-900">{business.name}</h2>
            <span
              className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                business.status === 'ACTIVE'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {business.status}
            </span>
          </div>
          {isOwner && (
            <label className="cursor-pointer rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
              {business.logo ? 'Change Logo' : 'Upload Logo'}
              <input
                type="file"
                accept="image/*"
                onChange={handleLogoChange}
                className="hidden"
              />
            </label>
          )}
        </div>

        {/* Form / Read-only fields */}
        {editing ? (
          <form onSubmit={handleSubmit} className="space-y-4 p-6">
            <div>
              <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700">
                Business Name
              </label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="phone" className="mb-1 block text-sm font-medium text-gray-700">
                Phone
              </label>
              <input
                id="phone"
                name="phone"
                value={form.phone}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="address" className="mb-1 block text-sm font-medium text-gray-700">
                Address
              </label>
              <textarea
                id="address"
                name="address"
                value={form.address}
                onChange={handleChange}
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <dl className="divide-y divide-gray-100 p-6">
            <div className="flex py-3 first:pt-0 last:pb-0">
              <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Phone</dt>
              <dd className="text-sm text-gray-900">{business.phone || '—'}</dd>
            </div>
            <div className="flex py-3 first:pt-0 last:pb-0">
              <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Email</dt>
              <dd className="text-sm text-gray-900">{business.email || '—'}</dd>
            </div>
            <div className="flex py-3 first:pt-0 last:pb-0">
              <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Address</dt>
              <dd className="text-sm text-gray-900">{business.address || '—'}</dd>
            </div>
          </dl>
        )}
      </div>
    </div>
  )
}
