/**
 * lib/formatters.ts
 * -----------------
 * Helpers de formato para la UI.
 * Centralizar acá para no repetir lógica de formato en los componentes.
 */

/**
 * Formatea un número o string decimal como moneda argentina (ARS).
 * Ejemplo: "150000.00" → "$150.000"
 */
export function formatCurrency(value: string | number): string {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

/**
 * Formatea una fecha YYYY-MM-DD como "lun 2 jun" (día semana abreviado + número + mes abreviado).
 * Útil para encabezados de tabla de reporte semanal.
 * La fecha se interpreta como local (sin conversión de timezone, ya que viene del backend
 * en formato YYYY-MM-DD representando una fecha en hora BA).
 */
export function formatDayLabel(dateStr: string): string {
  // Parsear como fecha local añadiendo T00:00 para evitar el ajuste UTC
  const [year, month, day] = dateStr.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  return new Intl.DateTimeFormat('es-AR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  }).format(date)
}
