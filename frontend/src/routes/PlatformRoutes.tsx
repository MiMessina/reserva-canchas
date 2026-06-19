/**
 * routes/PlatformRoutes.tsx
 * -------------------------
 * Router del panel de System Admin (platform.localhost).
 * Solo se renderiza cuando el hostname empieza con "platform."
 * (ver AppRouter.tsx — routing condicional por hostname).
 *
 * Rutas:
 *   /login           → PlatformLoginPage (pública)
 *   /                → TenantListPage (requiere auth de platform)
 *   /tenants/:id     → TenantDetailPage (requiere auth de platform)
 *   *                → redirige a /
 */

import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { PlatformLoginPage } from '@/features/platform-admin/PlatformLoginPage'
import { PlatformLayout } from '@/features/platform-admin/PlatformLayout'
import { PlatformProtectedRoute } from '@/features/platform-admin/PlatformProtectedRoute'
import { TenantListPage } from '@/features/platform-admin/TenantListPage'
import { TenantDetailPage } from '@/features/platform-admin/TenantDetailPage'

const platformRouter = createBrowserRouter([
  {
    path: '/login',
    element: <PlatformLoginPage />,
  },
  {
    element: <PlatformProtectedRoute />,
    children: [
      {
        element: <PlatformLayout />,
        children: [
          {
            path: '/',
            element: <TenantListPage />,
          },
          {
            path: '/tenants/:id',
            element: <TenantDetailPage />,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])

export function PlatformRoutes() {
  return <RouterProvider router={platformRouter} />
}
