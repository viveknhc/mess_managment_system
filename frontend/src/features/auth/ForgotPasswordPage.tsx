import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { getApiErrorMessage } from '../../utils/apiError'

const inputClass =
  'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none'

export function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState('')
  const [sent, setSent] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await apiClient.post('/auth/password-reset/', { identifier })
      setSent(data.detail)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Could not send the reset link. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Forgot password</h1>
          <p className="mt-1 text-sm text-gray-500">We'll email you a link to set a new one</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {sent ? (
            <div role="status" className="space-y-3 text-sm text-gray-700">
              <p className="rounded-lg bg-green-50 px-4 py-3 text-green-800">{sent}</p>
              <p>The link works once and expires in 1 hour. Check your spam folder if it doesn't arrive.</p>
              <p className="text-gray-500">
                No email on your account? Ask your mess owner to add one, then try again. Mess owners can
                contact MessDeck support.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
              <div className="mb-6">
                <label htmlFor="identifier" className="mb-1 block text-sm font-medium text-gray-700">
                  Username or email
                </label>
                <input
                  id="identifier"
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                  autoFocus
                  autoComplete="username"
                  className={inputClass}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send reset link'}
              </button>
            </form>
          )}
        </div>

        <p className="mt-4 text-center text-sm">
          <Link to="/login" className="font-medium text-blue-600 hover:text-blue-700">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
