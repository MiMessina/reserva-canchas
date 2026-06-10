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
 *   /admin/grid         → DailyGridPage (grilla multi-cancha — JWT)
 *   /admin/operators    → OperatorsPage (gestion de operadores — tenant_admin)
 *   /admin/agent        → ChatDemoPage (chat demo con agente IA — JWT)
 *
 * Layout:
 *   Las rutas /admin/* y / pasan por ProtectedRoute (verifica JWT) →
 *   AdminLayout (navbar + Outlet). La ruta /booking es pública y tiene
 *   su propio header inline; no usa AdminLayout.
 */

import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from './ProtectedRoute'
import { AdminLayout } from '@/components/AdminLayout'
import { DashboardPage } from '@/app/DashboardPage'
import { CourtsListPage } from '@/features/courts/pages/CourtsListPage'
import { CourtDetailPage } from '@/features/courts/pages/CourtDetailPage'
import { BookingPage } from '@/features/booking/pages/BookingPage'
import { BookingsAdminPage } from '@/features/booking/pages/BookingsAdminPage'
import { CashboxPage } from '@/features/booking/pages/CashboxPage'
import { DailyGridPage } from '@/features/booking/pages/DailyGridPage'
import { OperatorsPage } from '@/features/users/pages/OperatorsPage'
import { ChatDemoPage } from '@/features/agent/ChatDemoPage'

const router = createBrowserRouter([
  {
    // Ruta publica: login
    path: '/login',
    element: <LoginPage />,
  },
  {
    // Ruta publica: grilla de turnos (AllowAny — el jugador no necesita cuenta)
    // Tiene su propio header; NO usa AdminLayout.
    path: '/booking',
    element: <BookingPage />,
  },
  {
    // Rutas protegidas (requieren JWT)
    element: <ProtectedRoute />,
    children: [
      {
        // AdminLayout: navbar + Outlet para todas las rutas del panel admin.
        element: <AdminLayout />,
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
          {
            path: '/admin/grid',
            element: <DailyGridPage />,
          },
          {
            path: '/admin/operators',
            element: <OperatorsPage />,
          },
          {
            path: '/admin/agent',
            element: <ChatDemoPage />,
          },
        ],
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
