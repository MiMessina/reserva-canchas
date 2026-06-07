/**
 * features/booking/pages/BookingsAdminPage.tsx
 * ----------------------------------------------
 * Panel de reservas para operator/admin. Ruta: /admin/bookings (requiere JWT).
 *
 * Funcionalidad:
 *  - Filtros: fecha (date_from/date_to), estado, cancha.
 *  - Lista paginada de reservas con acciones inline por estado.
 *  - PENDING_PAYMENT: "Confirmar" + "Cancelar".
 *  - CONFIRMED: "Cancelar" + "Completar" (si end_dt ya paso).
 *  - CANCELLED / COMPLETED: sin acciones.
 *  - Al cancelar: modal que pide motivo.
 *  - Mobile-first: cards apiladas en mobile, tabla en md+.
 */

import { useState } from 'react'
import {
  CheckCheck,
  X,
  Flag,
  Filter,
  ClipboardList,
  ChevronRight,
  User,
} from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { Button } from '@/components/Button'
import { Modal } from '@/components/Modal'
import { useCourts } from '@/features/courts/hooks/useCourts'
import {
  useBookings,
  useConfirmBooking,
  useCancelBooking,
  useCompleteBooking,
} from '../hooks/useBookings'
import { formatDateTimeBA, toLocalDateStringBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'
import {
  STATUS_LABELS,
  STATUS_BADGE_CLASSES,
  type Booking,
  type BookingStatus,
  type BookingsFilters,
} from '../types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function todayLocalDate(): string {
  return toLocalDateStringBA(new Date())
}

function isInPast(utcDateStr: string): boolean {
  return new Date(utcDateStr) < new Date()
}

function formatARS(value: string): string {
  const num = parseFloat(value)
  if (isNaN(num)) return value
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
  }).format(num)
}

// ─── Helper de contacto ───────────────────────────────────────────────────────

function contactLabel(booking: Booking): string {
  if (booking.guest_name) {
    return `Invitado: ${booking.guest_name}${booking.guest_phone ? ` · ${booking.guest_phone}` : ''}`
  }
  if (booking.user_email) {
    return `Usuario: ${booking.user_email}`
  }
  return '—'
}

// ─── Badge de estado ──────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: BookingStatus }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_BADGE_CLASSES[status],
      ].join(' ')}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}

// ─── Modal de cancelacion ─────────────────────────────────────────────────────

interface CancelModalProps {
  isOpen: boolean
  booking: Booking | null
  onClose: () => void
}

function CancelModal({ isOpen, booking, onClose }: CancelModalProps) {
  const [reason, setReason] = useState('')
  const [apiError, setApiError] = useState<string | null>(null)
  const cancelBooking = useCancelBooking()

  async function handleConfirm() {
    if (!booking) return
    setApiError(null)
    try {
      await cancelBooking.mutateAsync({
        id: booking.id,
        reason: reason.trim() || undefined,
      })
      setReason('')
      onClose()
    } catch (err) {
      setApiError(extractApiErrorMessage(err))
    }
  }

  function handleClose() {
    setReason('')
    setApiError(null)
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Cancelar reserva"
      size="sm"
    >
      <div className="space-y-4">
        {booking && (
          <p className="text-sm text-gray-600">
            Vas a cancelar la reserva de{' '}
            <span className="font-semibold">{booking.guest_name || 'un jugador'}</span>{' '}
            en <span className="font-semibold">{booking.court_name}</span>{' '}
            ({formatDateTimeBA(booking.start_dt)}).
          </p>
        )}

        <div className="space-y-1">
          <label
            htmlFor="cancel-reason"
            className="block text-sm font-medium text-gray-700"
          >
            Motivo (opcional)
          </label>
          <textarea
            id="cancel-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Ej: El jugador solicito la baja."
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
          />
        </div>

        {apiError && <ErrorState compact message={apiError} />}

        <div className="flex flex-col-reverse sm:flex-row gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            fullWidth
          >
            Volver
          </Button>
          <Button
            type="button"
            variant="danger"
            isLoading={cancelBooking.isPending}
            onClick={() => void handleConfirm()}
            fullWidth
          >
            Confirmar cancelacion
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ─── Card de reserva (mobile) ─────────────────────────────────────────────────

interface BookingCardProps {
  booking: Booking
  onConfirm: (booking: Booking) => void
  onCancel: (booking: Booking) => void
  onComplete: (booking: Booking) => void
  isConfirming: boolean
  isCompleting: boolean
}

function BookingCard({
  booking,
  onConfirm,
  onCancel,
  onComplete,
  isConfirming,
  isCompleting,
}: BookingCardProps) {
  const canComplete =
    booking.status === 'CONFIRMED' && isInPast(booking.end_dt)

  return (
    <li className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Encabezado */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-gray-900">{booking.court_name}</p>
          <p className="text-xs text-gray-500">
            {formatDateTimeBA(booking.start_dt)}
          </p>
        </div>
        <StatusBadge status={booking.status} />
      </div>

      {/* Detalle */}
      <div className="px-4 py-3 space-y-1 text-sm text-gray-600">
        <div className="flex items-center gap-1.5">
          <User size={13} className="text-gray-400 shrink-0" aria-hidden="true" />
          <span className="text-gray-500 truncate">{contactLabel(booking)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500">Precio</span>
          <span className="font-semibold text-gray-900">
            {formatARS(booking.price)}
          </span>
        </div>
        {booking.cancellation_reason && (
          <div className="flex items-start gap-1 pt-1">
            <span className="text-gray-400 text-xs mt-0.5">Motivo:</span>
            <span className="text-xs text-gray-500 italic">
              {booking.cancellation_reason}
            </span>
          </div>
        )}
      </div>

      {/* Acciones */}
      {(booking.status === 'PENDING_PAYMENT' || booking.status === 'CONFIRMED') && (
        <div className="px-4 pb-3 flex flex-wrap gap-2">
          {booking.status === 'PENDING_PAYMENT' && (
            <Button
              size="sm"
              variant="primary"
              isLoading={isConfirming}
              leftIcon={<CheckCheck size={14} />}
              onClick={() => onConfirm(booking)}
            >
              Confirmar
            </Button>
          )}
          {canComplete && (
            <Button
              size="sm"
              variant="secondary"
              isLoading={isCompleting}
              leftIcon={<Flag size={14} />}
              onClick={() => onComplete(booking)}
            >
              Completar
            </Button>
          )}
          <Button
            size="sm"
            variant="danger"
            leftIcon={<X size={14} />}
            onClick={() => onCancel(booking)}
          >
            Cancelar
          </Button>
        </div>
      )}
    </li>
  )
}

// ─── Fila de tabla (md+) ──────────────────────────────────────────────────────

interface BookingRowProps {
  booking: Booking
  onConfirm: (booking: Booking) => void
  onCancel: (booking: Booking) => void
  onComplete: (booking: Booking) => void
  isConfirming: boolean
  isCompleting: boolean
}

function BookingRow({
  booking,
  onConfirm,
  onCancel,
  onComplete,
  isConfirming,
  isCompleting,
}: BookingRowProps) {
  const canComplete =
    booking.status === 'CONFIRMED' && isInPast(booking.end_dt)

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 text-sm text-gray-900 font-medium">
        {booking.court_name}
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {formatDateTimeBA(booking.start_dt)}
      </td>
      <td className="px-4 py-3 text-sm text-gray-700">
        <div className="flex items-center gap-1.5">
          <User size={13} className="text-gray-400 shrink-0" aria-hidden="true" />
          <span className="truncate max-w-[180px]">{contactLabel(booking)}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={booking.status} />
      </td>
      <td className="px-4 py-3 text-sm font-semibold text-gray-900">
        {formatARS(booking.price)}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {booking.status === 'PENDING_PAYMENT' && (
            <button
              type="button"
              title="Confirmar reserva"
              aria-label="Confirmar reserva"
              disabled={isConfirming}
              onClick={() => onConfirm(booking)}
              className="inline-flex items-center gap-1 text-xs font-medium text-green-700 hover:text-green-900 disabled:opacity-40"
            >
              {isConfirming ? (
                <Spinner size="sm" color="gray" />
              ) : (
                <CheckCheck size={15} />
              )}
              <span>Confirmar</span>
            </button>
          )}
          {canComplete && (
            <button
              type="button"
              title="Completar reserva"
              aria-label="Completar reserva"
              disabled={isCompleting}
              onClick={() => onComplete(booking)}
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:text-brand-900 disabled:opacity-40"
            >
              {isCompleting ? (
                <Spinner size="sm" color="gray" />
              ) : (
                <Flag size={14} />
              )}
              <span>Completar</span>
            </button>
          )}
          {(booking.status === 'PENDING_PAYMENT' ||
            booking.status === 'CONFIRMED') && (
            <button
              type="button"
              title="Cancelar reserva"
              aria-label="Cancelar reserva"
              onClick={() => onCancel(booking)}
              className="inline-flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-800"
            >
              <X size={14} />
              <span>Cancelar</span>
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function BookingsAdminPage() {
  const today = todayLocalDate()

  const [filters, setFilters] = useState<BookingsFilters>({
    date_from: today,
    date_to: today,
  })
  const [bookingToCancel, setBookingToCancel] = useState<Booking | null>(null)
  const [confirmingId, setConfirmingId] = useState<number | null>(null)
  const [completingId, setCompletingId] = useState<number | null>(null)

  const { data: courtsData } = useCourts({ is_active: true })
  const courts = courtsData?.results ?? []

  const { data, isLoading, isError, error, refetch } = useBookings(filters)
  const bookings = data?.results ?? []

  const confirmBooking = useConfirmBooking()
  const completeBooking = useCompleteBooking()

  async function handleConfirm(booking: Booking) {
    setConfirmingId(booking.id)
    try {
      await confirmBooking.mutateAsync(booking.id)
    } finally {
      setConfirmingId(null)
    }
  }

  async function handleComplete(booking: Booking) {
    setCompletingId(booking.id)
    try {
      await completeBooking.mutateAsync(booking.id)
    } finally {
      setCompletingId(null)
    }
  }

  function updateFilter<K extends keyof BookingsFilters>(
    key: K,
    value: BookingsFilters[K],
  ) {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-2">
          <ClipboardList size={20} className="text-brand-600" aria-hidden="true" />
          <h1 className="text-base font-semibold text-gray-900">Reservas</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-5 space-y-5">
        {/* Panel de filtros */}
        <section
          aria-label="Filtros de reservas"
          className="bg-white rounded-xl border border-gray-200 px-4 py-4 space-y-4"
        >
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Filter size={15} aria-hidden="true" />
            <span>Filtrar</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {/* Fecha desde */}
            <div className="space-y-1">
              <label
                htmlFor="filter-date-from"
                className="block text-xs font-medium text-gray-600"
              >
                Desde
              </label>
              <input
                id="filter-date-from"
                type="date"
                value={filters.date_from ?? ''}
                onChange={(e) => updateFilter('date_from', e.target.value || undefined)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Fecha hasta */}
            <div className="space-y-1">
              <label
                htmlFor="filter-date-to"
                className="block text-xs font-medium text-gray-600"
              >
                Hasta
              </label>
              <input
                id="filter-date-to"
                type="date"
                value={filters.date_to ?? ''}
                onChange={(e) => updateFilter('date_to', e.target.value || undefined)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Estado */}
            <div className="space-y-1">
              <label
                htmlFor="filter-status"
                className="block text-xs font-medium text-gray-600"
              >
                Estado
              </label>
              <select
                id="filter-status"
                value={filters.status ?? ''}
                onChange={(e) =>
                  updateFilter(
                    'status',
                    (e.target.value as BookingStatus) || undefined,
                  )
                }
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Todos</option>
                {(Object.keys(STATUS_LABELS) as BookingStatus[]).map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
              </select>
            </div>

            {/* Cancha */}
            <div className="space-y-1">
              <label
                htmlFor="filter-court"
                className="block text-xs font-medium text-gray-600"
              >
                Cancha
              </label>
              <select
                id="filter-court"
                value={filters.court ?? ''}
                onChange={(e) =>
                  updateFilter(
                    'court',
                    e.target.value ? Number(e.target.value) : undefined,
                  )
                }
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Todas</option>
                {courts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {/* Contador */}
        {!isLoading && !isError && (
          <p className="text-sm text-gray-500">
            {data?.count ?? 0} reserva{(data?.count ?? 0) !== 1 ? 's' : ''}
          </p>
        )}

        {/* Estados de carga / error / vacio */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando reservas..." />
          </div>
        )}

        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {!isLoading && !isError && bookings.length === 0 && (
          <EmptyState
            icon={<ClipboardList size={48} strokeWidth={1.5} />}
            title="Sin reservas"
            description="No hay reservas para los filtros seleccionados."
          />
        )}

        {/* Lista mobile (< md): cards apiladas */}
        {!isLoading && !isError && bookings.length > 0 && (
          <>
            <ul className="space-y-3 md:hidden" aria-label="Lista de reservas">
              {bookings.map((booking) => (
                <BookingCard
                  key={booking.id}
                  booking={booking}
                  onConfirm={(b) => void handleConfirm(b)}
                  onCancel={setBookingToCancel}
                  onComplete={(b) => void handleComplete(b)}
                  isConfirming={confirmingId === booking.id}
                  isCompleting={completingId === booking.id}
                />
              ))}
            </ul>

            {/* Tabla desktop (>= md) */}
            <div className="hidden md:block overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">Cancha</th>
                    <th className="px-4 py-3">Fecha / Hora</th>
                    <th className="px-4 py-3">Jugador</th>
                    <th className="px-4 py-3">Estado</th>
                    <th className="px-4 py-3">Precio</th>
                    <th className="px-4 py-3">
                      <span className="sr-only">Acciones</span>
                      <ChevronRight size={14} aria-hidden="true" />
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {bookings.map((booking) => (
                    <BookingRow
                      key={booking.id}
                      booking={booking}
                      onConfirm={(b) => void handleConfirm(b)}
                      onCancel={setBookingToCancel}
                      onComplete={(b) => void handleComplete(b)}
                      isConfirming={confirmingId === booking.id}
                      isCompleting={completingId === booking.id}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>

      {/* Modal de cancelacion */}
      <CancelModal
        isOpen={bookingToCancel !== null}
        booking={bookingToCancel}
        onClose={() => setBookingToCancel(null)}
      />
    </div>
  )
}
