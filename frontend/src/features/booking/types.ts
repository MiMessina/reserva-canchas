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
  page?: number
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

// ─── Resumen de caja diaria ───────────────────────────────────────────────────

export interface CashDailySummary {
  date: string                // YYYY-MM-DD
  total: string               // decimal string; neto del día (puede ser negativo)
  ingresos: string            // suma de amounts > 0
  devoluciones: string        // suma de amounts < 0 (valor negativo o "0")
  movements_count: number
  ingresos_count: number
  devoluciones_count: number
}

// ─── Grilla multi-cancha ──────────────────────────────────────────────────────

export type SlotStatus = 'AVAILABLE' | 'PENDING_PAYMENT' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED'

export interface DailyGridSlot {
  start_dt: string        // ISO 8601 UTC
  end_dt: string          // ISO 8601 UTC
  status: SlotStatus
  booking_id: number | null
  guest_name: string | null
  price: string | null    // decimal string
}

export interface DailyGridCourt {
  id: number
  name: string
  type: string
  slot_duration_minutes: number
  slots: DailyGridSlot[]
}

export interface DailyGridResponse {
  date: string            // YYYY-MM-DD en hora BA
  courts: DailyGridCourt[]
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export interface BookingsTodaySummary {
  pending_payment: number
  confirmed: number
  completed: number
  cancelled: number
  total: number
}

export interface DashboardSummary {
  bookings_today: BookingsTodaySummary
  courts_total: number
  courts_occupied_now: number
  cashbox_today: CashDailySummary
}
