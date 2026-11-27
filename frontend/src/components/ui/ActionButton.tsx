import type { ButtonHTMLAttributes } from 'react'

type Tone = 'primary' | 'neutral' | 'success' | 'danger' | 'warning' | 'accent'

/**
 * Small button for table rows and cards.
 *
 * Deliberately unlike a status badge (flat, borderless, rounded-full): a border, a card
 * background, a light shadow, a rounded-rectangle shape, and a press effect, so "Active"
 * reads as a label and "Deactivate" reads as something to tap.
 *
 * `solid` is for the one main action in a row (e.g. Delivered); everything else is outline.
 */
const OUTLINE: Record<Tone, string> = {
  primary: 'border-blue-300 text-blue-700 hover:border-blue-400 hover:bg-blue-50',
  neutral: 'border-gray-300 text-gray-700 hover:border-gray-400 hover:bg-gray-50',
  success: 'border-green-300 text-green-700 hover:border-green-400 hover:bg-green-50',
  danger: 'border-red-300 text-red-700 hover:border-red-400 hover:bg-red-50',
  warning: 'border-orange-300 text-orange-700 hover:border-orange-400 hover:bg-orange-50',
  accent: 'border-purple-300 text-purple-700 hover:border-purple-400 hover:bg-purple-50',
}

const SOLID: Record<Tone, string> = {
  primary: 'border-blue-600 bg-blue-600 text-white hover:bg-blue-700',
  neutral: 'border-gray-700 bg-gray-700 text-white hover:bg-gray-800',
  success: 'border-green-600 bg-green-600 text-white hover:bg-green-700',
  danger: 'border-red-600 bg-red-600 text-white hover:bg-red-700',
  warning: 'border-orange-500 bg-orange-500 text-white hover:bg-orange-600',
  accent: 'border-purple-600 bg-purple-600 text-white hover:bg-purple-700',
}

export function ActionButton({
  tone = 'neutral',
  solid = false,
  className = '',
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone; solid?: boolean }) {
  return (
    <button
      type={type}
      className={`inline-flex cursor-pointer items-center justify-center gap-1 whitespace-nowrap rounded-lg border px-2.5 py-1 text-xs font-semibold shadow-sm transition select-none active:scale-[0.97] focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${
        solid ? SOLID[tone] : `bg-white ${OUTLINE[tone]}`
      } ${className}`}
      {...props}
    />
  )
}
