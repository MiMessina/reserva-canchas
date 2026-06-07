/**
 * features/booking/types.ts
 * --------------------------
 * Tipos del contrato de API para Reservas (Booking), Disponibilidad (Slot)
 * y Movimientos de Caja (CashMovement).
 * Mapean exactamente lo que devuelve el backend; no agregar campos que no existan.
 */

// ─── Booking ──────────────────────────────────────────────────────────────────

export type BookingStatus =
  | 'PENDING_PAYMENT'
  | 'CONFIRMED'
  | 'CANCELLED'
  | 'COMPLETED'

export const STATUS_LABELS: Record<BookingStatus, string> = {
  PENDING_PAYMENT: 'Pendiente de seña',
  CONFIRMED: 'Confirmada',
  CANCELLED: 'Cancelada',
  COMPLETED: 'Completada',
}

/** Colores de badge por estado. Clase Tailwind completa (bg + text). */
export const STATUS_BADGE_CLASSES: Record<BookingStatus, string> = {
  PENDING_PAYMENT: 'bg-yellow-100 text-yellow-800',
  CONFIRMED: 'bg-green-100 text-green-800',
  CANCELLED: 'bg-red-100 text-red-700',
  COMPLETED: 'bg-gray-100 text-gray-600',
}

export interface Booking {
  id: number
  court: number
  court_name: string
  // Campos solo en BookingStaffSerializer (admin/operator):
  user?: number | null
  user_email?: string | null
  guest_name?: string
  guest_phone?: string
  is_active?: boolean
  // Campos en ambos serializers:
  start_dt: string            // ISO 8601 UTC
  end_dt: string              // ISO 8601 UTC
  status: BookingStatus
  status_display: string      // texto legible del backend
  price: string               // decimal string, ej: "15000.00"
  cancellation_reason: string
  created_at: string          // ISO 8601 UTC
  updated_at: string          // ISO 8601 UTC
}

// ─── Payloads de mutación ─────────────────────────────────────────────────────

export interface CreateBookingPayload {
  court: number
  start_dt: string            // ISO 8601 UTC
  guest_name?: string
  guest_phone?: string
}

export interface CancelBookingPayload {
  reason?: string
}

// ─── Disponibilidad ───────────────────────────────────────────────────────────

export interface Slot {
  start_dt: string            // ISO 8601 UTC
  end_dt: string              // ISO 8601 UTC
  is_available: boolean
}

export interface AvailabilityResponse {
  date: string                // YYYY-MM-DD
  court: number
  slots: Slot[]
}

// ─── Filtros de query ─────────────────────────────────────────────────────────

export interface BookingsFilters {
  court?: number
  status?: BookingStatus
  date_from?: string          // YYYY-MM-DD
  date_to?: string            // YYYY-MM-DD
}

// ─── Caja diaria ─────────────────────────────────────────────────────────────

export interface CashMovement {
  id: number
  booking: number
  booking_court: string
  operator: number
  operator_email: string
  amount: string              // decimal string; negativo = cancelación/reversión
  notes: string
  created_at: string          // ISO 8601 UTC
}
