/**
 * routes/AppRouter.tsx
 * --------------------
 * Definición central de rutas (React Router v6).
 *
 * Rutas Sprint 0:
 *   /login        → LoginPage (pública)
 *   /             → DashboardPage (protegida)  — placeholder Sprint 0
 *
 * Rutas futuras (Sprint 1+) — se agregan acá cuando los features estén listos:
 *   /canchas      → courts/CourtsPage
 *   /reservas     → booking/BookingPage (grilla pública)
 *   /caja         → cashbox/CashboxPage
 */

import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from './ProtectedRoute'
import { DashboardPage } from '@/app/DashboardPage'

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
      // Sprint 1+: agregar rutas de features acá
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
