/**
 * app/DashboardPage.tsx
 * ---------------------
 * PLACEHOLDER — Sprint 0.
 * Pantalla protegida mínima que confirma la sesión iniciada.
 *
 * En Sprint 1 se reemplaza por el panel real (Admin: gestión de canchas /
 * Cajero: caja del día / Jugador: grilla de reservas).
 * El rol del usuario determina qué panel mostrar; la lógica de routing
 * fino por rol se agrega en Sprint 1.
 */

import { LogOut, CheckCircle } from 'lucide-react'
import { useAuth } from '@/features/auth/useAuth'
import { Button } from '@/components/Button'
import { nowBA } from '@/lib/datetime'

export function DashboardPage() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header mínimo */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">C</span>
          </div>
          <span className="font-semibold text-gray-900 text-sm">CanchaYA</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<LogOut size={14} />}
          onClick={logout}
          aria-label="Cerrar sesión"
        >
          Salir
        </Button>
      </header>

      {/* Contenido placeholder */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12 text-center">
        <span className="text-brand-500 mb-4">
          <CheckCircle size={56} strokeWidth={1.5} aria-hidden="true" />
        </span>
        <h1 className="text-xl font-bold text-gray-900">Sesion iniciada</h1>
        {user && (
          <p className="mt-2 text-sm text-gray-600">
            Bienvenido, <strong>{user.email}</strong>
          </p>
        )}
        {user?.role && (
          <span className="mt-3 inline-block bg-brand-100 text-brand-700 text-xs font-medium px-2.5 py-1 rounded-full">
            Rol: {user.role}
          </span>
        )}
        <p className="mt-6 text-xs text-gray-400">{nowBA()}</p>

        {/* Aviso de placeholder */}
        <div className="mt-8 max-w-sm rounded-xl border border-dashed border-gray-300 bg-white p-5 text-left">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Sprint 0 — Placeholder
          </p>
          <p className="text-sm text-gray-600">
            El panel real (grilla de canchas, reservas y caja) se construye en
            Sprint 1. Esta pantalla confirma que el login JWT funciona
            correctamente y que la sesion esta protegida.
          </p>
        </div>
      </main>
    </div>
  )
}
