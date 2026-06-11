/**
 * services/settings.ts
 * ---------------------
 * Llamadas a la API de configuracion del complejo.
 *
 * Endpoints:
 *   GET   /api/settings/  → publico, sin auth (usa publicApiClient)
 *   PATCH /api/settings/  → solo tenant_admin, requiere JWT (usa apiClient)
 */

import apiClient, { publicApiClient } from '@/lib/axios'
import type { ComplexSettings, UpdateComplexSettingsRequest } from '@/types/settings'

/**
 * Obtiene la configuracion del complejo.
 * Usa publicApiClient (sin JWT) porque el endpoint es publico:
 * el jugador tambien necesita los datos de pago al reservar.
 */
export async function getComplexSettings(): Promise<ComplexSettings> {
  const { data } = await publicApiClient.get<ComplexSettings>('/settings/')
  return data
}

/**
 * Actualiza parcialmente la configuracion del complejo.
 * Requiere JWT de tenant_admin.
 */
export async function updateComplexSettings(
  payload: UpdateComplexSettingsRequest,
): Promise<ComplexSettings> {
  const { data } = await apiClient.patch<ComplexSettings>('/settings/', payload)
  return data
}
