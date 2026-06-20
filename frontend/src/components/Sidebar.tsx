import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Home, LayoutGrid, CalendarCheck, Wallet, LogOut,
  TableProperties, Users, MessageCircle, BarChart2, Settings,
} from 'lucide-react'
import type { JWTPayload } from '@/types/auth'
import { useSidebar } from '@/context/SidebarContext'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  allowedRoles?: JWTPayload['role'][]
  end?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Inicio', icon: <Home size={20} aria-hidden="true" />, end: true },
  { to: '/admin/courts', label: 'Canchas', icon: <LayoutGrid size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin'] },
  { to: '/admin/bookings', label: 'Reservas', icon: <CalendarCheck size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin', 'operator'] },
  { to: '/admin/grid', label: 'Grilla', icon: <TableProperties size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin', 'operator'] },
  { to: '/admin/cashbox', label: 'Caja', icon: <Wallet size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin', 'operator'] },
  { to: '/admin/operators', label: 'Operadores', icon: <Users size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin'] },
  { to: '/admin/agent', label: 'Asistente', icon: <MessageCircle size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin', 'operator'] },
  { to: '/admin/reports', label: 'Reportes', icon: <BarChart2 size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin', 'operator'] },
  { to: '/admin/settings', label: 'Configuración', icon: <Settings size={20} aria-hidden="true" />, allowedRoles: ['tenant_admin'] },
]

function linkClasses({ isActive }: { isActive: boolean }) {
  return [
    'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors w-full',
    'focus:outline-none focus:ring-2 focus:ring-brand-500',
    isActive
      ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800',
  ].join(' ')
}

export interface SidebarProps {
  user: Pick<JWTPayload, 'email' | 'role'> | null
  onLogout: () => void
}

export function Sidebar({ user, onLogout }: SidebarProps) {
  const { isOpen, close } = useSidebar()

  const visibleItems = NAV_ITEMS.filter(
    item => !item.allowedRoles || (user?.role && item.allowedRoles.includes(user.role))
  )

  function handleNavClick() {
    if (window.innerWidth < 768) close()
  }

  return (
    <>
      {/* Overlay — solo mobile, aparece detrás del sidebar */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px]"
          aria-hidden="true"
          onClick={close}
        />
      )}

      {/* Panel lateral */}
      <aside
        className={[
          'fixed left-0 z-50 flex flex-col w-60',
          'bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700',
          'transition-transform duration-200 ease-in-out',
          /* Desktop: arranca debajo del topbar */
          'md:top-14 md:h-[calc(100vh-3.5rem)]',
          /* Mobile: cubre toda la pantalla incluyendo topbar */
          'top-0 h-full',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
        aria-label="Menú de navegación"
        aria-hidden={!isOpen}
      >
        {/* Cabecera del sidebar — solo visible en mobile (reemplaza el topbar tapado) */}
        <div className="md:hidden flex items-center gap-2 px-4 h-14 border-b border-gray-200 dark:border-gray-700 shrink-0">
          <div
            className="w-7 h-7 bg-brand-600 rounded-md flex items-center justify-center"
            aria-hidden="true"
          >
            <span className="text-white font-bold text-xs">C</span>
          </div>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">CANCHERO!</span>
        </div>

        {/* Ítems de navegación */}
        <nav
          className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5"
          aria-label="Navegación principal"
        >
          {visibleItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={linkClasses}
              onClick={handleNavClick}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Pie: email + logout */}
        <div className="shrink-0 border-t border-gray-200 dark:border-gray-700 p-3">
          {user?.email && (
            <p
              className="px-4 py-1.5 text-xs text-gray-400 dark:text-gray-500 truncate"
              title={user.email}
            >
              {user.email}
            </p>
          )}
          <button
            type="button"
            onClick={onLogout}
            aria-label="Cerrar sesión"
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg w-full text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-red-900/20 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
          >
            <LogOut size={20} aria-hidden="true" />
            Salir
          </button>
        </div>
      </aside>
    </>
  )
}
