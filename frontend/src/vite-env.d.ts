/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_AUTH_STORAGE?: 'session' | 'local'
  /** Support WhatsApp number, country code + digits (src/config/support.ts) */
  readonly VITE_SUPPORT_WHATSAPP?: string
  /** Support email (src/config/support.ts) */
  readonly VITE_SUPPORT_EMAIL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
