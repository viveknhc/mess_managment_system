/**
 * JWT token persistence.
 *
 * Dev: sessionStorage — each browser tab keeps its own login, so you can be
 * signed in as owner / staff / customer / super admin side by side in one window.
 * Prod: localStorage — login is shared across tabs and survives closing the tab.
 *
 * Override with VITE_AUTH_STORAGE=session|local.
 */

const mode = import.meta.env.VITE_AUTH_STORAGE ?? (import.meta.env.DEV ? 'session' : 'local')
const storage: Storage = mode === 'session' ? sessionStorage : localStorage

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export const tokenStorage = {
  getAccess: () => storage.getItem(ACCESS_KEY),
  getRefresh: () => storage.getItem(REFRESH_KEY),
  setTokens: (access: string, refresh?: string) => {
    storage.setItem(ACCESS_KEY, access)
    if (refresh) storage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    storage.removeItem(ACCESS_KEY)
    storage.removeItem(REFRESH_KEY)
  },
}
