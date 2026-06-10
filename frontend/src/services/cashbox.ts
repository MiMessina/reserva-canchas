/**
 * services/cashbox.ts
 * -------------------
 * Llamadas a la API de Sesiones de Caja (CashSession).
 * Usa el cliente axios autenticado (lib/axios.ts).
 * No contiene lógica de negocio: solo transporte HTTP.
 *
 * Endpoints:
 *   POST   /api/cash-sessions/open/
 *   POST   /api/cash-sessions/close/
 *   GET    /api/cash-sessions/today/   → 200 CashSession | 404
 *   GET    /api/cash-sessions/         → paginado, filtrable por ?date=YYYY-MM-DD
 */

import apiClient from '@/lib/axios'
import type { CashSession, OpenCashSessionRequest, CloseCashSessionRequest } from '@/types/cashbox'
import type { PaginatedResponse } from '@/types/api'
import axios from 'axios'

/**
 * Obtiene la sesión de caja del día actual.
 * Retorna null si el backend responde 404 (sin sesión abierta hoy).
 */
export async function getCashSessionToday(): Promise<CashSession | null> {
  try {
    const { data } = await apiClient.get<CashSession>('/cash-sessions/today/')
    return data
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * Abre una nueva sesión de caja con el monto inicial indicado.
 */
export async function openCashSession(
  payload: OpenCashSessionRequest,
): Promise<CashSession> {
  const { data } = await apiClient.post<CashSession>('/cash-sessions/open/', payload)
  return data
}

/**
 * Cierra la sesión de caja activa con el monto contado y notas opcionales.
 */
export async function closeCashSession(
  payload: CloseCashSessionRequest,
): Promise<CashSession> {
  const { data } = await apiClient.post<CashSession>('/cash-sessions/close/', payload)
  return data
}

/**
 * Obtiene el historial de sesiones de caja.
 * @param date - Filtro opcional en formato YYYY-MM-DD.
 */
export async function getCashSessionHistory(
  date?: string,
): Promise<CashSession[]> {
  const { data } = await apiClient.get<PaginatedResponse<CashSession>>(
    '/cash-sessions/',
    { params: date ? { date } : undefined },
  )
  return data.results
}
