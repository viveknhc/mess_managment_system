import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { getApiErrorMessage } from '../../utils/apiError'

const inputClass =
  'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none'

/** Opened from the emailed link: /reset-password?uid=…&token=… */
export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError("The two passwords don't match.")
      return
    }
    setLoading(true)
    try {
      await apiClient.post('/auth/password-reset/confirm/', { uid, token, new_password: password })
      setDone(true)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Could not reset the password. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  let body
  if (!uid || !token) {
    body = (
      <p className="text-sm text-gray-700">
        This reset link is incomplete. Open the link from the email again, or{' '}
        <Link to="/forgot-password" className="font-medium text-blue-600">ask for a new one</Link>.
      </p>
    )
  } else if (done) {
    body = (
      <div role="status" className="space-y-4 text-sm">
        <p className="rounded-lg bg-green-50 px-4 py-3 text-green-800">
          Password changed. You've been signed out on other devices.
        </p>
        <Link
          to="/login"
          className="block w-full rounded-lg bg-blue-600 px-4 py-2.5 text-center font-medium text-white hover:bg-blue-700"
        >
          Sign in
        </Link>
      </div>
    )
  } else {
    body = (
      <form onSubmit={handleSubmit}>
        {error && (
          <div role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
            {error.includes('expired') && (
              <>
                {' '}
                <Link to="/forgot-password" className="font-medium underline">Get a new link</Link>
              </>
            )}
          </div>
        )}
        <div className="mb-4">
          <label htmlFor="new-password" className="mb-1 block text-sm font-medium text-gray-700">New password</label>
          <input id="new-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            required minLength={8} autoFocus autoComplete="new-password" className={inputClass} />
          <p className="mt-1 text-xs text-gray-500">At least 8 characters, not only numbers, not too common.</p>
        </div>
        <div className="mb-6">
          <label htmlFor="confirm-password" className="mb-1 block text-sm font-medium text-gray-700">Confirm new password</label>
          <input id="confirm-password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
            required autoComplete="new-password" className={inputClass} />
        </div>
        <button type="submit" disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {loading ? 'Saving...' : 'Set new password'}
        </button>
      </form>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Set a new password</h1>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">{body}</div>
        {!done && (
          <p className="mt-4 text-center text-sm">
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-700">Back to sign in</Link>
          </p>
        )}
      </div>
    </div>
  )
}
