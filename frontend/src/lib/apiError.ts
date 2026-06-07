/**
 * lib/apiError.ts
 * ---------------
 * Helper para extraer mensajes de error legibles desde respuestas Axios.
 * Mapea los codigos de negocio del backend (API_GUIDELINES.md §7) a
 * mensajes en espanol rioplatense.
 *
 * REGLA: no repetir este mapeo en cada componente; centralizarlo aca.
 */

import type { ApiError, ApiErrorCode } from '@/types/api'

// Codigos de negocio adicionales del modulo de canchas
type CourtsErrorCode = ApiErrorCode | 'INVALID_SCHEDULE' | 'SCHEDULE_OVERLAP'

const ERROR_MESSAGES: Record<CourtsErrorCode, string> = {
  SLOT_ALREADY_BOOKED:
    'Ese turno ya fue reservado. Eliga otro horario.',
  BOOKING_IN_PAST:
    'No se puede reservar un turno que ya paso.',
  COURT_INACTIVE:
    'La cancha no esta disponible en este momento.',
  OUTSIDE_SCHEDULE:
    'El horario esta fuera del horario habilitado.',
  INVALID_TRANSITION:
    'Esta accion no esta permitida en el estado actual de la reserva.',
  VALIDATION_ERROR:
    'Los datos ingresados no son validos. Revisa el formulario.',
  TENANT_FORBIDDEN:
    'No tenes permiso para realizar esta accion.',
  INVALID_SCHEDULE:
    'El horario de apertura debe ser anterior al de cierre.',
  SCHEDULE_OVERLAP:
    'Ya existe un bloque horario que se superpone con este dia y horario.',
}

/**
 * Extrae el mensaje de error de una respuesta Axios/API.
 * Prioriza el codigo de negocio del backend; si no lo reconoce, usa el mensaje
 * literal del backend o un fallback generico.
 */
export function extractApiErrorMessage(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return 'Ocurrio un error inesperado. Intenta de nuevo.'
  }

  // Error con respuesta HTTP (Axios)
  if ('response' in error) {
    const axiosError = error as {
      response?: {
        status: number
        data?: unknown
      }
    }
    const status = axiosError.response?.status
    const data = axiosError.response?.data

    // Intentar parsear el formato estandar del backend { error: { code, message } }
    if (data && typeof data === 'object' && 'error' in data) {
      const apiError = data as ApiError
      const code = apiError.error.code as CourtsErrorCode
      if (code && ERROR_MESSAGES[code]) {
        return ERROR_MESSAGES[code]
      }
      // Si el codigo no esta mapeado, usar el mensaje del backend directamente.
      if (apiError.error.message) {
        return apiError.error.message
      }
    }

    // Errores DRF de validacion (campo: [mensaje]) — devuelve el primero
    if (data && typeof data === 'object') {
      const entries = Object.entries(data as Record<string, unknown>)
      for (const [field, value] of entries) {
        if (field === 'non_field_errors' && Array.isArray(value) && value.length > 0) {
          return String(value[0])
        }
      }
      // Primer campo con error
      for (const [, value] of entries) {
        if (Array.isArray(value) && value.length > 0) {
          return String(value[0])
        }
        if (typeof value === 'string') {
          return value
        }
      }
    }

    // Fallback por codigo HTTP
    if (status === 400) return 'Los datos ingresados no son validos.'
    if (status === 401) return 'Sesion expirada. Volvé a iniciar sesion.'
    if (status === 403) return 'No tenes permiso para realizar esta accion.'
    if (status === 404) return 'El recurso no fue encontrado.'
    if (status && status >= 500) return 'Error del servidor. Intenta de nuevo en unos momentos.'
  }

  // Sin conexion / timeout
  if ('message' in error) {
    const msg = (error as { message: string }).message
    if (msg.toLowerCase().includes('network') || msg.toLowerCase().includes('timeout')) {
      return 'Sin conexion. Verifica tu red e intenta de nuevo.'
    }
  }

  return 'Ocurrio un error inesperado. Intenta de nuevo.'
}
