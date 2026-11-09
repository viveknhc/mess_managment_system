import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from './Logo'
import { whatsappLink } from '../../utils/contact'

/* ------------------------------------------------------------------ */
/*  Intersection-observer fade-in hook                                 */
/* ------------------------------------------------------------------ */

function useFadeIn<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('opacity-100', 'translate-y-0')
          el.classList.remove('opacity-0', 'translate-y-6')
          observer.unobserve(el)
        }
      },
      { threshold: 0.15 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return ref
}

function FadeIn({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const ref = useFadeIn<HTMLDivElement>()
  return (
    <div ref={ref} className={`opacity-0 translate-y-6 transition-all duration-700 ease-out ${className}`}>
      {children}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const CONTACT_URL = whatsappLink('Hi, I want to set up MessDeck for my mess.')

const SETUP_FEE = '₹2,500'
const MONTHLY_FEE = '₹500'
const FIRST_PAYMENT = '₹3,000'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'FAQ', href: '#faq' },
]

const PAIN_POINTS = [
  {
    emoji: '📓',
    title: 'Notebooks Get Lost',
    desc: 'Handwritten registers fade, tear, and have zero search. One coffee spill and your month is gone.',
    accent: 'border-red-400',
  },
  {
    emoji: '📱',
    title: 'WhatsApp Chaos',
    desc: '"Please skip my meal tomorrow" buried in 200 messages. No way to track who paid and who didn\'t.',
    accent: 'border-red-400',
  },
  {
    emoji: '🤷',
    title: 'No Visibility',
    desc: 'How many meals today? Who\'s expiring this week? You\'re guessing instead of knowing.',
    accent: 'border-red-400',
  },
]

// Mirrors "Monthly fee covers" in docs/Monthly_Subscription_Plan.pdf — keep the two in sync.
const FEATURES = [
  { emoji: '👥', title: 'Customer Management', desc: 'Full records for every customer. Search, filter, and see everything at a glance.' },
  { emoji: '🍽️', title: 'Meals & Plans', desc: 'Set up breakfast, lunch, dinner, and packed meal plans with your own prices.' },
  { emoji: '📅', title: 'Subscription Tracking', desc: 'Start dates, renewals, and automatic alerts before a subscription expires.' },
  { emoji: '💰', title: 'Payment Recording', desc: 'Record every payment and see paid and pending balances for each customer.' },
  { emoji: '🚚', title: 'Deliveries & Meal Counts', desc: 'A daily delivery list for your staff and exact meal counts for your kitchen.' },
  { emoji: '⏸️', title: 'Skip & Pause', desc: 'Customers skip a meal or pause for a few days without the back-and-forth.' },
  { emoji: '📊', title: 'Daily Dashboard', desc: 'Today\'s meals, deliveries, collections, and pending dues on one screen.' },
  { emoji: '🔑', title: 'Owner & Staff Logins', desc: 'Separate logins for you, your managers, delivery staff, and kitchen staff.' },
  { emoji: '💾', title: 'Daily Data Backup', desc: 'Your data is backed up every day and kept private to your business.' },
  { emoji: '💬', title: 'WhatsApp & Email Support', desc: 'Stuck on something? Message us and we\'ll help you sort it out.' },
]

const STEPS = [
  { num: 1, title: 'Contact Us', desc: 'Message us on WhatsApp. We\'ll answer your questions and show you around.' },
  { num: 2, title: 'We Set It Up', desc: 'We create your account, add your meals, plans, staff, and up to 100 customers.' },
  { num: 3, title: 'Start Using It', desc: 'A 30-minute walkthrough and you\'re live. Then just ₹500 a month.' },
]

const SETUP_INCLUDES = [
  'Creating your business account',
  'Adding your owner and staff logins',
  'Setting up your meals and plans',
  'Importing your existing customer list (up to 100 customers)',
  'A 30-minute walkthrough on how to use it',
]

const TERMS = [
  'Setup fee is non-refundable',
  'Cancel the monthly plan any time',
  'If you cancel and come back after more than 3 months, a ₹1,000 reactivation fee applies',
  'Your data is private to your business',
]

const FAQS = [
  {
    q: 'How much do I pay to start?',
    a: `Your first payment is ${FIRST_PAYMENT}: the ${SETUP_FEE} one-time setup fee plus ${MONTHLY_FEE} for the first month. After that, it's ${MONTHLY_FEE} each month.`,
  },
  {
    q: 'What does the setup fee include?',
    a: 'We create your business account, add your owner and staff logins, set up your meals and plans, import up to 100 of your existing customers, and give you a 30-minute walkthrough.',
  },
  {
    q: 'Do I need to install anything?',
    a: 'No. We host everything for you. It works in the browser on your phone, tablet, or computer.',
  },
  {
    q: 'How does skip and pause work?',
    a: 'Customers can skip individual meals or pause their subscription for a few days. Deliveries for those days are taken off the list automatically.',
  },
  {
    q: 'Can I cancel?',
    a: 'Yes, cancel the monthly plan any time. The setup fee is non-refundable. If you come back after more than 3 months, a ₹1,000 reactivation fee applies.',
  },
  {
    q: 'Is my data safe?',
    a: 'Your data is backed up every day and is private to your business. No other business can see it.',
  },
]

/* ------------------------------------------------------------------ */
/*  Subcomponents                                                      */
/* ------------------------------------------------------------------ */

function Navbar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleAnchor = useCallback((e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault()
    setOpen(false)
    document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  return (
    <nav
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-cream/85 backdrop-blur-lg shadow-sm' : 'bg-transparent'
      }`}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <a href="#hero" onClick={(e) => handleAnchor(e, '#hero')} aria-label="MessDeck home">
            <Logo />
          </a>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={(e) => handleAnchor(e, l.href)} className="text-sm font-medium text-gray-600 hover:text-brand-800 transition-colors">
                {l.label}
              </a>
            ))}
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-brand-800 transition-colors">
              Login
            </Link>
            <a href={CONTACT_URL} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-brand-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-900 transition-colors">
              Contact Us
            </a>
          </div>

          {/* Mobile hamburger */}
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-gray-600" aria-label="Toggle menu">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {open ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /> : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-cream/95 backdrop-blur-lg border-t border-brand-100 shadow-lg">
          <div className="px-4 py-4 space-y-3">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={(e) => handleAnchor(e, l.href)} className="block text-sm font-medium text-gray-600 hover:text-brand-800">
                {l.label}
              </a>
            ))}
            <Link to="/login" className="block text-sm font-medium text-gray-700">Login</Link>
            <a href={CONTACT_URL} target="_blank" rel="noopener noreferrer" className="block rounded-lg bg-brand-800 px-4 py-2 text-sm font-semibold text-white text-center">
              Contact Us
            </a>
          </div>
        </div>
      )}
    </nav>
  )
}

function HeroSection() {
  return (
    <section id="hero" className="relative overflow-hidden bg-gradient-to-br from-cream via-cream to-brand-50 pt-24 pb-16 sm:pt-32 sm:pb-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Copy */}
          <div className="text-center lg:text-left">
            <p className="mb-6 inline-block rounded-full bg-brand-800 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-cream">
              Run your mess smarter.
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-brand-800 leading-tight">
              Run Your Mess{' '}
              <span className="text-brand-500">Like a Pro.</span>
              <br />
              <span className="text-gray-500 text-3xl sm:text-4xl lg:text-5xl">Ditch the Notebooks.</span>
            </h1>
            <p className="mt-6 text-lg text-gray-600 max-w-xl mx-auto lg:mx-0">
              Manage customers, subscriptions, payments, and deliveries from your phone. We set everything up for you, and you pay just {MONTHLY_FEE} a month.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <a href={CONTACT_URL} target="_blank" rel="noopener noreferrer" className="rounded-xl bg-brand-800 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-800/25 hover:bg-brand-900 hover:shadow-xl transition-all">
                Contact Us on WhatsApp
              </a>
              <a href="#pricing" onClick={(e) => { e.preventDefault(); document.querySelector('#pricing')?.scrollIntoView({ behavior: 'smooth' }) }} className="rounded-xl border-2 border-brand-200 bg-white px-8 py-3.5 text-base font-semibold text-gray-700 hover:border-brand-500 hover:text-brand-800 transition-all">
                See Pricing
              </a>
            </div>
            <p className="mt-4 text-sm text-brand-600">{SETUP_FEE} one-time setup &middot; {MONTHLY_FEE}/month &middot; Cancel any time</p>
          </div>

          {/* Mock dashboard illustration */}
          <div className="relative hidden lg:block">
            <div className="relative rounded-2xl bg-white shadow-2xl shadow-brand-900/10 border border-brand-100 p-6 transform rotate-1 hover:rotate-0 transition-transform duration-500">
              {/* Mini dashboard header */}
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <div className="ml-4 h-4 w-32 rounded bg-gray-100" />
              </div>
              {/* Stats row */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[
                  { label: 'Active Subs', val: '247', color: 'text-brand-800', bg: 'bg-brand-50' },
                  { label: 'Today\'s Meals', val: '189', color: 'text-brand-500', bg: 'bg-brand-100' },
                  { label: 'Collected', val: '\u20B9120K', color: 'text-amber-700', bg: 'bg-amber-50' },
                ].map((s) => (
                  <div key={s.label} className={`${s.bg} rounded-lg p-3`}>
                    <div className={`text-xl font-bold ${s.color}`}>{s.val}</div>
                    <div className="text-xs text-gray-500">{s.label}</div>
                  </div>
                ))}
              </div>
              {/* Fake table rows */}
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-cream p-2.5">
                    <div className="h-8 w-8 rounded-full bg-brand-100" />
                    <div className="flex-1">
                      <div className="h-3 w-24 rounded bg-gray-200" />
                      <div className="mt-1 h-2 w-16 rounded bg-gray-100" />
                    </div>
                    <div className={`h-5 w-14 rounded-full ${i <= 2 ? 'bg-brand-200' : i === 3 ? 'bg-yellow-100' : 'bg-red-100'}`} />
                  </div>
                ))}
              </div>
            </div>
            {/* Floating card */}
            <div className="absolute -top-4 -right-4 rounded-xl bg-white shadow-lg border border-brand-100 p-3 animate-bounce" style={{ animationDuration: '3s' }}>
              <div className="text-2xl font-bold text-brand-500">+12%</div>
              <div className="text-xs text-gray-500">Collections</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function PainPointsSection() {
  return (
    <section className="bg-cream py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-brand-800">
              Still Running Your Mess on Paper?
            </h2>
            <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
              You're not alone. Most mess owners juggle notebooks, WhatsApp, and memory. Here's what that costs you:
            </p>
          </div>
        </FadeIn>
        <div className="grid md:grid-cols-3 gap-8">
          {PAIN_POINTS.map((p, i) => (
            <FadeIn key={i}>
              <div className={`bg-white rounded-xl border-t-4 ${p.accent} p-6 shadow-sm hover:shadow-md transition-shadow`}>
                <div className="text-4xl mb-4">{p.emoji}</div>
                <h3 className="text-lg font-semibold text-brand-800 mb-2">{p.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{p.desc}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function FeaturesSection() {
  return (
    <section id="features" className="bg-white py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-brand-800">
              Everything You Need to Manage Your Mess
            </h2>
            <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
              Everything below is included in the {MONTHLY_FEE} monthly plan. No extra charges per feature.
            </p>
          </div>
        </FadeIn>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-6">
          {FEATURES.map((f, i) => (
            <FadeIn key={i}>
              <div className="group rounded-xl border border-brand-100 bg-white p-6 shadow-sm hover:border-brand-300 hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
                <div className="text-3xl mb-3">{f.emoji}</div>
                <h3 className="text-base font-semibold text-brand-800 mb-1">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function HowItWorksSection() {
  return (
    <section className="bg-brand-800 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white">
              Get Started in 3 Simple Steps
            </h2>
            <p className="mt-4 text-lg text-brand-100 max-w-2xl mx-auto">
              We do the setup work, so you can start using it right away.
            </p>
          </div>
        </FadeIn>
        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Dashed connector (desktop only) */}
          <div className="hidden md:block absolute top-12 left-1/6 right-1/6 border-t-2 border-dashed border-brand-400" style={{ left: '20%', right: '20%' }} />

          {STEPS.map((s) => (
            <FadeIn key={s.num}>
              <div className="relative text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white text-brand-800 text-2xl font-bold shadow-lg">
                  {s.num}
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-brand-100 text-sm">{s.desc}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function PricingSection() {
  return (
    <section id="pricing" className="bg-cream py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-brand-800">
              Simple, Transparent Pricing
            </h2>
            <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
              One plan with every feature. We host it, you use it.
            </p>
          </div>
        </FadeIn>
        <FadeIn>
          <div className="mx-auto max-w-4xl grid md:grid-cols-2 gap-8">
            <div className="rounded-2xl bg-white border border-brand-200 p-8 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-500">One-time setup</h3>
              <div className="mt-4 text-4xl font-extrabold text-brand-800">{SETUP_FEE}</div>
              <ul className="mt-8 space-y-3">
                {SETUP_INCLUDES.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-gray-600">{f}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl bg-brand-800 text-white p-8 shadow-xl">
              <h3 className="text-lg font-semibold text-brand-100">Monthly subscription</h3>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold">{MONTHLY_FEE}</span>
                <span className="text-sm text-brand-200">/month</span>
              </div>
              <ul className="mt-8 space-y-3">
                {FEATURES.map((f) => (
                  <li key={f.title} className="flex items-start gap-2 text-sm">
                    <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-brand-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-brand-50">{f.title}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="mt-8 text-center text-sm text-gray-600">
            First payment: {SETUP_FEE} setup + {MONTHLY_FEE} first month = <strong>{FIRST_PAYMENT}</strong>. After that, {MONTHLY_FEE} each month.
          </p>
          <div className="mt-6 text-center">
            <a href={CONTACT_URL} target="_blank" rel="noopener noreferrer" className="inline-block rounded-xl bg-brand-800 px-8 py-3.5 text-base font-semibold text-white shadow-lg hover:bg-brand-900 transition-all">
              Contact Us to Get Started
            </a>
          </div>
          <ul className="mt-8 mx-auto max-w-2xl space-y-1 text-xs text-gray-500 list-disc pl-5">
            {TERMS.map((t) => <li key={t}>{t}</li>)}
          </ul>
        </FadeIn>
      </div>
    </section>
  )
}

function FAQSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(null)

  return (
    <section id="faq" className="bg-cream py-16 sm:py-24">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-brand-800">
              Frequently Asked Questions
            </h2>
          </div>
        </FadeIn>
        <div className="space-y-3">
          {FAQS.map((faq, i) => (
            <FadeIn key={i}>
              <div className="rounded-xl bg-white border border-brand-100 shadow-sm overflow-hidden">
                <button
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                  className="flex w-full items-center justify-between px-6 py-4 text-left"
                >
                  <span className="text-sm font-semibold text-brand-800">{faq.q}</span>
                  <svg
                    className={`h-5 w-5 text-gray-400 flex-shrink-0 transition-transform duration-200 ${openIdx === i ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <div className={`overflow-hidden transition-all duration-300 ${openIdx === i ? 'max-h-40 pb-4' : 'max-h-0'}`}>
                  <p className="px-6 text-sm text-gray-500 leading-relaxed">{faq.a}</p>
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function CTABanner() {
  return (
    <section className="bg-gradient-to-r from-brand-700 to-brand-900 py-16 sm:py-20">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
        <FadeIn>
          <h2 className="text-3xl sm:text-4xl font-bold text-white">
            Ready to Ditch the Notebooks?
          </h2>
          <p className="mt-4 text-lg text-brand-100 max-w-2xl mx-auto">
            We set it up for you. {MONTHLY_FEE} a month. Cancel any time.
          </p>
          <div className="mt-8">
            <a href={CONTACT_URL} target="_blank" rel="noopener noreferrer" className="inline-block rounded-xl bg-cream px-10 py-4 text-base font-semibold text-brand-800 shadow-lg hover:bg-brand-50 hover:shadow-xl transition-all">
              Contact Us on WhatsApp
            </a>
          </div>
        </FadeIn>
      </div>
    </section>
  )
}

function Footer() {
  const footerLinks = {
    Product: [
      { label: 'Features', href: '#features' },
      { label: 'Pricing', href: '#pricing' },
      { label: 'FAQ', href: '#faq' },
    ],
    Support: [
      { label: 'WhatsApp Us', href: CONTACT_URL },
      { label: 'Login', href: '/login' },
    ],
  }

  return (
    <footer className="bg-brand-900 py-12 sm:py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-3 gap-8">
          {/* Brand */}
          <div className="lg:col-span-1">
            <Logo light />
            <p className="mt-3 text-sm text-brand-200">
              Mess management software. Run your mess smarter.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h4 className="text-sm font-semibold text-brand-100 uppercase tracking-wider">{title}</h4>
              <ul className="mt-3 space-y-2">
                {links.map((l) => (
                  <li key={l.label}>
                    <a href={l.href} className="text-sm text-brand-200 hover:text-white transition-colors">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-brand-700 pt-8 text-center">
          <p className="text-sm text-brand-200">
            Made with {'\u2764\uFE0F'} in India {'\uD83C\uDDEE\uD83C\uDDF3'} &middot; &copy; {new Date().getFullYear()} MessDeck. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <HeroSection />
      <PainPointsSection />
      <FeaturesSection />
      <HowItWorksSection />
      <PricingSection />
      <FAQSection />
      <CTABanner />
      <Footer />
    </div>
  )
}
