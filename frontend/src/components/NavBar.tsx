/**
 * components/NavBar.tsx
 * ---------------------
 * Topbar fija del panel admin: botón hamburguesa, logo y toggle de tema.
 * La navegación vive en Sidebar.tsx; el logout está en el pie del Sidebar.
 */

import { Menu, Moon, Sun } from 'lucide-react'
import type { JWTPayload } from '@/types/auth'
import { useThemeContext } from '@/context/ThemeContext'
import { useSidebar } from '@/context/SidebarContext'
import { useTenantInfo } from '@/hooks/useTenantInfo'
import logoUrl from '@/assets/logo.svg'

export interface NavBarProps {
  user: Pick<JWTPayload, 'email' | 'role'> | null
  onLogout: () => void
}

export function NavBar({ user }: NavBarProps) {
  const { theme, toggle } = useThemeContext()
  const { toggle: toggleSidebar } = useSidebar()
  const { complexName } = useTenantInfo()

  return (
    <header
      className="fixed top-0 inset-x-0 z-30 h-14 bg-white border-b border-gray-200 dark:bg-gray-900 dark:border-gray-700 flex items-center px-4 gap-3"
      role="banner"
    >
      {/* Botón hamburguesa */}
      <button
        type="button"
        onClick={toggleSidebar}
        aria-label="Abrir o cerrar menú de navegación"
        className="flex items-center justify-center w-9 h-9 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        <Menu size={22} aria-hidden="true" />
      </button>

      {/* Logo — isotipo oficial (escudo deportivo) */}
      <div className="flex items-center gap-2">
        <img src={logoUrl} alt="" aria-hidden="true" className="h-8 w-auto" />
        <span className="text-sm font-semibold text-gray-900 dark:text-white">{complexName}</span>
      </div>

      <div className="flex-1" />

      {/* Email del usuario — solo visible en desktop */}
      {user?.email && (
        <span
          className="hidden md:block text-sm text-gray-500 dark:text-gray-400 max-w-[200px] truncate"
          title={user.email}
        >
          {user.email}
        </span>
      )}

      {/* Toggle dark / light mode */}
      <button
        type="button"
        onClick={toggle}
        aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
        className="flex items-center justify-center w-8 h-8 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
      </button>
    </header>
  )
}
