/**
 * routes/AppRouter.tsx
 * --------------------
 * Definicion central de rutas (React Router v6).
 *
 * Rutas Sprint 0:
 *   /login        → LoginPage (publica)
 *   /             → DashboardPage (protegida) — redirige a /admin/courts
 *
 * Rutas Sprint 1:
 *   /admin/courts      → CourtsListPage (lista de canchas)
 *   /admin/courts/:id  → CourtDetailPage (detalle de cancha)
 *
 * Rutas Sprint 2:
 *   /booking            → BookingPage (grilla publica de turnos — sin auth)
 *   /admin/bookings     → BookingsAdminPage (panel operator/admin — JWT)
 *   /admin/cashbox      → CashboxPage (caja diaria — JWT)
 */

import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from './ProtectedRoute'
import { DashboardPage } from '@/app/DashboardPage'
import { CourtsListPage } from '@/features/courts/pages/CourtsListPage'
import { CourtDetailPage } from '@/features/courts/pages/CourtDetailPage'
import { BookingPage } from '@/features/booking/pages/BookingPage'
import { BookingsAdminPage } from '@/features/booking/pages/BookingsAdminPage'
import { CashboxPage } from '@/features/booking/pages/CashboxPage'

const router = createBrowserRouter([
  {
    // Ruta publica: login
    path: '/login',
    element: <LoginPage />,
  },
  {
    // Ruta publica: grilla de turnos (AllowAny — el jugador no necesita cuenta)
    path: '/booking',
    element: <BookingPage />,
  },
  {
    // Rutas protegidas (requieren JWT)
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
      {
        path: '/admin/bookings',
        element: <BookingsAdminPage />,
      },
      {
        path: '/admin/cashbox',
        element: <CashboxPage />,
      },
    ],
  },
  {
    // Fallback: cualquier ruta desconocida va al root (que redirige segun auth)
    path: '*',
    element: <Navigate to="/" replace />,
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
