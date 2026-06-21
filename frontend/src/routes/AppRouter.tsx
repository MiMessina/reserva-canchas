/**
 * routes/AppRouter.tsx
 * --------------------
 * Definicion central de rutas (React Router v6).
 *
 * ROUTING CONDICIONAL POR HOSTNAME (ADR-013 + Sprint 14):
 *   1. hostname empieza con "platform." → PlatformRoutes (panel System Admin)
 *   2. hostname es "app.localhost"      → CentralLoginRoutes (login centralizado)
 *   3. cualquier otro hostname          → rutas de tenant (el existente)
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
 *   /mis-reservas       → MyBookingsPage (consulta de reservas del jugador — sin auth)
 *   /admin/bookings     → BookingsAdminPage (panel operator/admin — JWT)
 *   /admin/cashbox      → CashboxPage (caja diaria — JWT)
 *   /admin/grid         → DailyGridPage (grilla multi-cancha — JWT)
 *   /admin/operators    → OperatorsPage (gestion de operadores — tenant_admin)
 *   /admin/agent        → ChatDemoPage (chat demo con agente IA — JWT)
 *   /admin/reports      → ReportsPage (reportes semanales — operator/admin)
 *   /admin/settings     → SettingsPage (configuracion del complejo — tenant_admin)
 *
 * Rutas de recuperación de contraseña (publicas — sin JWT):
 *   /forgot-password              → ForgotPasswordPage
 *   /reset-password/:uid/:token   → ResetPasswordPage
 *
 * Rutas Sprint 14/16 (login centralizado — app.localhost):
 *   /login          → CentralLoginPage
 *   /auth/callback  → AuthCallbackPage (ruta pública — intercambia OTC por JWT)
 *
 * Layout:
 *   Las rutas /admin/* y / pasan por ProtectedRoute (verifica JWT) →
 *   AdminLayout (navbar + Outlet). Las rutas /booking y /mis-reservas son
 *   públicas y tienen su propio header inline; no usan AdminLayout.
 *
 *   TenantRootLayout: layout raíz invisible del router de tenant.
 *   El intercambio del ?code= ahora ocurre en AuthCallbackPage (/auth/callback).
 */

import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom'
import { PlatformRoutes } from './PlatformRoutes'
import { LoginPage } from '@/features/auth/LoginPage'
import { CentralLoginPage } from '@/features/auth/CentralLoginPage'
import { AuthCallbackPage } from '@/features/auth/AuthCallbackPage'
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage'
import { ResetPasswordPage } from '@/features/auth/ResetPasswordPage'
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
import { ReportsPage } from '@/features/reports/ReportsPage'
import { MyBookingsPage } from '@/features/myBookings/MyBookingsPage'
import { SettingsPage } from '@/features/settings/SettingsPage'

// ─── Routing condicional por hostname (ADR-013 + Sprint 14) ──────────────────
// Evaluado una sola vez al cargar el módulo (no cambia durante la sesión).

const isPlatformAdmin = window.location.hostname.startsWith('platform.')
const isCentralLogin = window.location.hostname === 'app.localhost'

// ─── Layout raíz del tenant ───────────────────────────────────────────────────
// Componente invisible que envuelve todas las rutas del tenant.
// El intercambio de OTC ahora ocurre en AuthCallbackPage (/auth/callback).
function TenantRootLayout() {
  return <Outlet />
}

// ─── Router del tenant ────────────────────────────────────────────────────────

const tenantRouter = createBrowserRouter([
  {
    // Layout raíz: monta useCodeExchange sin alterar el HTML.
    element: <TenantRootLayout />,
    children: [
      {
        // Ruta publica: login
        path: '/login',
        element: <LoginPage />,
      },
      {
        // Ruta publica: callback del login centralizado (patrón OAuth2)
        // Intercambia el ?code= OTC por JWT — fuera de ProtectedRoute para evitar race condition.
        path: '/auth/callback',
        element: <AuthCallbackPage />,
      },
      {
        // Ruta publica: grilla de turnos (AllowAny — el jugador no necesita cuenta)
        // Tiene su propio header; NO usa AdminLayout.
        path: '/booking',
        element: <BookingPage />,
      },
      {
        // Ruta publica: consulta de reservas por telefono (sin auth)
        path: '/mis-reservas',
        element: <MyBookingsPage />,
      },
      {
        // Ruta publica: solicitud de recuperacion de contraseña
        path: '/forgot-password',
        element: <ForgotPasswordPage />,
      },
      {
        // Ruta publica: confirmacion del reset de contraseña (link del email)
        path: '/reset-password/:uid/:token',
        element: <ResetPasswordPage />,
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
              {
                path: '/admin/reports',
                element: <ReportsPage />,
              },
              {
                path: '/admin/settings',
                element: <SettingsPage />,
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
    ],
  },
])

// ─── Router de login centralizado (app.localhost) ─────────────────────────────

const centralRouter = createBrowserRouter([
  {
    path: '/login',
    element: <CentralLoginPage />,
  },
  {
    // Cualquier otra ruta en app.localhost redirige al login central
    path: '*',
    element: <Navigate to="/login" replace />,
  },
])

// ─── AppRouter ────────────────────────────────────────────────────────────────

export function AppRouter() {
  // 1. hostname platform.* → panel de System Admin
  if (isPlatformAdmin) {
    return <PlatformRoutes />
  }

  // 2. hostname app.localhost → login centralizado (Sprint 14)
  if (isCentralLogin) {
    return <RouterProvider router={centralRouter} />
  }

  // 3. Cualquier otro hostname → rutas del tenant
  return <RouterProvider router={tenantRouter} />
}
