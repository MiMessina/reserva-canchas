/**
 * app/DashboardPage.tsx
 * ---------------------
 * Sprint 1: redirige al panel principal según rol.
 * - tenant_admin / operator / player → /admin/courts
 *   (la grilla pública del jugador se implementa en Sprint 2)
 */

import { Navigate } from 'react-router-dom'

export function DashboardPage() {
  return <Navigate to="/admin/courts" replace />
}
