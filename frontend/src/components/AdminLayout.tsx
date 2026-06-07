/**
 * components/AdminLayout.tsx
 * --------------------------
 * Layout del panel de administracion (tenant_admin / operator).
 * Compone NavBar + <Outlet /> de React Router.
 *
 * Obtiene user y logout desde useAuth() internamente.
 * No contiene lógica de negocio: solo estructura visual del panel.
 *
 * Padding-top compensa la topbar fija en desktop (h-16 = pt-16).
 * Padding-bottom compensa la bottom tab bar en mobile (h-~16 = pb-16).
 */

import { Outlet } from 'react-router-dom'
import { NavBar } from './NavBar'
import { useAuth } from '@/features/auth/useAuth'

export function AdminLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar user={user} onLogout={logout} />

      {/*
       * pt-14: compensa la topbar compacta de mobile (h-14).
       * pb-16: compensa la bottom tab bar de mobile.
       * md:pt-16 md:pb-0: en desktop, topbar alta (h-16) y sin bottom bar.
       */}
      <main className="pt-14 pb-16 md:pt-16 md:pb-0">
        <Outlet />
      </main>
    </div>
  )
}
