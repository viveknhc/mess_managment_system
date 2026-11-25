import { useEffect } from 'react'
import { useAppTheme } from '../hooks/useAppTheme'

/** Puts the current theme on <html data-theme>, so toasts and dialogs (outside the layouts) match. */
export function ThemeSync() {
  const theme = useAppTheme()
  useEffect(() => {
    const root = document.documentElement
    if (theme) root.dataset.theme = theme
    else delete root.dataset.theme
  }, [theme])
  return null
}
