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

export const STATUS_LABEL: Record<SaasStatus, string> = {
  PENDING: 'Awaiting first payment',
  TRIAL: 'Trial',
  ACTIVE: 'Active',
  PAST_DUE: 'Payment overdue',
  SUSPENDED: 'Suspended',
  CANCELLED: 'Cancelled',
}

export const STATUS_COLOR: Record<SaasStatus, string> = {
  PENDING: 'bg-blue-100 text-blue-700',
  TRIAL: 'bg-blue-100 text-blue-700',
  ACTIVE: 'bg-green-100 text-green-700',
  PAST_DUE: 'bg-yellow-100 text-yellow-700',
  SUSPENDED: 'bg-red-100 text-red-700',
  CANCELLED: 'bg-gray-100 text-gray-700',
}

export const METHOD_LABEL: Record<string, string> = {
  UPI: 'UPI',
  CASH: 'Cash',
  BANK_TRANSFER: 'Bank transfer',
  RAZORPAY: 'Razorpay',
}
