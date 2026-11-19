import { SUPPORT_EMAIL } from '../../config/support'
import { LegalLayout, Section } from './LegalLayout'

export function ShippingPolicyPage() {
  return (
    <LegalLayout title="Shipping & Delivery Policy">
      <Section title="No physical shipping">
        <p>
          MessDeck is online software. Nothing is shipped. You use it in a web browser on your phone, tablet or
          computer.
        </p>
      </Section>

      <Section title="When you get access">
        <p>
          After the first payment, we set up your business account, logins, meals and plans and share your login
          details on WhatsApp or email, normally within 2 working days. Monthly renewals take effect as soon as the
          payment is confirmed; there is nothing to wait for.
        </p>
      </Section>

      <Section title="Meals delivered by a mess">
        <p>
          A mess may use MessDeck to plan its own meal deliveries. Those meals are prepared and delivered by the mess,
          not by MessDeck, and their delivery terms are set by the mess.
        </p>
      </Section>

      <Section title="Questions">
        <p>
          If you have paid and not received access, email{' '}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-brand-700 underline">{SUPPORT_EMAIL}</a>.
        </p>
      </Section>
    </LegalLayout>
  )
}
