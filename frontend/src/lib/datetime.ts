/**
 * lib/datetime.ts
 * ---------------
 * FUENTE ÚNICA de conversión UTC → America/Argentina/Buenos_Aires.
 * Usar SOLO estas funciones en componentes y servicios.
 * NO repetir la lógica de timezone en otros archivos (ver RULES.md).
 *
 * Implementación con Intl.DateTimeFormat nativo (sin dependencias externas).
 * Buenos Aires no tiene horario de verano (siempre UTC-3).
 */

const TZ = 'America/Argentina/Buenos_Aires'
const LOCALE = 'es-AR'

/**
 * Formatea una fecha/hora UTC a hora de Buenos Aires con fecha y hora completas.
 * Entrada: ISO 8601 string (ej: "2026-06-05T20:00:00Z") o Date object.
 * Salida: "05/06/2026, 17:00" (formato es-AR corto).
 */
export function formatDateTimeBA(utcInput: string | Date): string {
  const date = typeof utcInput === 'string' ? new Date(utcInput) : utcInput
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TZ,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

/**
 * Formatea solo la hora de una fecha/hora UTC en hora de Buenos Aires.
 * Salida: "17:00"
 */
export function formatTimeBA(utcInput: string | Date): string {
  const date = typeof utcInput === 'string' ? new Date(utcInput) : utcInput
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TZ,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

/**
 * Formatea solo la fecha de una fecha/hora UTC en hora de Buenos Aires.
 * Salida: "viernes, 5 de junio de 2026"
 */
export function formatDateBA(utcInput: string | Date): string {
  const date = typeof utcInput === 'string' ? new Date(utcInput) : utcInput
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TZ,
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

/**
 * Formatea una fecha en formato corto para encabezados de grilla.
 * Salida: "vie 05/06"
 */
export function formatDateShortBA(utcInput: string | Date): string {
  const date = typeof utcInput === 'string' ? new Date(utcInput) : utcInput
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TZ,
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
  }).format(date)
}

/**
 * Devuelve la fecha en formato YYYY-MM-DD según la hora de Buenos Aires.
 * Útil para enviar como filtro de fecha a la API.
 */
export function toLocalDateStringBA(utcInput: string | Date): string {
  const date = typeof utcInput === 'string' ? new Date(utcInput) : utcInput
  // Usamos Intl para obtener los componentes en BA timezone
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)

  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')}`
}

/**
 * Devuelve el timestamp actual en Buenos Aires como string legible.
 * Útil para mostrar "ahora" en la UI.
 */
export function nowBA(): string {
  return formatDateTimeBA(new Date())
}
