/**
 * services/myBookingsService.ts
 * ------------------------------
 * Llamadas a la API pública para que un invitado consulte y cancele sus reservas.
 * No requiere autenticación JWT (usa publicApiClient).
 *
 * GET  /api/bookings/guest-lookup/?phone=... → lista de reservas del invitado
 * POST /api/bookings/{id}/cancel-guest/      → cancelar reserva como invitado
 */

import { publicApiClient } from '@/lib/axios'
import type { GuestBooking } from '@/types/myBookings'

export const lookupBookingsByPhone = (phone: string): Promise<GuestBooking[]> =>
  publicApiClient
    .get<GuestBooking[]>('/api/bookings/guest-lookup/', { params: { phone } })
    .then((r) => r.data)

export const cancelBookingAsGuest = (
  bookingId: number,
  guestPhone: string,
): Promise<GuestBooking> =>
  publicApiClient
    .post<GuestBooking>(`/api/bookings/${bookingId}/cancel-guest/`, {
      guest_phone: guestPhone,
    })
    .then((r) => r.data)
