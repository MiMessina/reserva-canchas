/**
 * features/myBookings/MyBookingsPage.tsx
 * ----------------------------------------
 * Página pública "Mis Reservas". Ruta: /mis-reservas (sin autenticación).
 *
 * El jugador ingresa su número de teléfono y ve las reservas activas
 * asociadas. Puede cancelar las que estén en PENDING_PAYMENT.
 *
 * Endpoints:
 *   GET  /api/bookings/guest-lookup/?phone=... (sin JWT)
 *   POST /api/bookings/{id}/cancel-guest/      (sin JWT)
 *
 * UX:
 *   - Formulario de búsqueda por teléfono
 *   - Loading / empty / error states
 *   - Badge de estado (mismo sistema que BookingsAdminPage)
 *   - Cancelación con feedback de éxito y errores 403/409
 *   - Link de retorno a la grilla de reservas
 *   - Mobile-first, dark mode completo
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Phone, CalendarX, CheckCircle2, AlertTriangle, Search, MapPin, Clock, ArrowLeft } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { Button } from '@/components/Button'
import { formatDateBA, formatTimeBA } from '@/lib/datetime'
import { formatCurrency } from '@/lib/formatters'
import { extractApiErrorMessage } from '@/lib/apiError'
import { lookupBookingsByPhone, cancelBookingAsGuest } from '@/services/myBookingsService'
import type { GuestBooking } from '@/types/myBookings'

// ─── Badge de estado ──────────────────────────────────────────────────────────

const STATUS_BADGE: Record<GuestBooking['status'], string> = {
  PENDING_PAYMENT: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  CONFIRMED: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
}

// ─── Tarjeta de reserva ───────────────────────────────────────────────────────

interface BookingCardProps {
  booking: GuestBooking
  phone: string
  onCancelled: () => void
}

function BookingCard({ booking, phone, onCancelled }: BookingCardProps) {
  const [cancelSuccess, setCancelSuccess] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const cancelMutation = useMutation({
    mutationFn: () => cancelBookingAsGuest(booking.id, phone),
    onSuccess: () => {
      setCancelError(null)
      setCancelSuccess(true)
      void queryClient.invalidateQueries({ queryKey: ['guest-bookings', phone] })
      onCancelled()
    },
    onError: (err) => {
      // Mapeamos errores específicos de cancelación como invitado
      const axiosErr = err as { response?: { status: number } }
      const status = axiosErr?.response?.status
      if (status === 403) {
        setCancelError('No se pudo cancelar. El número no coincide con el de la reserva.')
      } else if (status === 409) {
        setCancelError('Esta reserva ya no puede cancelarse.')
      } else {
        setCancelError(extractApiErrorMessage(err))
      }
    },
  })

  const canCancel = booking.status === 'PENDING_PAYMENT'
  const fechaLabel = formatDateBA(booking.start_dt)
  const horaInicio = formatTimeBA(booking.start_dt)
  const horaFin = formatTimeBA(booking.end_dt)

  if (cancelSuccess) {
    return (
      <div className="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 px-4 py-4 flex items-center gap-3">
        <CheckCircle2 size={20} className="text-green-500 shrink-0" aria-hidden="true" />
        <p className="text-sm font-medium text-green-800 dark:text-green-400">
          Reserva #{booking.id} cancelada correctamente.
        </p>
      </div>
    )
  }

  return (
    <article className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
      {/* Header de la card */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
          Reserva #{booking.id}
        </span>
        <span
          className={[
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold',
            STATUS_BADGE[booking.status],
          ].join(' ')}
        >
          {booking.status_display}
        </span>
      </div>

      {/* Cuerpo de la card */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <MapPin size={14} className="shrink-0 text-gray-400 dark:text-gray-500" aria-hidden="true" />
          <span className="font-medium">{booking.court_name}</span>
        </div>
        <div className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
          <Clock size={14} className="shrink-0 mt-0.5 text-gray-400 dark:text-gray-500" aria-hidden="true" />
          <div>
            <span className="capitalize">{fechaLabel}</span>
            <br />
            <span className="text-xs text-gray-500 dark:text-gray-500">
              {horaInicio} – {horaFin}
            </span>
          </div>
        </div>
        <div className="text-sm font-semibold text-brand-700 dark:text-brand-400">
          {formatCurrency(booking.price)}
        </div>
      </div>

      {/* Error de cancelación */}
      {cancelError && (
        <div
          role="alert"
          className="mx-4 mb-3 flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2"
        >
          <AlertTriangle size={14} className="text-red-500 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-xs text-red-700 dark:text-red-400">{cancelError}</p>
        </div>
      )}

      {/* Acción de cancelar */}
      {canCancel && (
        <div className="px-4 pb-4">
          <Button
            variant="danger"
            size="sm"
            fullWidth
            isLoading={cancelMutation.isPending}
            onClick={() => {
              setCancelError(null)
              cancelMutation.mutate()
            }}
          >
            Cancelar reserva
          </Button>
        </div>
      )}
    </article>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function MyBookingsPage() {
  const [phoneInput, setPhoneInput] = useState('')
  const [submittedPhone, setSubmittedPhone] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  const {
    data: bookings,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['guest-bookings', submittedPhone],
    queryFn: () => lookupBookingsByPhone(submittedPhone),
    enabled: submittedPhone.length > 0,
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = phoneInput.trim()
    if (!trimmed) return
    setSubmittedPhone(trimmed)
    setHasSearched(true)
  }

  const showResults = hasSearched && submittedPhone.length > 0

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-4">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center shrink-0">
              <span className="text-white font-bold text-sm" aria-hidden="true">C</span>
            </div>
            <div>
              <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100 leading-tight">
                Mis reservas
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Consultá y gestioná tus turnos
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-5 space-y-5">
        {/* Link de volver a la grilla */}
        <Link
          to="/booking"
          className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 hover:underline"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Volver a la grilla de turnos
        </Link>

        {/* Formulario de búsqueda */}
        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          <div className="space-y-1.5">
            <label
              htmlFor="phone-lookup"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200"
            >
              Tu número de teléfono
            </label>
            <div className="relative">
              <Phone
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                aria-hidden="true"
              />
              <input
                id="phone-lookup"
                type="tel"
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                placeholder="Ej: 1123456789"
                autoComplete="tel"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 pl-9 pr-3 py-2.5 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
              />
            </div>
          </div>
          <Button
            type="submit"
            variant="primary"
            fullWidth
            leftIcon={<Search size={15} />}
            disabled={phoneInput.trim().length === 0}
          >
            Buscar mis turnos
          </Button>
        </form>

        {/* Resultados */}
        {showResults && (
          <section aria-label="Tus reservas" className="space-y-3">
            {isLoading && (
              <div className="flex justify-center py-10">
                <Spinner size="lg" label="Buscando reservas..." />
              </div>
            )}

            {isError && !isLoading && (
              <div className="flex flex-col items-center gap-4 py-8 text-center">
                <AlertTriangle size={40} className="text-red-300" aria-hidden="true" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    Hubo un problema. Intentalo de nuevo.
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Verificá tu conexión y volvé a buscar.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => void refetch()}
                >
                  Reintentar
                </Button>
              </div>
            )}

            {!isLoading && !isError && bookings !== undefined && bookings.length === 0 && (
              <div className="flex flex-col items-center gap-3 py-10 text-center">
                <CalendarX
                  size={48}
                  strokeWidth={1.5}
                  className="text-gray-300 dark:text-gray-600"
                  aria-hidden="true"
                />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                    No encontramos reservas activas
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    No hay reservas pendientes o confirmadas para el número{' '}
                    <strong>{submittedPhone}</strong>.
                  </p>
                </div>
              </div>
            )}

            {!isLoading && !isError && bookings && bookings.length > 0 && (
              <>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {bookings.length === 1
                    ? '1 reserva activa encontrada'
                    : `${bookings.length} reservas activas encontradas`}
                </p>
                <ul className="space-y-3" aria-label="Lista de reservas">
                  {bookings.map((booking) => (
                    <li key={booking.id}>
                      <BookingCard
                        booking={booking}
                        phone={submittedPhone}
                        onCancelled={() => void refetch()}
                      />
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}
      </main>
    </div>
  )
}
