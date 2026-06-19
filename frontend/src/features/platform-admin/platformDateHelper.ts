/**
 * features/platform-admin/platformDateHelper.ts
 * -----------------------------------------------
 * Helper de fechas para el panel de platform.
 * Convierte timestamps UTC del backend a America/Argentina/Buenos_Aires.
 *
 * REGLA: centralizar la conversión; no repetirla por componente.
 */

const BA_TIMEZONE = 'America/Argentina/Buenos_Aires'

/**
 * Formatea una fecha ISO de creación de tenant para mostrar en la tabla.
 * Ej: "2026-06-01T10:00:00Z" → "01/06/2026"
 */
export function formatTenantDate(isoString: string): string {
  try {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: BA_TIMEZONE,
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(new Date(isoString))
  } catch {
    return isoString
  }
}

/**
 * Formatea un timestamp completo (fecha + hora) en Buenos Aires.
 * Ej: "2026-06-01T10:00:00Z" → "01/06/2026, 07:00"
 */
export function formatTenantDateTime(isoString: string): string {
  try {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: BA_TIMEZONE,
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(isoString))
  } catch {
    return isoString
  }
}
