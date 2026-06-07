/**
 * components/ErrorState.tsx
 * -------------------------
 * Estado de error reutilizable.
 * Modos:
 *   - compact: banner inline (ej: error de form/credenciales).
 *   - full (default): pantalla completa de error con opción de reintentar.
 *
 * Maneja errores de negocio (ej: SLOT_ALREADY_BOOKED) con mensaje claro.
 */

import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './Button'

interface ErrorStateProps {
  message?: string
  compact?: boolean
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorState({
  message = 'Ocurrió un error inesperado. Intentá de nuevo.',
  compact = false,
  onRetry,
  retryLabel = 'Reintentar',
}: ErrorStateProps) {
  if (compact) {
    return (
      <div
        role="alert"
        className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700"
      >
        <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span>{message}</span>
      </div>
    )
  }

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center py-16 px-4 text-center"
    >
      <span className="text-red-300 mb-4">
        <AlertCircle size={48} strokeWidth={1.5} aria-hidden="true" />
      </span>
      <h3 className="text-base font-semibold text-gray-700">
        Algo salió mal
      </h3>
      <p className="mt-1 text-sm text-gray-500 max-w-xs">{message}</p>
      {onRetry && (
        <div className="mt-5">
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={onRetry}
          >
            {retryLabel}
          </Button>
        </div>
      )}
    </div>
  )
}
