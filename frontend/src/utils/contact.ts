// TODO: replace with the real WhatsApp number (country code, no + or spaces) before going live.
export const CONTACT_WHATSAPP = '910000000000'

export function whatsappLink(message: string) {
  return `https://wa.me/${CONTACT_WHATSAPP}?text=${encodeURIComponent(message)}`
}
