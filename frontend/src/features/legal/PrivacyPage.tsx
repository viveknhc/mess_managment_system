import { LEGAL_NAME, SUPPORT_EMAIL } from '../../config/support'
import { Bullets, LegalLayout, Section } from './LegalLayout'

export function PrivacyPage() {
  return (
    <LegalLayout title="Privacy Policy">
      <p>
        This policy explains what information MessDeck (run by {LEGAL_NAME}) collects, how it is used and the choices
        you have.
      </p>

      <Section title="What we collect">
        <Bullets
          items={[
            <><b>Account details:</b> names, phone numbers, email addresses and passwords (stored encrypted) of mess owners, managers, staff and customers who log in.</>,
            <><b>Business data entered by a mess:</b> customer names, contact details, addresses, meal plans, subscriptions, payments, deliveries and notes.</>,
            <><b>Payment records:</b> amounts, dates and payment references. Card, UPI and bank details are handled by Razorpay and never reach us.</>,
            <><b>Technical data:</b> basic logs such as IP address, browser type and the time of a request, used for security and fixing problems.</>,
          ]}
        />
      </Section>

      <Section title="How we use it">
        <Bullets
          items={[
            'To run MessDeck: logins, subscriptions, deliveries, payment records, reports and notifications.',
            'To take payments for MessDeck plans and, where a mess turns it on, to let its customers pay the mess online.',
            'To provide support, keep the service secure and fix problems.',
          ]}
        />
        <p>We do not sell personal data and we do not use it for advertising.</p>
      </Section>

      <Section title="Who can see it">
        <Bullets
          items={[
            'Each mess sees only its own data. Customers see only their own subscription, deliveries and payments.',
            'Our hosting and database providers store the data on our behalf.',
            'Razorpay processes payments under its own privacy policy.',
            'We share data with authorities only when the law requires it.',
          ]}
        />
      </Section>

      <Section title="Who is responsible for customer data">
        <p>
          A mess decides which of its customers' details it stores in MessDeck. For that data, the mess is responsible
          for having its customers' permission, and we process it on the mess's behalf. Customers should contact
          their mess first about their data; we will help the mess respond.
        </p>
      </Section>

      <Section title="Security and storage">
        <p>
          Data is sent over HTTPS, passwords and payment keys are stored encrypted, and every mess's data is kept
          separate. Data is backed up every day. We keep data while the account is active and delete it within 90
          days after an account is closed, unless the law requires us to keep it longer.
        </p>
      </Section>

      <Section title="Your choices">
        <p>
          You can ask to see, correct, export or delete your personal data by emailing{' '}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-brand-700 underline">{SUPPORT_EMAIL}</a>.
          We reply within 30 days.
        </p>
      </Section>

      <Section title="Changes">
        <p>
          We may update this policy; the date at the top shows the latest version, and we will tell account owners
          about important changes.
        </p>
      </Section>
    </LegalLayout>
  )
}
