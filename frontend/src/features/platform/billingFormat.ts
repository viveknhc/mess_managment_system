import type { SaasStatus } from './platformApi'

export function rupees(value: string | number) {
  return `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}

export function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '—'
}

/** Day before an ISO date — e.g. "paid until" when the next payment is due on `value`. */
export function dayBefore(value: string) {
  const d = new Date(value)
  d.setUTCDate(d.getUTCDate() - 1)
  return d.toISOString().slice(0, 10)
}

/** "3 days left" / "5 hours left" / "ended" for a free trial ending at `endsAt` (ISO datetime). */
export function trialLeftLabel(endsAt: string, now = Date.now()) {
  const ms = Date.parse(endsAt) - now
  if (ms <= 0) return 'ended — awaiting payment'
  const hours = Math.ceil(ms / 3_600_000)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} left`
  const days = Math.ceil(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} left`
}

export function formatDateTime(value: string) {
  return new Date(value).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export const STATUS_LABEL: Record<SaasStatus, string> = {
  PENDING: 'Awaiting first payment',
  TRIAL: 'Free trial',
  ACTIVE: 'Active',
  PAST_DUE: 'Payment overdue',
  SUSPENDED: 'Suspended',
  CANCELLED: 'Cancelled',
}

export const METHOD_LABEL: Record<string, string> = {
  UPI: 'UPI',
  CASH: 'Cash',
  BANK_TRANSFER: 'Bank transfer',
  RAZORPAY: 'Razorpay',
}
