/**
 * features/booking/BookingDetailModal.tsx
 * ----------------------------------------
 * Modal que muestra el detalle completo de una reserva al hacer click en un
 * slot ocupado de la grilla multi-cancha (DailyGridPage).
 *
 * Props:
 *   - bookingId: number | null  — null = modal cerrado
 *   - onClose: () => void
 *
 * Fetch: GET /api/bookings/{bookingId}/ con React Query (operator/admin, JWT).
 * Query key: ['booking-detail', bookingId]
 *
 * Estados: loading · error · datos.
 * Sigue el patrón dark mode de los componentes existentes.
 */

import { useQuery } from '@tanstack/react-query'
import { User, Phone, MapPin, Clock, Banknote, FileText, Hash } from 'lucide-react'
import { Modal } from '@/components/Modal'
import { Spinner } from '@/components/Spinner'
import { getBookingDetail } from './services/booking.service'
import { formatTimeBA, formatDateBA } from '@/lib/datetime'
import { STATUS_LABELS, STATUS_BADGE_CLASSES } from './types'
import type { BookingStatus } from './types'

// ─── Props ────────────────────────────────────────────────────────────────────

interface BookingDetailModalProps {
  bookingId: number | null
  onClose: () => void
}

// ─── Sub-componentes internos ─────────────────────────────────────────────────

interface DetailRowProps {
  icon: React.ReactNode
  label: string
  value: React.ReactNode
}

function DetailRow({ icon, label, value }: DetailRowProps) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <span className="mt-0.5 shrink-0 text-gray-400 dark:text-gray-500">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">{label}</p>
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 break-words">
          {value}
        </p>
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function BookingDetailModal({ bookingId, onClose }: BookingDetailModalProps) {
  const isOpen = bookingId !== null

  const { data, isLoading, isError } = useQuery({
    queryKey: ['booking-detail', bookingId],
    queryFn: () => getBookingDetail(bookingId!),
    // Solo ejecutar cuando hay un bookingId válido
    enabled: bookingId !== null,
    // No refetch automático: los datos del modal son suficientemente estáticos
    staleTime: 30_000,
  })

  // ── Contenido del body del modal ───────────────────────────────────────────

  let body: React.ReactNode

  if (isLoading) {
    body = (
      <div className="flex flex-col items-center justify-center py-10 gap-3">
        <Spinner size="md" label="Cargando detalle..." />
        <p className="text-sm text-gray-500 dark:text-gray-400">Cargando detalle...</p>
      </div>
    )
  } else if (isError || !data) {
    body = (
      <div className="py-8 text-center space-y-2">
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          No se pudo cargar el detalle de la reserva.
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Intentalo de nuevo o cerrá el modal.
        </p>
      </div>
    )
  } else {
    const statusKey = data.status as BookingStatus
    const badgeClasses = STATUS_BADGE_CLASSES[statusKey] ?? 'bg-gray-100 text-gray-600'
    const statusLabel = STATUS_LABELS[statusKey] ?? data.status_display

    // Formatear horario en hora BA
    const fechaLabel = formatDateBA(data.start_dt)
    const horaInicio = formatTimeBA(data.start_dt)
    const horaFin = formatTimeBA(data.end_dt)
    const horarioLabel = `${horaInicio} – ${horaFin}`

    body = (
      <div className="space-y-1">
        {/* Badge de estado */}
        <div className="mb-4">
          <span
            className={[
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold',
              badgeClasses,
            ].join(' ')}
          >
            {statusLabel}
          </span>
        </div>

        {/* Filas de detalle */}
        <DetailRow
          icon={<Hash size={15} />}
          label="N.° de reserva"
          value={`#${data.id}`}
        />
        <DetailRow
          icon={<User size={15} />}
          label="Jugador / Invitado"
          value={data.guest_name ?? <span className="italic text-gray-400">Sin nombre registrado</span>}
        />
        {data.guest_phone && (
          <DetailRow
            icon={<Phone size={15} />}
            label="Teléfono"
            value={data.guest_phone}
          />
        )}
        <DetailRow
          icon={<MapPin size={15} />}
          label="Cancha"
          value={data.court_name}
        />
        <DetailRow
          icon={<Clock size={15} />}
          label="Fecha y horario"
          value={
            <>
              <span className="capitalize">{fechaLabel}</span>
              <br />
              <span className="text-gray-600 dark:text-gray-300">{horarioLabel}</span>
            </>
          }
        />
        <DetailRow
          icon={<Banknote size={15} />}
          label="Precio"
          value={
            new Intl.NumberFormat('es-AR', {
              style: 'currency',
              currency: 'ARS',
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            }).format(Number(data.price))
          }
        />
        {data.notes && (
          <DetailRow
            icon={<FileText size={15} />}
            label="Notas"
            value={data.notes}
          />
        )}
      </div>
    )
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Detalle de la reserva"
      size="sm"
    >
      {body}
    </Modal>
  )
}
