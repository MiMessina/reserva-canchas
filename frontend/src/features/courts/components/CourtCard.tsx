/**
 * features/courts/components/CourtCard.tsx
 * ------------------------------------------
 * Tarjeta de cancha para el listado (mobile-first).
 * Muestra: nombre, tipo, precio base, duracion, estado activo/inactivo.
 * Acciones: editar, desactivar — solo para tenant_admin.
 */

import { Pencil, PowerOff, Power, MapPin } from 'lucide-react'
import { COURT_TYPE_LABELS } from '../types'
import type { Court } from '../types'

interface CourtCardProps {
  court: Court
  canEdit: boolean
  onEdit: (court: Court) => void
  onToggleActive: (court: Court) => void
  onViewDetail: (court: Court) => void
}

/** Formatea el precio base en formato argentino sin decimales si no aplica. */
function formatPrice(price: string): string {
  const num = parseFloat(price)
  if (isNaN(num)) return price
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(num)
}

export function CourtCard({
  court,
  canEdit,
  onEdit,
  onToggleActive,
  onViewDetail,
}: CourtCardProps) {
  return (
    <article
      className={[
        'bg-white dark:bg-gray-800 rounded-2xl border shadow-sm p-4',
        'transition-opacity',
        court.is_active ? 'border-gray-200 dark:border-gray-700' : 'border-gray-200 dark:border-gray-700 opacity-70',
      ].join(' ')}
      aria-label={`Cancha: ${court.name}`}
    >
      {/* Encabezado */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => onViewDetail(court)}
            className="text-left focus:outline-none focus:ring-2 focus:ring-brand-500 rounded"
          >
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-base leading-tight hover:text-brand-600 transition-colors">
              {court.name}
            </h3>
          </button>
          <div className="flex items-center gap-1.5 mt-1">
            <MapPin size={12} className="text-gray-400 shrink-0" aria-hidden="true" />
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {COURT_TYPE_LABELS[court.court_type]}
              {court.surface ? ` · ${court.surface}` : ''}
            </span>
          </div>
        </div>

        {/* Badge de estado */}
        <span
          aria-label={court.is_active ? 'Activa' : 'Inactiva'}
          className={[
            'shrink-0 inline-block px-2 py-0.5 rounded-full text-xs font-medium',
            court.is_active
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-500',
          ].join(' ')}
        >
          {court.is_active ? 'Activa' : 'Inactiva'}
        </span>
      </div>

      {/* Datos */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-2">
          <span className="block text-xs text-gray-400 mb-0.5">Precio base</span>
          <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {formatPrice(court.base_price)}
          </span>
        </div>
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-2">
          <span className="block text-xs text-gray-400 mb-0.5">Turno</span>
          <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {court.slot_duration_minutes} min
          </span>
        </div>
      </div>

      {/* Acciones — solo tenant_admin */}
      {canEdit && (
        <div className="flex gap-2 border-t border-gray-100 dark:border-gray-700 pt-3">
          <button
            type="button"
            aria-label={`Editar cancha ${court.name}`}
            onClick={() => onEdit(court)}
            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-brand-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <Pencil size={14} aria-hidden="true" />
            Editar
          </button>
          <div className="w-px bg-gray-100 dark:bg-gray-700" aria-hidden="true" />
          <button
            type="button"
            aria-label={
              court.is_active
                ? `Desactivar cancha ${court.name}`
                : `Activar cancha ${court.name}`
            }
            onClick={() => onToggleActive(court)}
            className={[
              'flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
              'focus:outline-none focus:ring-2',
              court.is_active
                ? 'text-gray-600 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 focus:ring-red-500'
                : 'text-gray-600 dark:text-gray-300 hover:bg-green-50 dark:hover:bg-green-900/20 hover:text-green-600 focus:ring-green-500',
            ].join(' ')}
          >
            {court.is_active ? (
              <>
                <PowerOff size={14} aria-hidden="true" />
                Desactivar
              </>
            ) : (
              <>
                <Power size={14} aria-hidden="true" />
                Activar
              </>
            )}
          </button>
        </div>
      )}
    </article>
  )
}
