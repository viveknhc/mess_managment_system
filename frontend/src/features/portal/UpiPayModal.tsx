import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import type { UpiPayStart } from './portalApi'
import { portalApi } from './portalApi'
import { notify } from '../../utils/notify'

const formatINR = (v: string) => `₹${Number(v).toLocaleString('en-IN')}`

interface Props {
  subId: string
  start: UpiPayStart
  onClose: () => void
  onClaimed: () => void
}

/** Pay the mess's UPI ID: open a UPI app (phone) or scan the QR (computer), then tell the mess. */
export function UpiPayModal({ subId, start, onClose, onClaimed }: Props) {
  const [qr, setQr] = useState('')
  const [utr, setUtr] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    QRCode.toDataURL(start.upi_url, { margin: 1, width: 220 }).then(setQr).catch(() => setQr(''))
  }, [start.upi_url])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !sending && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, sending])

  async function copyUpiId() {
    try {
      await navigator.clipboard.writeText(start.upi_id)
      notify.success('UPI ID copied')
    } catch {
      notify.error('Could not copy. Select the UPI ID and copy it yourself.')
    }
  }

  async function handlePaid() {
    setSending(true)
    const res = await portalApi.claimUpi(subId, utr)
    setSending(false)
    if (!res.ok) {
      notify.error(res.error)
      return
    }
    notify.success('Sent to the mess', 'Your plan updates as soon as they confirm the payment.')
    onClaimed()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
      onClick={() => !sending && onClose()}>
      <div role="dialog" aria-modal="true" aria-labelledby="upi-pay-title"
        className="max-h-[92dvh] w-full max-w-md overflow-y-auto rounded-t-2xl bg-white p-5 shadow-lg sm:rounded-xl sm:p-6"
        onClick={(e) => e.stopPropagation()}>
        <h2 id="upi-pay-title" className="text-lg font-bold text-gray-900">Pay {formatINR(start.amount)} by UPI</h2>
        <p className="mt-1 text-sm text-gray-500">To {start.payee_name}</p>

        {/* Step 1: pay */}
        <div className="mt-4 space-y-3">
          <a href={start.upi_url}
            className="block rounded-lg bg-blue-600 px-4 py-3 text-center text-sm font-semibold text-white hover:bg-blue-700 sm:hidden">
            Open UPI app (GPay, PhonePe, Paytm…)
          </a>
          {qr && (
            <div className="hidden flex-col items-center sm:flex">
              <img src={qr} alt={`UPI QR code to pay ${formatINR(start.amount)}`} className="h-52 w-52" />
              <p className="mt-1 text-xs text-gray-500">Scan with any UPI app on your phone</p>
            </div>
          )}
          <div className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
            <div className="min-w-0">
              <p className="text-xs text-gray-500">Or pay this UPI ID</p>
              <p className="truncate font-mono text-sm text-gray-900">{start.upi_id}</p>
            </div>
            <button type="button" onClick={copyUpiId}
              className="shrink-0 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100">
              Copy
            </button>
          </div>
        </div>

        {/* Step 2: tell the mess */}
        <div className="mt-5 border-t border-gray-100 pt-4">
          <label htmlFor="upi-utr" className="mb-1 block text-sm font-medium text-gray-700">
            UPI reference number <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <input id="upi-utr" value={utr} onChange={(e) => setUtr(e.target.value)} inputMode="numeric"
            placeholder="12-digit number from your UPI app" maxLength={32}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none" />
          <p className="mt-1 text-xs text-gray-500">
            Tap below only after the money has left your account. The mess checks it and then confirms.
          </p>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={sending}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
            Cancel
          </button>
          <button type="button" onClick={handlePaid} disabled={sending}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
            {sending ? 'Sending…' : "I've paid"}
          </button>
        </div>
      </div>
    </div>
  )
}
