/**
 * features/booking/hooks/useBookings.ts
 * ---------------------------------------
 * Hooks de React Query para Reservas, Disponibilidad y Caja diaria.
 *
 * Query keys (consistentes por dominio, siguiendo API_GUIDELINES.md):
 *   ["availability", courtId, date]  → grilla de slots de una cancha
 *   ["bookings", filters]             → lista paginada de reservas
 *   ["cash-movements", date]          → movimientos de caja del dia
 *
 * Invalidacion de cache tras cada mutacion:
 *   - createBooking  → invalida ["bookings"] y ["availability", courtId, date]
 *   - confirmBooking → invalida ["bookings"] y ["cash-movements"]
 *   - cancelBooking  → invalida ["bookings"] y ["availability", courtId, date]
 *   - completeBooking → invalida ["bookings"]
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query'
import {
  getAvailability,
  getBookings,
  createBooking,
  confirmBooking,
  cancelBooking,
  completeBooking,
  getCashMovements,
  getCashMovementsSummary,
  getDailyGrid,
  getDashboardSummary,
} from '../services/booking.service'
import type {
  AvailabilityResponse,
  Booking,
  BookingsFilters,
  CashDailySummary,
  CashMovement,
  CreateBookingPayload,
  DailyGridResponse,
  DashboardSummary,
} from '../types'
import type { PaginatedResponse } from '@/types/api'

// ─── Query keys ──────────────────────────────────────────────────────────────

export const bookingKeys = {
  all: ['bookings'] as const,
  list: (filters?: BookingsFilters) => ['bookings', 'list', filters] as const,
}

export const availabilityKeys = {
  all: ['availability'] as const,
  slot: (courtId: number, date: string) =>
    ['availability', courtId, date] as const,
}

export const cashMovementKeys = {
  all: ['cash-movements'] as const,
  byDate: (date?: string) => ['cash-movements', date ?? 'today'] as const,
  summary: (date?: string) => ['cash-movements', 'summary', date ?? 'today'] as const,
}

// ─── Disponibilidad — Query ───────────────────────────────────────────────────

export function useAvailability(
  courtId: number,
  date: string,         // YYYY-MM-DD
): UseQueryResult<AvailabilityResponse> {
  return useQuery({
    queryKey: availabilityKeys.slot(courtId, date),
    queryFn: () => getAvailability(courtId, date),
    // Solo ejecutar si hay cancha y fecha validas.
    enabled: courtId > 0 && date.length === 10,
  })
}

// ─── Bookings — Queries ───────────────────────────────────────────────────────

export function useBookings(
  filters?: BookingsFilters,
): UseQueryResult<PaginatedResponse<Booking>> {
  return useQuery({
    queryKey: bookingKeys.list(filters),
    queryFn: () => getBookings(filters),
  })
}

// ─── Bookings — Mutations ─────────────────────────────────────────────────────

/**
 * Crear reserva (guest o autenticado).
 * Invalida la grilla de disponibilidad de la cancha/dia afectados y la lista de reservas.
 */
export function useCreateBooking(): UseMutationResult<
  Booking,
  Error,
  CreateBookingPayload
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createBooking,
    onSuccess: () => {
      // Invalida la disponibilidad de esa cancha (cualquier fecha)
      void queryClient.invalidateQueries({
        queryKey: availabilityKeys.all,
      })
      // Invalida la lista de reservas
      void queryClient.invalidateQueries({ queryKey: bookingKeys.all })
    },
  })
}

/**
 * Confirmar reserva (operator/admin).
 * Genera un CashMovement en el backend: invalida tambien la caja.
 */
export function useConfirmBooking(): UseMutationResult<Booking, Error, number> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: confirmBooking,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: bookingKeys.all })
      void queryClient.invalidateQueries({ queryKey: cashMovementKeys.all })
    },
  })
}

/**
 * Cancelar reserva (jugador solo la propia; operator/admin cualquiera).
 * Invalida disponibilidad (el slot queda libre) y lista de reservas.
 */
export function useCancelBooking(): UseMutationResult<
  Booking,
  Error,
  { id: number; reason?: string }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }) => cancelBooking(id, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: bookingKeys.all })
      void queryClient.invalidateQueries({ queryKey: availabilityKeys.all })
      void queryClient.invalidateQueries({ queryKey: cashMovementKeys.all })
    },
  })
}

/**
 * Completar reserva (operator/admin; solo si end_dt ya paso).
 */
export function useCompleteBooking(): UseMutationResult<Booking, Error, number> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: completeBooking,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: bookingKeys.all })
    },
  })
}

// ─── Caja diaria — Query ──────────────────────────────────────────────────────

export function useCashMovements(
  date?: string,         // YYYY-MM-DD; undefined = hoy (lo resuelve el backend)
): UseQueryResult<PaginatedResponse<CashMovement>> {
  return useQuery({
    queryKey: cashMovementKeys.byDate(date),
    queryFn: () => getCashMovements(date),
  })
}

// ─── Caja — Resumen diario ────────────────────────────────────────────────────

export function useCashMovementsSummary(
  date?: string,
): UseQueryResult<CashDailySummary> {
  return useQuery({
    queryKey: cashMovementKeys.summary(date),
    queryFn: () => getCashMovementsSummary(date),
  })
}

// ─── Grilla multi-cancha — Query ──────────────────────────────────────────────

export const dailyGridKeys = {
  grid: (date: string) => ['daily-grid', date] as const,
}

export function useDailyGrid(date: string): UseQueryResult<DailyGridResponse> {
  return useQuery({
    queryKey: dailyGridKeys.grid(date),
    queryFn: () => getDailyGrid(date),
    enabled: date.length === 10,
  })
}

// ─── Dashboard — Query ────────────────────────────────────────────────────────

export const dashboardKeys = {
  summary: () => ['dashboard', 'summary'] as const,
}

export function useDashboardSummary(): UseQueryResult<DashboardSummary> {
  return useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: getDashboardSummary,
    // Refrescar cada 60 segundos para que "ocupadas ahora" se mantenga actualizado
    refetchInterval: 60_000,
  })
}
