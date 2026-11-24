import { useEffect, type ReactNode } from 'react'

interface Props {
  webhookUrl: string
  onClose: () => void
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
        {n}
      </span>
      <div className="min-w-0 text-sm text-gray-600">
        <p className="font-medium text-gray-900">{title}</p>
        <div className="mt-1 space-y-1">{children}</div>
      </div>
    </li>
  )
}

/** Step-by-step guide for an owner connecting their own Razorpay account and webhook. */
export function OnlinePaymentsHelpModal({ webhookUrl, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const isLocal = /\/\/(localhost|127\.0\.0\.1)/.test(webhookUrl)

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="online-payments-help-title"
        className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 shadow-lg sm:rounded-xl sm:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="online-payments-help-title" className="text-lg font-bold text-gray-900">
            How to collect payments online
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        <p className="mb-4 text-sm text-gray-600">
          Customers pay from their app with UPI, card or netbanking. The money goes straight to <b>your own Razorpay
          account</b> and Razorpay sends it to your bank (usually in 2 working days, minus Razorpay's fee).
        </p>

        <ol className="space-y-4">
          <Step n={1} title="Create a Razorpay account">
            <p>Sign up at razorpay.com and finish KYC (PAN, bank account, business details). Real payments only start
              after Razorpay approves your KYC.</p>
          </Step>
          <Step n={2} title="Copy your API keys">
            <p>Razorpay Dashboard → <b>Account &amp; Settings → API Keys → Generate Key</b> (in Live mode).</p>
            <p>Copy the <b>Key ID</b> (starts with <code className="text-xs">rzp_live_</code>) and the <b>Key Secret</b>.
              Razorpay shows the secret only once, so keep it safe.</p>
          </Step>
          <Step n={3} title="Paste them here">
            <p>Paste both keys on this page, tick <b>Customers can pay online</b>, and click <b>Save Settings</b>.</p>
          </Step>
          <Step n={4} title="Add the webhook (recommended)">
            <p>Razorpay Dashboard → <b>Account &amp; Settings → Webhooks → Add New Webhook</b>:</p>
            <ul className="list-disc space-y-0.5 pl-5">
              <li><b>Webhook URL:</b> the URL from the Copy button on this page</li>
              <li><b>Secret:</b> leave it blank</li>
              <li><b>Active events:</b> tick <code className="text-xs">payment.captured</code> and{' '}
                <code className="text-xs">order.paid</code></li>
            </ul>
            <p>This records a payment even if the customer closes the app or loses network right after paying.</p>
          </Step>
          <Step n={5} title="Test before going live">
            <p>To try it out first, use <b>Test mode</b> keys (<code className="text-xs">rzp_test_</code>). No real
              money moves. Make a test payment from a customer account, check it appears under Customer Payments,
              then switch to your live keys.</p>
          </Step>
        </ol>

        <div className="mt-5 space-y-2 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
          <p>
            <b>Opening the webhook URL in a browser shows "Method Not Allowed".</b> That is normal: only Razorpay can
            call it. To check it works, see the delivery log on the Razorpay Webhooks page.
          </p>
          {isLocal && (
            <p className="text-yellow-800">
              This URL points to <b>localhost</b>, which Razorpay cannot reach. Copy it from the live site instead.
            </p>
          )}
        </div>

        <div className="mt-5 flex justify-end">
          <button type="button" onClick={onClose}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Got it
          </button>
        </div>
      </div>
    </div>
  )
}
