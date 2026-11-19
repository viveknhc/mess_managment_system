import { SUPPORT_EMAIL } from '../../config/support'
import { MONTHLY_FEE, REACTIVATION_FEE, SETUP_FEE } from '../landing/pricing'
import { Bullets, LegalLayout, Section } from './LegalLayout'

export function RefundPolicyPage() {
  return (
    <LegalLayout title="Refund & Cancellation Policy">
      <Section title="Cancelling your MessDeck plan">
        <Bullets
          items={[
            'You can cancel the monthly plan at any time by messaging or emailing us. There is no lock-in period.',
            'After you cancel, you will not be charged again. You keep access until the end of the month you have already paid for.',
            `If you cancel and come back after more than 3 months, a reactivation fee of ${REACTIVATION_FEE} applies.`,
          ]}
        />
      </Section>

      <Section title="Refunds">
        <Bullets
          items={[
            `The one-time setup fee of ${SETUP_FEE} is non-refundable, because the setup work is done as soon as you sign up.`,
            `The monthly fee of ${MONTHLY_FEE} is not refunded for a month that has already started, including part months.`,
            'If you were charged twice, or charged for a month after you cancelled, we refund the extra amount in full.',
            'If a payment failed but money was deducted, it is normally returned automatically by your bank or Razorpay. If it is not, contact us and we will help.',
          ]}
        />
        <p>
          Approved refunds are made to the original payment method within 5–7 working days. Your bank may take a few
          more days to show it.
        </p>
      </Section>

      <Section title="Payments made to a mess">
        <p>
          When a mess's customer pays for meals through MessDeck, the money goes directly to that mess. Refunds and
          cancellations of meal subscriptions follow the mess's own policy. Please contact the mess; MessDeck cannot
          refund those payments.
        </p>
      </Section>

      <Section title="How to ask">
        <p>
          Email <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-brand-700 underline">{SUPPORT_EMAIL}</a>{' '}
          with your business name and the payment reference. We reply within 2 working days.
        </p>
      </Section>
    </LegalLayout>
  )
}
