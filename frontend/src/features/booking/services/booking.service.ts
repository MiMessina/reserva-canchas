/**
 * features/booking/services/booking.service.ts
 * ---------------------------------------------
 * Llamadas a la API de Reservas y Caja diaria.
 * Usa el cliente axios central (lib/axios.ts).
 * No contiene logica de negocio: solo transporte HTTP.
 *
 * Endpoints:
 *   GET  /api/courts/{id}/availability/?date=YYYY-MM-DD  → AllowAny
 *   GET  /api/bookings/                                   → operator/admin (JWT)
 *   POST /api/bookings/                                   → AllowAny (guest) o JWT
 *   POST /api/bookings/{id}/confirm/                      → operator/admin (JWT)
 *   POST /api/bookings/{id}/cancel/                       → JWT
 *   POST /api/bookings/{id}/complete/                     → operator/admin (JWT)
 *   GET  /api/cash-movements/?date=YYYY-MM-DD             → operator/admin (JWT)
 *   GET  /api/cash-movements/summary/?date=YYYY-MM-DD    → operator/admin (JWT)
 */

import apiClient, { publicApiClient } from '@/lib/axios'
import type { PaginatedResponse } from '@/types/api'
import type {
  AvailabilityResponse,
  Booking,
  BookingsFilters,
  CancelBookingPayload,
  CashDailySummary,
  CashMovement,
  CreateBookingPayload,
} from '../types'

// ─── Disponibilidad ───────────────────────────────────────────────────────────

/**
 * Grilla de disponibilidad de una cancha para un dia dado.
 * Endpoint publico (AllowAny); no requiere JWT pero usa el mismo cliente
 * (el interceptor adjunta el token si existe, lo que no causa error).
 */
export async function getAvailability(
  courtId: number,
  date: string,          // YYYY-MM-DD
): Promise<AvailabilityResponse> {
  const { data } = await apiClient.get<AvailabilityResponse>(
    `/courts/${courtId}/availability/`,
    { params: { date } },
  )
  return data
}

// ─── Bookings ─────────────────────────────────────────────────────────────────

export async function getBookings(
  filters?: BookingsFilters,
): Promise<PaginatedResponse<Booking>> {
  const { data } = await apiClient.get<PaginatedResponse<Booking>>(
    '/bookings/',
    { params: filters },
  )
  return data
}

export async function createBooking(
  payload: CreateBookingPayload,
): Promise<Booking> {
  // publicApiClient: no adjunta JWT aunque el usuario esté logueado.
  // La grilla pública siempre crea reservas de invitado (ADR-008 XOR rule).
  const { data } = await publicApiClient.post<Booking>('/bookings/', payload)
  return data
}

export async function confirmBooking(id: number): Promise<Booking> {
  const { data } = await apiClient.post<Booking>(`/bookings/${id}/confirm/`)
  return data
}

export async function cancelBooking(
  id: number,
  reason?: string,
): Promise<Booking> {
  const payload: CancelBookingPayload = reason ? { reason } : {}
  const { data } = await apiClient.post<Booking>(
    `/bookings/${id}/cancel/`,
    payload,
  )
  return data
}

export async function completeBooking(id: number): Promise<Booking> {
  const { data } = await apiClient.post<Booking>(`/bookings/${id}/complete/`)
  return data
}

// ─── Caja diaria ─────────────────────────────────────────────────────────────

export async function getCashMovements(
  date?: string,         // YYYY-MM-DD; si no se pasa, el backend devuelve hoy
): Promise<PaginatedResponse<CashMovement>> {
  const { data } = await apiClient.get<PaginatedResponse<CashMovement>>(
    '/cash-movements/',
    { params: date ? { date } : undefined },
  )
  return data
}

export async function getCashMovementsSummary(
  date?: string,
): Promise<CashDailySummary> {
  const { data } = await apiClient.get<CashDailySummary>(
    '/cash-movements/summary/',
    { params: date ? { date } : undefined },
  )
  return data
}
