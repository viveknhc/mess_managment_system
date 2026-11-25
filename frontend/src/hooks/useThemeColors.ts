import { useEffect, useState } from 'react'
import { useAppTheme } from './useAppTheme'

export interface ThemeColors {
  accent: string
  accentInk: string
  surface: string
  muted: string // low bars, grid
  soft: string // medium bars
  text: string
  subtle: string // axis labels
}

const LIGHT: ThemeColors = {
  accent: '#2563eb', accentInk: '#ffffff', surface: '#ffffff', muted: '#e5e7eb', soft: '#9ca3af', text: '#111827', subtle: '#6b7280',
}

/** Resolved theme colours for charts (SVG attributes can't use CSS variables). Updates when the role theme changes. */
export function useThemeColors(): ThemeColors {
  const theme = useAppTheme()
  const [colors, setColors] = useState<ThemeColors>(LIGHT)
  useEffect(() => {
    // Wait a frame so ThemeSync has written <html data-theme> first.
    const id = requestAnimationFrame(() => {
      const css = getComputedStyle(document.documentElement)
      const v = (name: string, fallback: string) => css.getPropertyValue(name).trim() || fallback
      setColors(
        theme
          ? {
              accent: v('--accent', LIGHT.accent),
              accentInk: v('--accent-ink', LIGHT.accentInk),
              surface: v('--surface', LIGHT.surface),
              muted: v('--color-gray-300', '#3e3e45'),
              soft: v('--color-gray-700', '#d3d3d9'),
              text: v('--color-gray-900', '#f5f5f7'),
              subtle: v('--color-gray-500', '#90909a'),
            }
          : LIGHT,
      )
    })
    return () => cancelAnimationFrame(id)
  }, [theme])
  return colors
}
