/**
 * types/cashbox.ts
 * ----------------
 * Tipos del contrato de API para Sesiones de Caja (CashSession).
 * Mapean exactamente la respuesta de los endpoints /api/cash-sessions/.
 *
 * Endpoints cubiertos:
 *   POST   /api/cash-sessions/open/
 *   POST   /api/cash-sessions/close/
 *   GET    /api/cash-sessions/today/   → CashSession | 404 (null en el servicio)
 *   GET    /api/cash-sessions/         → paginado, filtrable por ?date=YYYY-MM-DD
 */

export type CashSessionStatus = 'OPEN' | 'CLOSED'

export interface CashSession {
  id: number
  operator: number
  session_date: string            // YYYY-MM-DD
  opened_at: string               // ISO UTC
  closed_at: string | null
  opening_amount: string          // decimal como string, ej: "5000.00"
  closing_amount: string | null
  expected_amount: string | null
  difference: string | null       // positivo = sobrante, negativo = faltante
  notes: string
  status: CashSessionStatus
  created_at: string              // ISO UTC
}

// ─── Payloads de mutación ──────────────────────────────────────────────────────

export interface OpenCashSessionRequest {
  opening_amount: number
  session_date?: string           // YYYY-MM-DD; omitir = hoy (lo resuelve el backend)
}

export interface CloseCashSessionRequest {
  closing_amount: number
  notes?: string
  session_date?: string           // YYYY-MM-DD; omitir = hoy (lo resuelve el backend)
}
