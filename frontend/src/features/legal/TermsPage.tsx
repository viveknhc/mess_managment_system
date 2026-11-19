import { Link } from 'react-router-dom'
import { LEGAL_NAME, SUPPORT_EMAIL } from '../../config/support'
import { MONTHLY_FEE, REACTIVATION_FEE, SETUP_FEE } from '../landing/pricing'
import { Bullets, LegalLayout, Section } from './LegalLayout'

export function TermsPage() {
  return (
    <LegalLayout title="Terms & Conditions">
      <p>
        These terms apply to MessDeck, an online mess management software run by {LEGAL_NAME} ("MessDeck", "we",
        "us"). By creating an account or using MessDeck you agree to them. If you use MessDeck on behalf of a mess or
        business, you agree to them for that business.
      </p>

      <Section title="1. The service">
        <p>
          MessDeck is a web application that helps mess and tiffin businesses manage customers, meal plans,
          subscriptions, payments, deliveries and reports. We host it for you; it works in a web browser and needs no
          installation.
        </p>
      </Section>

      <Section title="2. Accounts">
        <Bullets
          items={[
            'We create your business account after you sign up with us. You are responsible for the logins you give to your managers, staff and customers.',
            'Keep your password private. Tell us straight away if you think someone else has used your account.',
            'You must give correct business and contact details and keep them up to date.',
          ]}
        />
      </Section>

      <Section title="3. Fees and payment">
        <Bullets
          items={[
            `A one-time setup fee of ${SETUP_FEE} and a monthly fee of ${MONTHLY_FEE}, payable in advance. Prices are in Indian Rupees.`,
            'Payments are processed securely by Razorpay. We do not see or store your card, UPI or bank details.',
            'If a monthly fee is not paid on time, access may be limited after a short grace period until it is paid.',
            'We will tell you at least 30 days before any price change for your plan.',
          ]}
        />
        <p>
          Refunds and cancellations are covered by our{' '}
          <Link to="/refund-policy" className="font-medium text-brand-700 underline">
            Refund &amp; Cancellation Policy
          </Link>
          . If you cancel and come back after more than 3 months, a reactivation fee of {REACTIVATION_FEE} applies.
        </p>
      </Section>

      <Section title="4. Payments from your customers">
        <p>
          If you turn on online payments, your customers pay you directly into your own Razorpay account. MessDeck is
          not a party to those payments. Your prices, your refunds to your customers and any disputes with them are
          between you and your customers.
        </p>
      </Section>

      <Section title="5. Your data">
        <p>
          The data you enter (customers, plans, payments and so on) belongs to your business. We keep it private to
          your business and use it only to run the service, as described in our{' '}
          <Link to="/privacy" className="font-medium text-brand-700 underline">
            Privacy Policy
          </Link>
          . You must have your customers' permission to store their details in MessDeck.
        </p>
      </Section>

      <Section title="6. Acceptable use">
        <Bullets
          items={[
            'Do not use MessDeck for anything unlawful, or to store data you have no right to hold.',
            'Do not try to access another business\'s data, break the security of the service, or overload it.',
            'We may suspend an account that breaks these rules, after telling you where possible.',
          ]}
        />
      </Section>

      <Section title="7. Availability and liability">
        <p>
          We work to keep MessDeck available and back up data every day, but we cannot promise it will never be
          interrupted. To the extent the law allows, our total liability to you for any claim is limited to the fees
          you paid us in the 3 months before the claim. We are not liable for indirect losses such as lost profit.
        </p>
      </Section>

      <Section title="8. Ending the service">
        <p>
          You can cancel any time. We may end the service with 30 days' notice. Either way, you can ask us for an
          export of your data within 30 days of the account closing.
        </p>
      </Section>

      <Section title="9. Changes and law">
        <p>
          We may update these terms; the date at the top shows the latest version, and we will tell you about
          important changes. These terms are governed by the laws of India.
        </p>
      </Section>

      <Section title="10. Contact">
        <p>
          Questions about these terms: <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-brand-700 underline">{SUPPORT_EMAIL}</a>{' '}
          or see{' '}
          <Link to="/contact" className="font-medium text-brand-700 underline">
            Contact Us
          </Link>
          .
        </p>
      </Section>
    </LegalLayout>
  )
}
