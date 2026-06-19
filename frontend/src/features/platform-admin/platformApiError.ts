/**
 * features/platform-admin/platformApiError.ts
 * ---------------------------------------------
 * Helper para mapear errores de la API de platform a mensajes
 * legibles en español rioplatense.
 *
 * Códigos de negocio del backend (FEATURE_SPEC_PLATFORM_ADMIN.md §8):
 *   SCHEMA_ALREADY_EXISTS, DOMAIN_ALREADY_EXISTS,
 *   INVALID_SCHEMA_NAME, TENANT_CREATION_FAILED.
 */

type PlatformErrorCode =
  | 'SCHEMA_ALREADY_EXISTS'
  | 'DOMAIN_ALREADY_EXISTS'
  | 'INVALID_SCHEMA_NAME'
  | 'TENANT_CREATION_FAILED'

const PLATFORM_ERROR_MESSAGES: Record<PlatformErrorCode, string> = {
  SCHEMA_ALREADY_EXISTS:
    'Ya existe un complejo con ese schema. Elegí otro identificador.',
  DOMAIN_ALREADY_EXISTS:
    'Ese dominio ya está en uso. Elegí otro dominio para el complejo.',
  INVALID_SCHEMA_NAME:
    'El schema_name solo puede contener letras minúsculas, números y guion bajo.',
  TENANT_CREATION_FAILED:
    'No se pudo crear el complejo. El proceso fue revertido. Intentá de nuevo.',
}

/**
 * Extrae el mensaje de error legible de una respuesta Axios del cliente de platform.
 */
export function extractPlatformApiError(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return 'Ocurrió un error inesperado. Intentá de nuevo.'
  }

  if ('response' in error) {
    const axiosError = error as {
      response?: { status: number; data?: unknown }
    }
    const status = axiosError.response?.status
    const data = axiosError.response?.data

    // Formato estándar: { error: { code, message } }
    if (data && typeof data === 'object' && 'error' in data) {
      const apiErr = data as { error: { code?: string; message?: string } }
      const code = apiErr.error.code as PlatformErrorCode | undefined
      if (code && PLATFORM_ERROR_MESSAGES[code]) {
        return PLATFORM_ERROR_MESSAGES[code]
      }
      if (apiErr.error.message) {
        return apiErr.error.message
      }
    }

    // Errores DRF de validación (campo: [mensaje])
    if (data && typeof data === 'object') {
      const entries = Object.entries(data as Record<string, unknown>)
      for (const [field, value] of entries) {
        if (field === 'non_field_errors' && Array.isArray(value) && value.length > 0) {
          return String(value[0])
        }
      }
      for (const [, value] of entries) {
        if (Array.isArray(value) && value.length > 0) return String(value[0])
        if (typeof value === 'string') return value
      }
    }

    if (status === 400) return 'Los datos ingresados no son válidos.'
    if (status === 401) return 'Sesión expirada. Volvé a iniciar sesión en la plataforma.'
    if (status === 403) return 'No tenés permisos de administrador de plataforma.'
    if (status === 404) return 'El recurso no fue encontrado.'
    if (status && status >= 500) return 'Error del servidor. Intentá de nuevo en unos momentos.'
  }

  if ('message' in error) {
    const msg = (error as { message: string }).message
    if (msg.toLowerCase().includes('network') || msg.toLowerCase().includes('timeout')) {
      return 'Sin conexión. Verificá tu red e intentá de nuevo.'
    }
  }

  return 'Ocurrió un error inesperado. Intentá de nuevo.'
}
