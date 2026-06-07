/**
 * routes/AppRouter.tsx
 * --------------------
 * Definición central de rutas (React Router v6).
 *
 * Rutas Sprint 0:
 *   /login        → LoginPage (pública)
 *   /             → DashboardPage (protegida) — redirige a /admin/courts
 *
 * Rutas Sprint 1:
 *   /admin/courts      → CourtsListPage (lista de canchas)
 *   /admin/courts/:id  → CourtDetailPage (detalle de cancha)
 *
 * Rutas futuras (Sprint 2+):
 *   /reservas     → booking/BookingPage (grilla pública)
 *   /caja         → cashbox/CashboxPage
 */

import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from './ProtectedRoute'
import { DashboardPage } from '@/app/DashboardPage'
import { CourtsListPage } from '@/features/courts/pages/CourtsListPage'
import { CourtDetailPage } from '@/features/courts/pages/CourtDetailPage'

const router = createBrowserRouter([
  {
    // Ruta pública: login
    path: '/login',
    element: <LoginPage />,
  },
  {
    // Rutas protegidas
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <DashboardPage />,
      },
      {
        path: '/admin/courts',
        element: <CourtsListPage />,
      },
      {
        path: '/admin/courts/:id',
        element: <CourtDetailPage />,
      },
    ],
  },
  {
    // Fallback: cualquier ruta desconocida va al root (que redirige según auth)
    path: '*',
    element: <Navigate to="/" replace />,
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
