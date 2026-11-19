import {
  BUSINESS_ADDRESS,
  LEGAL_NAME,
  SUPPORT_EMAIL,
  formatWhatsapp,
  whatsappLink,
} from '../../config/support'
import { LegalLayout } from './LegalLayout'

export function ContactPage() {
  const rows = [
    { label: 'Business', value: LEGAL_NAME },
    {
      label: 'Email',
      value: (
        <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-brand-700 underline">
          {SUPPORT_EMAIL}
        </a>
      ),
    },
    {
      label: 'Phone / WhatsApp',
      value: (
        <a href={whatsappLink()} target="_blank" rel="noopener noreferrer" className="font-medium text-brand-700 underline">
          {formatWhatsapp()}
        </a>
      ),
    },
    ...(BUSINESS_ADDRESS
      ? [{ label: 'Address', value: <span className="whitespace-pre-line">{BUSINESS_ADDRESS}</span> }]
      : []),
    { label: 'Hours', value: 'Monday to Saturday, 10 am – 7 pm IST' },
  ]

  return (
    <LegalLayout title="Contact Us">
      <p>Questions about MessDeck, your account, billing or a refund? We're happy to help.</p>
      <dl className="divide-y divide-brand-100 rounded-xl border border-brand-100 bg-white">
        {rows.map((r) => (
          <div key={r.label} className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
            <dt className="text-sm font-medium text-gray-500">{r.label}</dt>
            <dd className="text-gray-900 sm:col-span-2">{r.value}</dd>
          </div>
        ))}
      </dl>
      <p className="text-sm text-gray-500">We usually reply within one working day.</p>
    </LegalLayout>
  )
}
