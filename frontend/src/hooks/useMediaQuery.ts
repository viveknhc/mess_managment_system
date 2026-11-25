import { useSyncExternalStore } from 'react'

/** True while the CSS media query matches; updates on resize/rotation. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query)
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
    () => false,
  )
}

/** Phones and small tablets in portrait — where wide tables become card lists. */
export const MOBILE_QUERY = '(max-width: 767px)'
