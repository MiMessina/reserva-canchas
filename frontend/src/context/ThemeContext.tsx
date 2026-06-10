/**
 * context/ThemeContext.tsx
 * ------------------------
 * Contexto global de tema (light/dark).
 * ThemeProvider envuelve la app en Providers.tsx.
 * useThemeContext() da acceso al tema actual y al toggle desde cualquier componente.
 */

import { createContext, useContext, type ReactNode } from 'react'
import { useTheme } from '@/hooks/useTheme'

interface ThemeContextValue {
  theme: 'light' | 'dark'
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme()
  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useThemeContext() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useThemeContext debe usarse dentro de ThemeProvider')
  return ctx
}
