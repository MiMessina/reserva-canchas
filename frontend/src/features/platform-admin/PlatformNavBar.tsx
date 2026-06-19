/**
 * features/platform-admin/PlatformNavBar.tsx
 * --------------------------------------------
 * Navbar del panel de System Admin.
 * Visualmente distinta a la del tenant-admin para dejar en claro
 * que es el panel de la plataforma, no de un complejo.
 *
 * Desktop: topbar fija con logo "CANCHERO! — Plataforma", email del admin,
 *          toggle dark mode y botón logout.
 * Mobile: topbar compacta (solo logo) + bottom bar con logout.
 */

import { LogOut, Shield, Moon, Sun } from 'lucide-react'
import { useThemeContext } from '@/context/ThemeContext'

interface PlatformNavBarProps {
  email?: string
  onLogout: () => void
}

export function PlatformNavBar({ email, onLogout }: PlatformNavBarProps) {
  const { theme, toggle } = useThemeContext()

  return (
    <>
      {/* ── TOP BAR (desktop md+) ───────────────────────────────────────── */}
      <header
        className="hidden md:flex fixed top-0 inset-x-0 z-40 h-16 bg-gray-900 border-b border-gray-700 items-center px-6 gap-4"
        role="banner"
      >
        {/* Logo */}
        <div className="flex items-center gap-2 shrink-0 mr-4">
          <div
            className="w-8 h-8 bg-gray-700 rounded-lg flex items-center justify-center"
            aria-hidden="true"
          >
            <Shield className="text-gray-300" size={16} />
          </div>
          <div>
            <span className="text-sm font-semibold text-white tracking-tight">
              CANCHERO!
            </span>
            <span className="text-sm text-gray-400 ml-1">— Plataforma</span>
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Email + toggle + logout */}
        <div className="flex items-center gap-3 shrink-0">
          {email && (
            <span
              className="text-sm text-gray-400 max-w-[200px] truncate"
              title={email}
            >
              {email}
            </span>
          )}
          {/* Toggle dark mode */}
          <button
            type="button"
            onClick={toggle}
            aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            className="flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
          <button
            type="button"
            onClick={onLogout}
            aria-label="Cerrar sesión"
            className={[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium',
              'text-gray-300 hover:text-red-400 hover:bg-gray-800 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-red-400',
            ].join(' ')}
          >
            <LogOut size={16} aria-hidden="true" />
            Salir
          </button>
        </div>
      </header>

      {/* ── TOP BAR COMPACTA (mobile) ────────────────────────────────────── */}
      <header
        className="md:hidden fixed top-0 inset-x-0 z-40 h-14 bg-gray-900 border-b border-gray-700 flex items-center px-4 gap-2"
        role="banner"
      >
        <div
          className="w-7 h-7 bg-gray-700 rounded-md flex items-center justify-center"
          aria-hidden="true"
        >
          <Shield className="text-gray-300" size={14} />
        </div>
        <span className="text-sm font-semibold text-white">Plataforma</span>
        <button
          type="button"
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          className="ml-auto flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500"
        >
          {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
        </button>
      </header>

      {/* ── BOTTOM BAR (mobile) ──────────────────────────────────────────── */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-gray-900 border-t border-gray-700 flex items-center justify-center"
        aria-label="Navegación de plataforma"
      >
        <button
          type="button"
          onClick={onLogout}
          aria-label="Cerrar sesión"
          className={[
            'flex flex-col items-center justify-center gap-0.5 min-w-[80px] py-3 min-h-[56px] px-4',
            'text-xs font-medium text-gray-400 hover:text-red-400 transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-red-400',
          ].join(' ')}
        >
          <LogOut size={20} aria-hidden="true" />
          <span>Salir</span>
        </button>
      </nav>
    </>
  )
}
