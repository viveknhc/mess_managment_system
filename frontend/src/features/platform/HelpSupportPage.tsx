import { useAuthStore } from '../../store/authStore'
import { SUPPORT_EMAIL, formatWhatsapp, supportEmailLink, whatsappLink } from '../../config/support'

/** Owner/manager help page — how to reach MessDeck support. */
export function HelpSupportPage() {
  const businessName = useAuthStore((s) => s.user?.business_name) ?? 'my business'

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Help &amp; Support</h1>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <p className="text-sm text-gray-700">
          Questions about MessDeck, your bill, or something not working? Message us and we'll get back to you the same day.
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <a
            href={whatsappLink(`Hi, I need help with MessDeck (${businessName}).`)}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-gray-200 p-4 hover:border-green-300 hover:bg-green-50"
          >
            <p className="text-sm font-semibold text-gray-900">WhatsApp</p>
            <p className="mt-1 text-sm text-gray-600">{formatWhatsapp()}</p>
          </a>
          <a
            href={supportEmailLink(`MessDeck help — ${businessName}`)}
            className="rounded-lg border border-gray-200 p-4 hover:border-blue-300 hover:bg-blue-50"
          >
            <p className="text-sm font-semibold text-gray-900">Email</p>
            <p className="mt-1 text-sm text-gray-600">{SUPPORT_EMAIL}</p>
          </a>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-800">Paying your bill</h2>
        <p className="mt-2 text-sm text-gray-700">
          Pay by UPI or cash, then send us the payment reference on WhatsApp. We record it and your account is updated the same day.
          You can see the amount due and your payment history on the Billing page.
        </p>
      </div>
    </div>
  )
}
