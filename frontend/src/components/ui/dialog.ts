import type { ReactNode } from 'react'

/**
 * App-wide confirm / choice popups. Call from anywhere — no hooks or context needed:
 *
 *   if (!(await confirmDialog({ title: 'Delete plan?', tone: 'danger', confirmText: 'Delete' }))) return
 *   const reason = await promptDialog({ title: 'Why not delivered?', options: ['Door locked', ...] })
 *
 * <DialogHost /> (DialogHost.tsx, mounted once in App) renders the open dialog. Bottom sheet on phones, centered on desktop.
 */

export type Tone = 'primary' | 'danger' | 'success'

export interface BaseOptions {
  title: string
  message?: ReactNode
  confirmText?: string
  cancelText?: string
  tone?: Tone
}

export interface PromptOptions extends BaseOptions {
  /** Quick-pick answers shown as chips; picking one fills the text box. */
  options?: string[]
  placeholder?: string
  /** Require some text before confirming (default true). */
  required?: boolean
  initialValue?: string
}

export type Request = { id: number } & (
  | { kind: 'confirm'; opts: BaseOptions; resolve: (ok: boolean) => void }
  | { kind: 'prompt'; opts: PromptOptions; resolve: (value: string | null) => void }
)

let current: Request | null = null
let nextId = 1
const listeners = new Set<() => void>()

function setCurrent(next: Request | null) {
  current = next
  listeners.forEach((l) => l())
}

export function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function confirmDialog(opts: BaseOptions): Promise<boolean> {
  return new Promise((resolve) => {
    if (current) closeWith(null) // only one dialog at a time
    setCurrent({ id: nextId++, kind: 'confirm', opts, resolve })
  })
}

export function promptDialog(opts: PromptOptions): Promise<string | null> {
  return new Promise((resolve) => {
    if (current) closeWith(null)
    setCurrent({ id: nextId++, kind: 'prompt', opts, resolve })
  })
}

export function closeWith(value: string | boolean | null) {
  const req = current
  if (!req) return
  setCurrent(null)
  if (req.kind === 'confirm') req.resolve(value === true)
  else req.resolve(typeof value === 'string' ? value : null)
}

export function getCurrent() {
  return current
}
