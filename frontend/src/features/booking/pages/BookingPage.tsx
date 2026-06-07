/**
 * features/booking/pages/BookingPage.tsx
 * ----------------------------------------
 * Grilla publica de turnos. Ruta: /booking (sin autenticacion requerida).
 *
 * Flujo:
 *  1. El jugador selecciona una cancha y una fecha.
 *  2. Se muestra la grilla de slots del dia: disponibles (verde) u ocupados (gris).
 *  3. Al tocar "Reservar" en un slot disponible, se abre el modal con el formulario.
 *  4. El jugador ingresa nombre y telefono y confirma.
 *  5. POST /api/bookings/ → exito: mensaje de confirmacion + refresco de grilla.
 *  6. Error: se muestra el mensaje del backend (incluido SLOT_ALREADY_BOOKED).
 *
 * Horas: siempre en America/Argentina/Buenos_Aires (via lib/datetime.ts).
 * Precios: formato ARS con Intl.NumberFormat.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { CalendarDays, Clock, MapPin, CheckCircle2 } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { Button } from '@/components/Button'
import { Modal } from '@/components/Modal'
import { useCourts } from '@/features/courts/hooks/useCourts'
import { useAvailability, useCreateBooking } from '../hooks/useBookings'
import { formatTimeBA, toLocalDateStringBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { Slot } from '../types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function todayLocalDate(): string {
  return toLocalDateStringBA(new Date())
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

// ─── Schema de formulario de reserva ─────────────────────────────────────────

const bookingSchema = z.object({
  guest_name: z
    .string()
    .min(2, 'El nombre debe tener al menos 2 caracteres.')
    .max(100, 'El nombre es demasiado largo.'),
  guest_phone: z
    .string()
    .min(7, 'Ingresa un telefono valido.')
    .max(30, 'El telefono es demasiado largo.'),
})

type BookingFormValues = z.infer<typeof bookingSchema>

// ─── Componente de fila de slot ───────────────────────────────────────────────

interface SlotRowProps {
  slot: Slot
  price: string
  onReserve: (slot: Slot) => void
}

function SlotRow({ slot, price, onReserve }: SlotRowProps) {
  const timeRange = `${formatTimeBA(slot.start_dt)} – ${formatTimeBA(slot.end_dt)}`

  if (!slot.is_available) {
    return (
      <li className="flex items-center justify-between py-3 px-4 rounded-xl bg-gray-50 border border-gray-100">
        <div className="flex items-center gap-2 text-gray-400">
          <Clock size={15} aria-hidden="true" />
          <span className="text-sm font-medium">{timeRange}</span>
        </div>
        <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2.5 py-1 rounded-full">
          Ocupado
        </span>
      </li>
    )
  }

  return (
    <li className="flex items-center justify-between py-3 px-4 rounded-xl bg-green-50 border border-green-200">
      <div className="flex items-center gap-2 text-green-700">
        <Clock size={15} aria-hidden="true" />
        <span className="text-sm font-semibold">{timeRange}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-green-800">
          {formatARS(price)}
        </span>
        <Button
          size="sm"
          variant="primary"
          onClick={() => onReserve(slot)}
          className="bg-green-600 hover:bg-green-700 focus:ring-green-500"
        >
          Reservar
        </Button>
      </div>
    </li>
  )
}

// ─── Modal de formulario de reserva ──────────────────────────────────────────

interface BookingModalProps {
  isOpen: boolean
  onClose: () => void
  slot: Slot | null
  courtId: number
  courtName: string
  price: string
}

interface BookingSuccess {
  bookingId: number
  timeRange: string
}

function BookingModal({
  isOpen,
  onClose,
  slot,
  courtId,
  courtName,
  price,
}: BookingModalProps) {
  const [successData, setSuccessData] = useState<BookingSuccess | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const createBooking = useCreateBooking()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<BookingFormValues>({
    resolver: zodResolver(bookingSchema),
  })

  function handleClose() {
    reset()
    setSuccessData(null)
    setApiError(null)
    onClose()
  }

  async function onSubmit(values: BookingFormValues) {
    if (!slot) return
    setApiError(null)
    try {
      const created = await createBooking.mutateAsync({
        court: courtId,
        start_dt: slot.start_dt,
        guest_name: values.guest_name,
        guest_phone: values.guest_phone,
      })
      setSuccessData({
        bookingId: created.id,
        timeRange: `${formatTimeBA(slot.start_dt)} – ${formatTimeBA(slot.end_dt)}`,
      })
      reset()
    } catch (err) {
      setApiError(extractApiErrorMessage(err))
    }
  }

  if (!slot) return null

  const timeRange = `${formatTimeBA(slot.start_dt)} – ${formatTimeBA(slot.end_dt)}`

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Confirmar reserva" size="md">
      {successData ? (
        <div className="flex flex-col items-center py-4 text-center gap-4">
          <CheckCircle2 size={48} className="text-green-500" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-base font-semibold text-gray-900">Reserva confirmada</p>
            <p className="text-sm text-gray-600">
              Turno: {courtName} · {successData.timeRange}
            </p>
            <p className="text-sm font-medium text-brand-700">
              Número de reserva: #{successData.bookingId}
            </p>
          </div>
          <p className="text-sm text-gray-500 leading-relaxed">
            Presentate en recepcion para confirmar la seña.
          </p>
          <Button variant="primary" onClick={handleClose} fullWidth>
            Cerrar
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          {/* Resumen del turno */}
          <div className="rounded-xl bg-gray-50 border border-gray-100 px-4 py-3 space-y-1.5 text-sm">
            <div className="flex items-center gap-2 text-gray-600">
              <MapPin size={14} aria-hidden="true" />
              <span className="font-medium">{courtName}</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600">
              <Clock size={14} aria-hidden="true" />
              <span>{timeRange}</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600">
              <span className="font-semibold text-brand-700">{formatARS(price)}</span>
            </div>
          </div>

          {/* Error de API */}
          {apiError && (
            <ErrorState compact message={apiError} />
          )}

          {/* Campo: Nombre */}
          <div className="space-y-1">
            <label
              htmlFor="guest_name"
              className="block text-sm font-medium text-gray-700"
            >
              Nombre completo <span aria-hidden="true" className="text-red-500">*</span>
            </label>
            <input
              id="guest_name"
              type="text"
              autoComplete="name"
              placeholder="Tu nombre"
              {...register('guest_name')}
              className={[
                'w-full rounded-lg border px-3 py-2.5 text-sm outline-none',
                'focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
                'transition-colors placeholder:text-gray-400',
                errors.guest_name
                  ? 'border-red-400 bg-red-50'
                  : 'border-gray-300 bg-white',
              ].join(' ')}
            />
            {errors.guest_name && (
              <p role="alert" className="text-xs text-red-600">
                {errors.guest_name.message}
              </p>
            )}
          </div>

          {/* Campo: Telefono */}
          <div className="space-y-1">
            <label
              htmlFor="guest_phone"
              className="block text-sm font-medium text-gray-700"
            >
              Telefono <span aria-hidden="true" className="text-red-500">*</span>
            </label>
            <input
              id="guest_phone"
              type="tel"
              autoComplete="tel"
              placeholder="Ej: 1123456789"
              {...register('guest_phone')}
              className={[
                'w-full rounded-lg border px-3 py-2.5 text-sm outline-none',
                'focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
                'transition-colors placeholder:text-gray-400',
                errors.guest_phone
                  ? 'border-red-400 bg-red-50'
                  : 'border-gray-300 bg-white',
              ].join(' ')}
            />
            {errors.guest_phone && (
              <p role="alert" className="text-xs text-red-600">
                {errors.guest_phone.message}
              </p>
            )}
          </div>

          {/* Acciones */}
          <div className="flex flex-col-reverse sm:flex-row gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              onClick={handleClose}
              fullWidth
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={createBooking.isPending}
              fullWidth
            >
              Confirmar reserva
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function BookingPage() {
  const [selectedCourtId, setSelectedCourtId] = useState<number>(0)
  const [selectedDate, setSelectedDate] = useState<string>(todayLocalDate())
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const { data: courtsData, isLoading: courtsLoading } = useCourts({
    is_active: true,
  })
  const courts = courtsData?.results ?? []

  // Seleccionar la primera cancha automaticamente cuando carguen los datos.
  const effectiveCourtId =
    selectedCourtId > 0
      ? selectedCourtId
      : (courts[0]?.id ?? 0)

  const selectedCourt = courts.find((c) => c.id === effectiveCourtId)

  const {
    data: availabilityData,
    isLoading: slotsLoading,
    isError: slotsError,
    error: slotsErrorObj,
    refetch: refetchSlots,
  } = useAvailability(effectiveCourtId, selectedDate)

  const slots = availabilityData?.slots ?? []

  function handleSlotReserve(slot: Slot) {
    setSelectedSlot(slot)
    setModalOpen(true)
  }

  function handleModalClose() {
    setModalOpen(false)
    setSelectedSlot(null)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-sm" aria-hidden="true">
              C
            </span>
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900 leading-tight">
              Reserva tu turno
            </h1>
            <p className="text-xs text-gray-500">Elegí cancha, dia y horario</p>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-5 space-y-5">
        {/* Selector de cancha */}
        <div className="space-y-1.5">
          <label
            htmlFor="court-select"
            className="block text-sm font-medium text-gray-700"
          >
            Cancha
          </label>
          {courtsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Spinner size="sm" />
              <span>Cargando canchas...</span>
            </div>
          ) : courts.length === 0 ? (
            <p className="text-sm text-gray-500">
              No hay canchas disponibles en este momento.
            </p>
          ) : (
            <select
              id="court-select"
              value={effectiveCourtId}
              onChange={(e) => setSelectedCourtId(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            >
              {courts.map((court) => (
                <option key={court.id} value={court.id}>
                  {court.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Selector de fecha */}
        <div className="space-y-1.5">
          <label
            htmlFor="date-select"
            className="block text-sm font-medium text-gray-700"
          >
            Fecha
          </label>
          <div className="relative">
            <CalendarDays
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
              aria-hidden="true"
            />
            <input
              id="date-select"
              type="date"
              value={selectedDate}
              min={todayLocalDate()}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>
        </div>

        {/* Grilla de slots */}
        <section aria-label="Disponibilidad de turnos">
          {slotsLoading && effectiveCourtId > 0 && (
            <div className="flex justify-center py-12">
              <Spinner size="lg" label="Cargando turnos..." />
            </div>
          )}

          {slotsError && !slotsLoading && (
            <ErrorState
              message={extractApiErrorMessage(slotsErrorObj)}
              onRetry={() => void refetchSlots()}
              retryLabel="Reintentar"
            />
          )}

          {!slotsLoading && !slotsError && effectiveCourtId > 0 && slots.length === 0 && (
            <EmptyState
              icon={<CalendarDays size={48} strokeWidth={1.5} />}
              title="Sin turnos disponibles"
              description="No hay turnos habilitados para este dia. Proba con otra fecha."
            />
          )}

          {!slotsLoading && !slotsError && slots.length > 0 && (
            <ul className="space-y-2" aria-label="Turnos del dia">
              {slots.map((slot) => (
                <SlotRow
                  key={slot.start_dt}
                  slot={slot}
                  price={selectedCourt?.base_price ?? '0'}
                  onReserve={handleSlotReserve}
                />
              ))}
            </ul>
          )}
        </section>
      </main>

      {/* Modal de reserva */}
      <BookingModal
        isOpen={modalOpen}
        onClose={handleModalClose}
        slot={selectedSlot}
        courtId={effectiveCourtId}
        courtName={selectedCourt?.name ?? ''}
        price={selectedCourt?.base_price ?? '0'}
      />
    </div>
  )
}
