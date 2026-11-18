import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { closeWith, getCurrent, subscribe, type Request, type Tone } from './dialog'

const TONE_BUTTON: Record<Tone, string> = {
  primary: 'bg-primary-600 hover:bg-primary-700 focus-visible:outline-primary-600',
  danger: 'bg-red-600 hover:bg-red-700 focus-visible:outline-red-600',
  success: 'bg-green-600 hover:bg-green-700 focus-visible:outline-green-600',
}

const TONE_ICON: Record<Tone, { bg: string; path: string }> = {
  primary: { bg: 'bg-primary-100 text-primary-600', path: 'M12 9v4m0 4h.01M12 3a9 9 0 110 18 9 9 0 010-18z' },
  danger: { bg: 'bg-red-100 text-red-600', path: 'M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z' },
  success: { bg: 'bg-green-100 text-green-600', path: 'M5 13l4 4L19 7' },
}

function DialogBody({ req }: { req: Request }) {
  const tone = req.opts.tone ?? 'primary'
  const [value, setValue] = useState(req.kind === 'prompt' ? (req.opts.initialValue ?? '') : '')
  const [show, setShow] = useState(false)
  const confirmRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const required = req.kind === 'prompt' && (req.opts.required ?? true)
  const canConfirm = !required || value.trim().length > 0

  useEffect(() => {
    const raf = requestAnimationFrame(() => setShow(true))
    const focusTarget = req.kind === 'prompt' && !req.opts.options?.length ? inputRef.current : confirmRef.current
    focusTarget?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') closeWith(null)
    }
    document.addEventListener('keydown', onKey)
    return () => {
      cancelAnimationFrame(raf)
      document.removeEventListener('keydown', onKey)
    }
  }, [req])

  function submit() {
    if (!canConfirm) return
    closeWith(req.kind === 'confirm' ? true : value.trim())
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center sm:p-4">
      <div
        className={`absolute inset-0 bg-gray-900/50 backdrop-blur-[2px] transition-opacity duration-200 ${show ? 'opacity-100' : 'opacity-0'}`}
        onClick={() => closeWith(null)}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="app-dialog-title"
        className={`relative w-full max-w-md rounded-t-2xl bg-white p-6 shadow-2xl transition-all duration-200 ease-out sm:rounded-2xl ${
          show ? 'translate-y-0 opacity-100 sm:scale-100' : 'translate-y-8 opacity-0 sm:translate-y-0 sm:scale-95'
        }`}
      >
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-gray-200 sm:hidden" aria-hidden="true" />
        <div className="flex gap-4">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${TONE_ICON[tone].bg}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d={TONE_ICON[tone].path} />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <h2 id="app-dialog-title" className="text-base font-semibold text-gray-900">
              {req.opts.title}
            </h2>
            {req.opts.message && <div className="mt-1 text-sm text-gray-600">{req.opts.message}</div>}
          </div>
        </div>

        {req.kind === 'prompt' && (
          <div className="mt-4 space-y-3">
            {req.opts.options && req.opts.options.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {req.opts.options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => setValue(opt)}
                    className={`rounded-full border px-3 py-2 text-sm transition ${
                      value === opt
                        ? 'border-primary-600 bg-primary-50 font-medium text-primary-700'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              rows={2}
              placeholder={req.opts.placeholder ?? 'Type here'}
              aria-label={req.opts.title}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
            />
          </div>
        )}

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => closeWith(null)}
            className="rounded-xl border border-gray-300 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 sm:py-2"
          >
            {req.opts.cancelText ?? 'Cancel'}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={submit}
            disabled={!canConfirm}
            className={`rounded-xl px-4 py-3 text-sm font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-40 sm:py-2 ${TONE_BUTTON[tone]}`}
          >
            {req.opts.confirmText ?? 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function DialogHost() {
  const req = useSyncExternalStore(subscribe, getCurrent)
  return req ? <DialogBody key={req.id} req={req} /> : null
}
