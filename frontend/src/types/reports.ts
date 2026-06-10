/**
 * types/reports.ts
 * ----------------
 * Tipos del contrato de API para los reportes semanales.
 * Mapean exactamente la respuesta de GET /api/bookings/weekly-report/.
 */

export interface WeeklyReportTotals {
  bookings_total: number
  confirmed: number
  cancelled: number
  completed: number
  pending_payment: number
  revenue_confirmed: string       // decimal string, ej: "150000.00"
}

export interface WeeklyReportByDay {
  date: string                    // YYYY-MM-DD
  bookings_total: number
  confirmed: number
  cancelled: number
  completed: number
  pending_payment: number
  revenue_confirmed: string       // decimal string
}

export interface WeeklyReportByCourt {
  court_id: number
  court_name: string
  court_type: string              // ej: "FUTBOL5", "PADEL"
  bookings_total: number
  confirmed_or_completed: number
  occupancy_pct: number           // 0–100
  revenue_confirmed: string       // decimal string
}

export interface WeeklyReport {
  date_from: string               // YYYY-MM-DD
  date_to: string                 // YYYY-MM-DD
  totals: WeeklyReportTotals
  by_day: WeeklyReportByDay[]
  by_court: WeeklyReportByCourt[]
}
