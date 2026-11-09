/**
 * MessDeck support contact — the single place the app reads it from.
 *
 * Set in frontend/.env (see .env.example):
 *   VITE_SUPPORT_WHATSAPP  country code + number, digits only (e.g. 919876543210)
 *   VITE_SUPPORT_EMAIL     support inbox
 *
 * TODO: replace the placeholder fallbacks below with the real WhatsApp number and email before going live.
 */
export const SUPPORT_WHATSAPP: string = import.meta.env.VITE_SUPPORT_WHATSAPP || '910000000000'
export const SUPPORT_EMAIL: string = import.meta.env.VITE_SUPPORT_EMAIL || 'support@messdeck.in'

/** wa.me link that opens a WhatsApp chat with support, optionally with a prefilled message. */
export function whatsappLink(message?: string) {
  const base = `https://wa.me/${SUPPORT_WHATSAPP}`
  return message ? `${base}?text=${encodeURIComponent(message)}` : base
}

/** mailto: link to the support inbox, optionally with a subject. */
export function supportEmailLink(subject?: string) {
  return subject ? `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(subject)}` : `mailto:${SUPPORT_EMAIL}`
}

/** "+91 00000 00000"-style display of the WhatsApp number. */
export function formatWhatsapp(number = SUPPORT_WHATSAPP) {
  if (number.length === 12 && number.startsWith('91')) return `+91 ${number.slice(2, 7)} ${number.slice(7)}`
  return `+${number}`
}
