import { useAuthStore } from '../store/authStore'

/** Shown to staff and customers of a suspended business — the API refuses their requests (BUSINESS_SUSPENDED). */
export function SuspendedNotice() {
  const businessName = useAuthStore((s) => s.user?.business_name)
  return (
    <div role="alert" className="mx-auto mt-12 max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <h2 className="text-lg font-semibold text-red-700">Account temporarily unavailable</h2>
      <p className="mt-2 text-sm text-red-700">
        {businessName ?? 'This mess'}'s account is currently suspended, so this page can't load. Please contact the mess
        owner.
      </p>
    </div>
  )
}
