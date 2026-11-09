/** Razorpay Checkout: load checkout.js once, open it, resolve with the signed result. */

const CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'

/** What the backend returns to open Checkout (or PAID when nothing is due any more). */
export type CheckoutStart =
  | {
      status: 'CHECKOUT'
      key_id: string
      order_id: string
      amount: number
      currency: string
      name: string
      description: string
      prefill: { name?: string; email?: string; contact?: string }
    }
  | { status: 'PAID' }

export interface CheckoutSuccess {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

interface RazorpayInstance {
  open(): void
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance
  }
}

let loading: Promise<void> | null = null

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  loading ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = CHECKOUT_SRC
    script.onload = () => resolve()
    script.onerror = () => {
      loading = null
      reject(new Error('Could not load the payment window. Check your internet connection.'))
    }
    document.body.appendChild(script)
  })
  return loading
}

/** Opens Checkout. Resolves with the signed result, or null if the user closed it. */
export async function openCheckout(
  start: Extract<CheckoutStart, { status: 'CHECKOUT' }>,
): Promise<CheckoutSuccess | null> {
  await loadCheckout()
  const Razorpay = window.Razorpay
  if (!Razorpay) throw new Error('Could not load the payment window.')

  return new Promise((resolve) => {
    const rzp = new Razorpay({
      key: start.key_id,
      order_id: start.order_id,
      amount: start.amount,
      currency: start.currency,
      name: start.name,
      description: start.description,
      prefill: start.prefill,
      theme: { color: '#2563eb' },
      handler: (r: CheckoutSuccess) => resolve(r),
      modal: { ondismiss: () => resolve(null) },
    })
    // On failure Razorpay keeps the window open so the user can retry; closing it resolves null.
    rzp.open()
  })
}

type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string }

export type PayOutcome = { outcome: 'paid' | 'cancelled' } | { outcome: 'error'; error: string }

/** Full flow: ask the backend for an order, open Checkout, send the signed result back to verify. */
export async function payOnline(
  start: () => Promise<ApiResult<CheckoutStart>>,
  verify: (result: CheckoutSuccess) => Promise<ApiResult<unknown>>,
): Promise<PayOutcome> {
  const started = await start()
  if (!started.ok) return { outcome: 'error', error: started.error }
  if (started.data.status === 'PAID') return { outcome: 'paid' } // an earlier payment was found and applied

  let result: CheckoutSuccess | null
  try {
    result = await openCheckout(started.data)
  } catch (e) {
    return { outcome: 'error', error: (e as Error).message }
  }
  if (!result) return { outcome: 'cancelled' }

  const verified = await verify(result)
  return verified.ok ? { outcome: 'paid' } : { outcome: 'error', error: verified.error }
}
