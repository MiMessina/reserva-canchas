/**
 * features/booking/pages/DailyGridPage.tsx
 * ------------------------------------------
 * Grilla multi-cancha del dia para operator/admin. Ruta: /admin/grid (requiere JWT).
 *
 * Funcionalidad:
 *  - Selector de fecha (default hoy en hora BA).
 *  - Tabla con scroll horizontal: primera columna "Horario", luego una columna
 *    por cada cancha del complejo.
 *  - Cada celda muestra el estado del slot con color semanfico:
 *      AVAILABLE       → blanco / gris claro "Libre"
 *      PENDING_PAYMENT → amarillo / nombre del invitado
 *      CONFIRMED       → azul / nombre del invitado
 *      COMPLETED       → gris / "Jugado"
 *      CANCELLED       → no deberia aparecer (vuelve a AVAILABLE en el backend)
 *  - Los horarios se convierten de UTC a hora BA usando formatTimeBA (lib/datetime).
 *  - Estados loading / empty / error.
 */

import { useState } from 'react'
import { TableProperties, CalendarDays } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { BookingDetailModal } from '../BookingDetailModal'
import { useDailyGrid } from '../hooks/useBookings'
import { formatTimeBA, toLocalDateStringBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { DailyGridSlot, SlotStatus } from '../types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function todayLocalDate(): string {
  return toLocalDateStringBA(new Date())
}

/** Clases de celda segun el estado del slot. */
function slotCellClasses(status: SlotStatus): string {
  switch (status) {
    case 'AVAILABLE':
      return 'bg-white text-gray-400'
    case 'PENDING_PAYMENT':
      return 'bg-yellow-50 text-yellow-700'
    case 'CONFIRMED':
      return 'bg-blue-50 text-blue-700'
    case 'COMPLETED':
      return 'bg-gray-100 text-gray-500'
    case 'CANCELLED':
      return 'bg-white text-gray-300 line-through'
    default:
      return 'bg-white text-gray-400'
  }
}

/** Texto que se muestra dentro de la celda del slot. */
function slotLabel(slot: DailyGridSlot): string {
  switch (slot.status) {
    case 'AVAILABLE':
      return 'Libre'
    case 'PENDING_PAYMENT':
    case 'CONFIRMED':
      return slot.guest_name ?? 'Invitado'
    case 'COMPLETED':
      return slot.guest_name ?? 'Jugado'
    case 'CANCELLED':
      return 'Cancelado'
    default:
      return '—'
  }
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function DailyGridPage() {
  const [selectedDate, setSelectedDate] = useState<string>(todayLocalDate())
  const [selectedBookingId, setSelectedBookingId] = useState<number | null>(null)

  const { data, isLoading, isError, error, refetch } = useDailyGrid(selectedDate)

  const courts = data?.courts ?? []

  // Construir la lista de horarios unicos ordenados a partir de todos los slots
  // de todas las canchas. Usamos start_dt (UTC) como clave; la conversion a
  // hora BA se hace al renderizar con formatTimeBA.
  const uniqueTimes = Array.from(
    new Set(
      courts.flatMap((court) => court.slots.map((slot) => slot.start_dt)),
    ),
  ).sort()

  /**
   * Dado un court y un start_dt, devuelve el slot correspondiente o null.
   * Comparamos start_dt exacto (ambos son strings ISO 8601 UTC).
   */
  function findSlot(courtId: number, startDt: string): DailyGridSlot | null {
    const court = courts.find((c) => c.id === courtId)
    if (!court) return null
    return court.slots.find((s) => s.start_dt === startDt) ?? null
  }

  const hasData = courts.length > 0 && uniqueTimes.length > 0

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center gap-2 flex-wrap">
          <TableProperties size={20} className="text-brand-600" aria-hidden="true" />
          <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">Grilla del dia</h1>

          {/* Selector de fecha */}
          <div className="ml-auto flex items-center gap-2">
            <CalendarDays
              size={15}
              className="text-gray-400"
              aria-hidden="true"
            />
            <input
              id="grid-date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              aria-label="Seleccionar fecha"
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-5">
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando grilla..." />
          </div>
        )}

        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {!isLoading && !isError && !hasData && (
          <EmptyState
            icon={<TableProperties size={48} strokeWidth={1.5} />}
            title="Sin datos para este dia"
            description="No hay canchas con turnos configurados para la fecha seleccionada."
          />
        )}

        {!isLoading && !isError && hasData && (
          <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                  {/* Columna de horarios — sticky */}
                  <th
                    scope="col"
                    className="sticky left-0 z-10 bg-gray-50 dark:bg-gray-900 px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide border-r border-gray-100 dark:border-gray-700 min-w-[80px]"
                  >
                    Horario
                  </th>
                  {courts.map((court) => (
                    <th
                      key={court.id}
                      scope="col"
                      className="px-4 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide min-w-[130px]"
                    >
                      <span className="block">{court.name}</span>
                      <span className="block font-normal text-gray-400 dark:text-gray-500 normal-case">
                        {court.type}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {uniqueTimes.map((startDt) => (
                  <tr key={startDt} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/50 transition-colors">
                    {/* Celda de horario — sticky */}
                    <td
                      className="sticky left-0 z-10 bg-white dark:bg-gray-800 px-4 py-2.5 text-xs font-semibold text-gray-600 dark:text-gray-400 border-r border-gray-100 dark:border-gray-700 whitespace-nowrap"
                    >
                      {formatTimeBA(startDt)}
                    </td>
                    {/* Celdas de cada cancha */}
                    {courts.map((court) => {
                      const slot = findSlot(court.id, startDt)
                      if (!slot) {
                        return (
                          <td
                            key={court.id}
                            className="px-3 py-2 text-center text-xs text-gray-300"
                          >
                            —
                          </td>
                        )
                      }

                      const isClickable = slot.booking_id !== null
                      return (
                        <td
                          key={court.id}
                          className={[
                            'px-3 py-2 text-center text-xs font-medium rounded-sm transition-colors',
                            slotCellClasses(slot.status),
                            isClickable ? 'cursor-pointer hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-500' : '',
                          ].join(' ')}
                          onClick={isClickable ? () => setSelectedBookingId(slot.booking_id) : undefined}
                          role={isClickable ? 'button' : undefined}
                          tabIndex={isClickable ? 0 : undefined}
                          onKeyDown={
                            isClickable
                              ? (e) => {
                                  if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault()
                                    setSelectedBookingId(slot.booking_id)
                                  }
                                }
                              : undefined
                          }
                          aria-label={
                            isClickable
                              ? `Ver detalle de reserva de ${slot.guest_name ?? 'invitado'} a las ${formatTimeBA(slot.start_dt)}`
                              : undefined
                          }
                        >
                          {slotLabel(slot)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Modal de detalle de reserva */}
      <BookingDetailModal
        bookingId={selectedBookingId}
        onClose={() => setSelectedBookingId(null)}
      />
    </div>
  )
}
