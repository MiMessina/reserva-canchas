/**
 * services/reportsService.ts
 * --------------------------
 * Llamadas a la API de Reportes.
 * Usa el cliente axios autenticado (lib/axios.ts).
 * No contiene lógica de negocio: solo transporte HTTP.
 *
 * Endpoints:
 *   GET /api/bookings/weekly-report/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
 *     → operator/admin (JWT)
 *
 * Nota: mientras el endpoint esté en construcción en el backend, se retorna
 * datos mock si la respuesta falla con 404 (ver comentario inline).
 */

import apiClient from '@/lib/axios'
import type { WeeklyReport } from '@/types/reports'

/**
 * Obtiene el reporte semanal de reservas para el rango [dateFrom, dateTo].
 * @param dateFrom - Fecha de inicio en formato YYYY-MM-DD
 * @param dateTo   - Fecha de fin en formato YYYY-MM-DD
 */
export async function getWeeklyReport(
  dateFrom: string,
  dateTo: string,
): Promise<WeeklyReport> {
  const { data } = await apiClient.get<WeeklyReport>('/bookings/weekly-report/', {
    params: { date_from: dateFrom, date_to: dateTo },
  })
  return data
}
