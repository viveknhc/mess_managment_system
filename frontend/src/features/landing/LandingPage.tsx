import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface PricingPlan {
  name: string
  price: string
  period: string
  features: string[]
  popular?: boolean
  cta: string
}

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

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'FAQ', href: '#faq' },
]

const PAIN_POINTS = [
  {
    emoji: '\uD83D\uDCD3',
    title: 'Notebooks Get Lost',
    desc: 'Handwritten registers fade, tear, and have zero search. One chai spill and your month is gone.',
    accent: 'border-red-400',
  },
  {
    emoji: '\uD83D\uDCF1',
    title: 'WhatsApp Chaos',
    desc: '"Bhaiya kal skip hai" buried in 200 messages. No way to track who paid and who didn\'t.',
    accent: 'border-red-400',
  },
  {
    emoji: '\uD83E\uDD37',
    title: 'No Visibility',
    desc: 'How many meals today? Who\'s expiring this week? You\'re guessing instead of knowing.',
    accent: 'border-red-400',
  },
]

const FEATURES = [
  { emoji: '\uD83D\uDC65', title: 'Customer Management', desc: 'Add customers in seconds. Search, filter, and see everything at a glance.' },
  { emoji: '\uD83D\uDCC5', title: 'Subscription Tracking', desc: 'Plans, start dates, renewals, expiry alerts — all automated.' },
  { emoji: '\uD83D\uDCB0', title: 'Payment Recording', desc: 'Track every rupee. Partial payments, pending dues, payment history.' },
  { emoji: '\uD83D\uDE9A', title: 'Delivery Management', desc: 'Daily delivery lists, mark delivered/skipped, route assignments.' },
  { emoji: '\uD83C\uDF73', title: 'Kitchen Counts', desc: 'Real-time meal counts so your kitchen knows exactly how much to cook.' },
  { emoji: '\uD83D\uDCCA', title: 'Reports & Insights', desc: 'Revenue, collections, expiring subs — beautiful charts, zero effort.' },
  { emoji: '\uD83D\uDD14', title: 'Smart Notifications', desc: 'Auto-reminders for expiring subs, pending payments, and more.' },
  { emoji: '\uD83D\uDC64', title: 'Customer Portal', desc: 'Customers check their own plan, skip meals, and view payment history.' },
]

const STEPS = [
  { num: 1, title: 'Sign Up Free', desc: 'Create your account in 30 seconds. No credit card needed.' },
  { num: 2, title: 'Set Up Your Mess', desc: 'Add your meals, plans, and customers. We\'ll help you import.' },
  { num: 3, title: 'Go Live!', desc: 'Start managing deliveries, tracking payments, and growing your business.' },
]

const FALLBACK_PLANS: PricingPlan[] = [
  {
    name: 'Starter',
    price: 'Free',
    period: 'forever',
    features: ['Up to 50 customers', '1 staff member', 'Basic reports', 'Email support'],
    cta: 'Start Free',
  },
  {
    name: 'Professional',
    price: '\u20B9499',
    period: '/month',
    features: ['Up to 500 customers', '5 staff members', 'Advanced reports', 'Customer portal', 'Priority support'],
    popular: true,
    cta: 'Start Free Trial',
  },
  {
    name: 'Business',
    price: '\u20B9999',
    period: '/month',
    features: ['Unlimited customers', 'Unlimited staff', 'Custom reports', 'API access', 'Dedicated support', 'White-label option'],
    cta: 'Contact Sales',
  },
]

const TESTIMONIALS = [
  {
    name: 'Rajesh Sharma',
    role: 'Sharma Tiffin Service, Pune',
    quote: 'Before Mess Manager, I had 3 registers and still missed payments. Now everything is on my phone. My collections improved by 40% in the first month!',
    stars: 5,
    color: 'bg-orange-500',
  },
  {
    name: 'Priya Nair',
    role: 'Amma\'s Kitchen, Kochi',
    quote: 'The kitchen counts feature alone saves me 30 minutes every morning. No more calling customers to confirm. It just works.',
    stars: 5,
    color: 'bg-emerald-500',
  },
  {
    name: 'Arun Gupta',
    role: 'Gupta Mess, Jaipur',
    quote: 'My customers love the portal — they can skip meals themselves and I don\'t get 50 WhatsApp messages a day anymore. Game changer!',
    stars: 5,
    color: 'bg-blue-500',
  },
]

const FAQS = [
  {
    q: 'Is there a free trial?',
    a: 'Yes! You get a full 30-day free trial with all features. No credit card required to start.',
  },
  {
    q: 'Can I import my existing customer data?',
    a: 'Absolutely. You can import customers from Excel or CSV files. Our support team can also help you migrate for free.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept UPI, credit/debit cards, net banking, and wallets via Razorpay. Your customers\' payment data stays between you and them.',
  },
  {
    q: 'How does skip and pause work?',
    a: 'Customers can skip individual meals or pause their entire subscription. You configure the rules — whether skipped days extend the plan, give credit, or no adjustment.',
  },
  {
    q: 'Is my data safe?',
    a: 'Your data is encrypted at rest and in transit. We run on secure cloud infrastructure with daily backups. Each business\'s data is completely isolated.',
  },
  {
    q: 'What happens after my trial ends?',
    a: 'You can continue on the free Starter plan (up to 50 customers) or upgrade to a paid plan. No data is lost — everything is preserved.',
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
        scrolled ? 'bg-white/80 backdrop-blur-lg shadow-sm' : 'bg-transparent'
      }`}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <a href="#hero" onClick={(e) => handleAnchor(e, '#hero')} className="flex items-center gap-2 font-bold text-xl text-primary-600">
            <span className="text-2xl">{'\uD83C\uDF5B'}</span> Mess Manager
          </a>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={(e) => handleAnchor(e, l.href)} className="text-sm font-medium text-gray-600 hover:text-primary-600 transition-colors">
                {l.label}
              </a>
            ))}
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-primary-600 transition-colors">
              Login
            </Link>
            <Link to="/signup" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors">
              Start Free Trial
            </Link>
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
        <div className="md:hidden bg-white/95 backdrop-blur-lg border-t border-gray-100 shadow-lg">
          <div className="px-4 py-4 space-y-3">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={(e) => handleAnchor(e, l.href)} className="block text-sm font-medium text-gray-600 hover:text-primary-600">
                {l.label}
              </a>
            ))}
            <Link to="/login" className="block text-sm font-medium text-gray-700">Login</Link>
            <Link to="/signup" className="block rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white text-center">
              Start Free Trial
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

function HeroSection() {
  return (
    <section id="hero" className="relative overflow-hidden bg-gradient-to-br from-primary-50 via-white to-blue-50 pt-24 pb-16 sm:pt-32 sm:pb-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Copy */}
          <div className="text-center lg:text-left">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900 leading-tight">
              Run Your Mess{' '}
              <span className="text-primary-600">Like a Pro.</span>
              <br />
              <span className="text-gray-500 text-3xl sm:text-4xl lg:text-5xl">Ditch the Notebooks.</span>
            </h1>
            <p className="mt-6 text-lg text-gray-600 max-w-xl mx-auto lg:mx-0">
              The all-in-one platform for mess &amp; tiffin businesses. Manage customers, subscriptions, payments, and deliveries — from your phone.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link to="/signup" className="rounded-xl bg-primary-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-primary-600/25 hover:bg-primary-700 hover:shadow-xl transition-all">
                Start Free Trial
              </Link>
              <a href="#features" onClick={(e) => { e.preventDefault(); document.querySelector('#features')?.scrollIntoView({ behavior: 'smooth' }) }} className="rounded-xl border-2 border-gray-200 bg-white px-8 py-3.5 text-base font-semibold text-gray-700 hover:border-primary-300 hover:text-primary-600 transition-all">
                See Features
              </a>
            </div>
            <p className="mt-4 text-sm text-gray-400">No credit card required &middot; 30-day free trial</p>
          </div>

          {/* Mock dashboard illustration */}
          <div className="relative hidden lg:block">
            <div className="relative rounded-2xl bg-white shadow-2xl border border-gray-100 p-6 transform rotate-1 hover:rotate-0 transition-transform duration-500">
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
                  { label: 'Active Subs', val: '247', color: 'text-primary-600', bg: 'bg-primary-50' },
                  { label: 'Today\'s Meals', val: '189', color: 'text-emerald-600', bg: 'bg-emerald-50' },
                  { label: 'Collected', val: '\u20B91.2L', color: 'text-amber-600', bg: 'bg-amber-50' },
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
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-gray-50 p-2.5">
                    <div className="h-8 w-8 rounded-full bg-gray-200" />
                    <div className="flex-1">
                      <div className="h-3 w-24 rounded bg-gray-200" />
                      <div className="mt-1 h-2 w-16 rounded bg-gray-100" />
                    </div>
                    <div className={`h-5 w-14 rounded-full ${i <= 2 ? 'bg-green-100' : i === 3 ? 'bg-yellow-100' : 'bg-red-100'}`} />
                  </div>
                ))}
              </div>
            </div>
            {/* Floating card */}
            <div className="absolute -top-4 -right-4 rounded-xl bg-white shadow-lg border border-gray-100 p-3 animate-bounce" style={{ animationDuration: '3s' }}>
              <div className="text-2xl font-bold text-green-600">+12%</div>
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
    <section className="bg-gray-50 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
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
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{p.title}</h3>
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
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              Everything You Need to Manage Your Mess
            </h2>
            <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
              From onboarding customers to tracking deliveries — one platform, zero headaches.
            </p>
          </div>
        </FadeIn>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((f, i) => (
            <FadeIn key={i}>
              <div className="group rounded-xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
                <div className="text-3xl mb-3">{f.emoji}</div>
                <h3 className="text-base font-semibold text-gray-900 mb-1">{f.title}</h3>
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
    <section className="bg-primary-600 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white">
              Get Started in 3 Simple Steps
            </h2>
            <p className="mt-4 text-lg text-primary-100 max-w-2xl mx-auto">
              You'll be up and running in under 10 minutes.
            </p>
          </div>
        </FadeIn>
        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Dashed connector (desktop only) */}
          <div className="hidden md:block absolute top-12 left-1/6 right-1/6 border-t-2 border-dashed border-primary-300" style={{ left: '20%', right: '20%' }} />

          {STEPS.map((s) => (
            <FadeIn key={s.num}>
              <div className="relative text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white text-primary-600 text-2xl font-bold shadow-lg">
                  {s.num}
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-primary-100 text-sm">{s.desc}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function PricingSection() {
  const [plans, setPlans] = useState<PricingPlan[]>(FALLBACK_PLANS)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/v1/pricing/', { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data: PricingPlan[]) => {
        if (Array.isArray(data) && data.length > 0) setPlans(data)
      })
      .catch(() => { /* use fallback */ })
    return () => controller.abort()
  }, [])

  return (
    <section id="pricing" className="bg-gray-50 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              Simple, Transparent Pricing
            </h2>
            <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
              Start free. Upgrade when you grow. No hidden fees.
            </p>
          </div>
        </FadeIn>
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <FadeIn key={i}>
              <div className={`relative rounded-2xl p-8 ${plan.popular ? 'bg-primary-600 text-white shadow-xl scale-105 border-0' : 'bg-white border border-gray-200 shadow-sm'} transition-all`}>
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-amber-400 px-4 py-1 text-xs font-bold text-gray-900 uppercase tracking-wide shadow">
                    Most Popular
                  </div>
                )}
                <div className="text-center">
                  <h3 className={`text-lg font-semibold ${plan.popular ? 'text-primary-100' : 'text-gray-500'}`}>{plan.name}</h3>
                  <div className="mt-4 flex items-baseline justify-center gap-1">
                    <span className={`text-4xl font-extrabold ${plan.popular ? 'text-white' : 'text-gray-900'}`}>{plan.price}</span>
                    <span className={`text-sm ${plan.popular ? 'text-primary-200' : 'text-gray-400'}`}>{plan.period}</span>
                  </div>
                </div>
                <ul className="mt-8 space-y-3">
                  {plan.features.map((f, fi) => (
                    <li key={fi} className="flex items-start gap-2 text-sm">
                      <svg className={`mt-0.5 h-4 w-4 flex-shrink-0 ${plan.popular ? 'text-primary-200' : 'text-green-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      <span className={plan.popular ? 'text-primary-50' : 'text-gray-600'}>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link to="/signup" className={`mt-8 block rounded-lg px-6 py-3 text-center text-sm font-semibold transition-all ${plan.popular ? 'bg-white text-primary-600 hover:bg-primary-50 shadow-lg' : 'bg-primary-600 text-white hover:bg-primary-700'}`}>
                  {plan.cta}
                </Link>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function TestimonialsSection() {
  return (
    <section className="bg-white py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              Trusted by Mess Owners Across India
            </h2>
          </div>
        </FadeIn>
        <div className="grid md:grid-cols-3 gap-8">
          {TESTIMONIALS.map((t, i) => (
            <FadeIn key={i}>
              <div className="rounded-xl bg-gray-50 p-6 shadow-sm">
                <div className="flex gap-0.5 mb-4">
                  {Array.from({ length: t.stars }).map((_, si) => (
                    <svg key={si} className="h-5 w-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <p className="text-gray-600 text-sm leading-relaxed mb-6 italic">"{t.quote}"</p>
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-full ${t.color} flex items-center justify-center text-white font-bold text-sm`}>
                    {t.name.charAt(0)}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{t.name}</div>
                    <div className="text-xs text-gray-500">{t.role}</div>
                  </div>
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}

function FAQSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(null)

  return (
    <section id="faq" className="bg-gray-50 py-16 sm:py-24">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              Frequently Asked Questions
            </h2>
          </div>
        </FadeIn>
        <div className="space-y-3">
          {FAQS.map((faq, i) => (
            <FadeIn key={i}>
              <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <button
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                  className="flex w-full items-center justify-between px-6 py-4 text-left"
                >
                  <span className="text-sm font-semibold text-gray-900">{faq.q}</span>
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
    <section className="bg-gradient-to-r from-primary-600 to-primary-800 py-16 sm:py-20">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
        <FadeIn>
          <h2 className="text-3xl sm:text-4xl font-bold text-white">
            Start Your Free 30-Day Trial
          </h2>
          <p className="mt-4 text-lg text-primary-100 max-w-2xl mx-auto">
            No credit card needed. Set up in minutes. Cancel anytime.
          </p>
          <div className="mt-8">
            <Link to="/signup" className="inline-block rounded-xl bg-white px-10 py-4 text-base font-semibold text-primary-600 shadow-lg hover:bg-primary-50 hover:shadow-xl transition-all">
              Get Started Free
            </Link>
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
      { label: 'Help Center', href: '#' },
      { label: 'Contact Us', href: '#' },
      { label: 'Status', href: '#' },
    ],
    Legal: [
      { label: 'Privacy Policy', href: '#' },
      { label: 'Terms of Service', href: '#' },
      { label: 'Cookie Policy', href: '#' },
    ],
    Company: [
      { label: 'About', href: '#' },
      { label: 'Blog', href: '#' },
      { label: 'Careers', href: '#' },
    ],
  }

  return (
    <footer className="bg-gray-900 py-12 sm:py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Brand */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2 font-bold text-xl text-white">
              <span className="text-2xl">{'\uD83C\uDF5B'}</span> Mess Manager
            </div>
            <p className="mt-3 text-sm text-gray-400">
              The modern way to run your mess business.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">{title}</h4>
              <ul className="mt-3 space-y-2">
                {links.map((l) => (
                  <li key={l.label}>
                    <a href={l.href} className="text-sm text-gray-400 hover:text-white transition-colors">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-gray-800 pt-8 text-center">
          <p className="text-sm text-gray-400">
            Made with {'\u2764\uFE0F'} in India {'\uD83C\uDDEE\uD83C\uDDF3'} &middot; &copy; {new Date().getFullYear()} Mess Manager. All rights reserved.
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
      <TestimonialsSection />
      <FAQSection />
      <CTABanner />
      <Footer />
    </div>
  )
}
