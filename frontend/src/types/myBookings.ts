/**
 * types/myBookings.ts
 * --------------------
 * Tipos del contrato de API para la funcionalidad "Mis Reservas" (guest lookup).
 * Mapean la respuesta de GET /api/bookings/guest-lookup/
 */

export interface GuestBooking {
  id: number
  court_name: string
  start_dt: string    // ISO 8601 UTC
  end_dt: string      // ISO 8601 UTC
  status: 'PENDING_PAYMENT' | 'CONFIRMED'
  status_display: string
  price: string       // decimal string, ej: "5000.00"
}
