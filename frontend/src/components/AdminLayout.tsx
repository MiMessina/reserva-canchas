/**
 * components/AdminLayout.tsx
 * --------------------------
 * Layout del panel de administración (tenant_admin / operator).
 *
 * Estructura:
 *  - SidebarProvider: gestiona el estado abierto/cerrado con persistencia en localStorage.
 *  - NavBar:  topbar fija (h-14) con botón hamburguesa, logo y toggle de tema.
 *  - Sidebar: panel lateral colapsable; en mobile aparece como overlay con backdrop.
 *  - main:    contenido desplazado a la derecha en desktop cuando el sidebar está abierto.
 */

import { Outlet } from 'react-router-dom'
import { NavBar } from './NavBar'
import { Sidebar } from './Sidebar'
import { SidebarProvider, useSidebar } from '@/context/SidebarContext'
import { useAuth } from '@/features/auth/useAuth'

function AdminLayoutInner() {
  const { user, logout } = useAuth()
  const { isOpen } = useSidebar()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <NavBar user={user} onLogout={logout} />
      <Sidebar user={user} onLogout={logout} />

      {/*
       * pt-14:       compensa la topbar fija (h-14) en todos los tamaños.
       * md:ml-60:    en desktop, desplaza el contenido cuando el sidebar está abierto.
       * transition:  animación sincronizada con el sidebar (duration-200).
       */}
      <main
        className={[
          'pt-14 transition-[margin-left] duration-200 ease-in-out',
          isOpen ? 'md:ml-60' : 'md:ml-0',
        ].join(' ')}
      >
        <Outlet />
      </main>
    </div>
  )
}

export function AdminLayout() {
  return (
    <SidebarProvider>
      <AdminLayoutInner />
    </SidebarProvider>
  )
}
