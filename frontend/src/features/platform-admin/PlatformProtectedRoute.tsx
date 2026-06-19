/**
 * features/platform-admin/PlatformProtectedRoute.tsx
 * ----------------------------------------------------
 * Guard de ruta para el panel de platform.
 * Si no hay platform_access_token en localStorage, redirige a /login.
 *
 * La validación real de permisos la hace el backend en cada request;
 * esta redirección es solo UX.
 */

import { Navigate, Outlet } from 'react-router-dom'
import { getPlatformAccessToken } from '@/lib/platformApiClient'

export function PlatformProtectedRoute() {
  const token = getPlatformAccessToken()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
