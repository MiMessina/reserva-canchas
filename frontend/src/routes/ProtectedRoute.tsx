/**
 * routes/ProtectedRoute.tsx
 * -------------------------
 * Wrapper de ruta protegida.
 * Si no hay token en localStorage, redirige a /login.
 * El backend es quien valida el token en cada request;
 * esta redirección es solo UX (evita renderizar pantallas vacías).
 */

import { Navigate, Outlet } from 'react-router-dom'
import { getAccessToken } from '@/lib/axios'

interface ProtectedRouteProps {
  /** Si se pasa, solo renderiza si el usuario tiene ese rol. */
  requiredRole?: string
}

export function ProtectedRoute({ requiredRole: _requiredRole }: ProtectedRouteProps) {
  const token = getAccessToken()

  if (!token) {
    // Sin token: redirigir a login. Guardar la ruta de origen para post-login (sprint 1).
    return <Navigate to="/login" replace />
  }

  // NOTA Sprint 0: la validación de rol fino queda como placeholder.
  // En Sprint 1 se decodifica el payload JWT y se valida requiredRole.
  // El backend rechaza cualquier acción no permitida por el rol.

  return <Outlet />
}
