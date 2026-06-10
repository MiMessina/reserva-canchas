/**
 * components/NavBar.tsx
 * ---------------------
 * Barra de navegación superior del panel admin. Fija, mobile-first.
 *
 * En desktop (md+): logo a la izquierda, links en el centro/derecha, logout a la derecha.
 * En mobile: barra de tabs inferior (bottom tab bar) con íconos y label.
 *   Los links solo se muestran si el rol del usuario los permite:
 *     - Canchas: solo tenant_admin
 *     - Reservas: tenant_admin y operator
 *     - Caja: tenant_admin y operator
 *
 * Usa NavLink de React Router para la clase activa automática.
 * No contiene lógica de negocio: solo navegación y logout.
 */

import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { Home, LayoutGrid, CalendarCheck, Wallet, LogOut, TableProperties, Users, MessageCircle, Moon, Sun, BarChart2 } from 'lucide-react'
import type { JWTPayload } from '@/types/auth'
import { useThemeContext } from '@/context/ThemeContext'

export interface NavBarProps {
  user: Pick<JWTPayload, 'email' | 'role'> | null
  onLogout: () => void
}

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  /** Roles que pueden ver este link. Si es undefined, lo ven todos. */
  allowedRoles?: JWTPayload['role'][]
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    label: 'Inicio',
    icon: <Home size={20} aria-hidden="true" />,
  },
  {
    to: '/admin/courts',
    label: 'Canchas',
    icon: <LayoutGrid size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin'],
  },
  {
    to: '/admin/bookings',
    label: 'Reservas',
    icon: <CalendarCheck size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin', 'operator'],
  },
  {
    to: '/admin/grid',
    label: 'Grilla',
    icon: <TableProperties size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin', 'operator'],
  },
  {
    to: '/admin/cashbox',
    label: 'Caja',
    icon: <Wallet size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin', 'operator'],
  },
  {
    to: '/admin/operators',
    label: 'Operadores',
    icon: <Users size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin'],
  },
  {
    to: '/admin/agent',
    label: 'Asistente',
    icon: <MessageCircle size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin', 'operator'],
  },
  {
    to: '/admin/reports',
    label: 'Reportes',
    icon: <BarChart2 size={20} aria-hidden="true" />,
    allowedRoles: ['tenant_admin', 'operator'],
  },
]

/** Clases del link activo para la topbar de desktop */
function desktopLinkClasses({ isActive }: { isActive: boolean }) {
  return [
    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
    'focus:outline-none focus:ring-2 focus:ring-brand-500',
    isActive
      ? 'bg-brand-50 text-brand-700 dark:bg-brand-900 dark:text-brand-300'
      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:text-gray-100 dark:hover:bg-gray-800',
  ].join(' ')
}

/** Clases del tab activo para la bottom bar de mobile */
function mobileLinkClasses({ isActive }: { isActive: boolean }) {
  return [
    'flex flex-col items-center justify-center gap-0.5 flex-1 py-2 min-h-[48px]',
    'text-xs font-medium transition-colors',
    'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-500',
    isActive
      ? 'text-brand-600 dark:text-brand-400'
      : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200',
  ].join(' ')
}

export function NavBar({ user, onLogout }: NavBarProps) {
  const { theme, toggle } = useThemeContext()

  const visibleItems = NAV_ITEMS.filter(
    (item) =>
      !item.allowedRoles || (user?.role && item.allowedRoles.includes(user.role)),
  )

  return (
    <>
      {/* ── TOP BAR (desktop md+) ───────────────────────────────────────── */}
      <header
        className="hidden md:flex fixed top-0 inset-x-0 z-40 h-16 bg-white border-b border-gray-200 dark:bg-gray-900 dark:border-gray-700 items-center px-6 gap-4"
        role="banner"
      >
        {/* Logo */}
        <div className="flex items-center gap-2 shrink-0 mr-4">
          <div
            className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center"
            aria-hidden="true"
          >
            <span className="text-white font-bold text-sm">C</span>
          </div>
          <span className="text-base font-semibold text-gray-900 dark:text-white tracking-tight">
            CanchaYA
          </span>
        </div>

        {/* Links de navegacion */}
        <nav className="flex items-center gap-1 flex-1" aria-label="Navegacion principal">
          {visibleItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={desktopLinkClasses}>
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Email + toggle + logout */}
        <div className="flex items-center gap-3 shrink-0">
          {user?.email && (
            <span
              className="text-sm text-gray-500 dark:text-gray-400 max-w-[200px] truncate"
              title={user.email}
            >
              {user.email}
            </span>
          )}
          {/* Boton toggle dark mode */}
          <button
            type="button"
            onClick={toggle}
            aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            className="flex items-center justify-center w-8 h-8 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
          <button
            type="button"
            onClick={onLogout}
            aria-label="Cerrar sesion"
            className={[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium',
              'text-gray-600 hover:text-red-600 hover:bg-red-50 dark:text-gray-300 dark:hover:bg-red-900/20 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-red-400',
            ].join(' ')}
          >
            <LogOut size={16} aria-hidden="true" />
            Salir
          </button>
        </div>
      </header>

      {/* ── BOTTOM TAB BAR (mobile, oculta en md+) ──────────────────────── */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200 dark:bg-gray-900 dark:border-gray-700 flex"
        aria-label="Navegacion principal"
      >
        {visibleItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={mobileLinkClasses}>
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}

        {/* Logout como tab final en mobile */}
        <button
          type="button"
          onClick={onLogout}
          aria-label="Cerrar sesion"
          className={[
            'flex flex-col items-center justify-center gap-0.5 flex-1 py-2 min-h-[48px]',
            'text-xs font-medium text-gray-500 hover:text-red-600 transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-red-400',
          ].join(' ')}
        >
          <LogOut size={20} aria-hidden="true" />
          <span>Salir</span>
        </button>
      </nav>

      {/* ── TOP BAR COMPACTA (mobile, solo logo) ────────────────────────── */}
      <header
        className="md:hidden fixed top-0 inset-x-0 z-40 h-14 bg-white border-b border-gray-200 dark:bg-gray-900 dark:border-gray-700 flex items-center px-4 gap-2"
        role="banner"
      >
        <div
          className="w-7 h-7 bg-brand-600 rounded-md flex items-center justify-center"
          aria-hidden="true"
        >
          <span className="text-white font-bold text-xs">C</span>
        </div>
        <span className="text-sm font-semibold text-gray-900 dark:text-white">CanchaYA</span>
        {/* Boton toggle dark mode en mobile */}
        <button
          type="button"
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          className="ml-auto flex items-center justify-center w-8 h-8 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
        </button>
      </header>
    </>
  )
}
