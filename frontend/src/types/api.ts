/**
 * Tipos genéricos del contrato de la API.
 * Siguiendo API_GUIDELINES.md: errores con formato estándar,
 * paginación con count/next/previous/results.
 */

/** Formato estándar de error de la API (ver API_GUIDELINES.md §7). */
export interface ApiError {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

/**
 * Códigos de error de negocio conocidos.
 * El frontend los mapea a mensajes en español rioplatense.
 */
export type ApiErrorCode =
  | 'SLOT_ALREADY_BOOKED'
  | 'BOOKING_IN_PAST'
  | 'COURT_INACTIVE'
  | 'OUTSIDE_SCHEDULE'
  | 'INVALID_TRANSITION'
  | 'VALIDATION_ERROR'
  | 'TENANT_FORBIDDEN'

/** Respuesta paginada estándar de DRF. */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Health check response */
export interface HealthResponse {
  status: 'ok'
  timestamp: string
}
