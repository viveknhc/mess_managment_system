import { businessLock, trialEnded, useAuthStore } from '../store/authStore'

/** Shown to staff and customers of a locked business — the API refuses their requests (BUSINESS_SUSPENDED / PAYMENT_REQUIRED). */
export function SuspendedNotice() {
  const businessName = useAuthStore((s) => s.user?.business_name)
  const notActivated = useAuthStore((s) => businessLock(s.user) === 'PAYMENT_REQUIRED')
  const trialOver = useAuthStore((s) => trialEnded(s.user))
  return (
    <div role="alert" className="mx-auto mt-12 max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <h2 className="text-lg font-semibold text-red-700">Account temporarily unavailable</h2>
      <p className="mt-2 text-sm text-red-700">
        {businessName ?? 'This mess'}'s account is {trialOver ? 'waiting for payment after its free trial' : notActivated ? 'not activated yet' : 'currently suspended'}, so this page
        can't load. Please contact the mess owner.
      </p>
    </div>
  )
}
