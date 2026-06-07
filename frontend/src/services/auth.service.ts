/**
 * services/auth.service.ts
 * ------------------------
 * Llamadas a la API de autenticación.
 * Usa el cliente axios central (lib/axios.ts).
 * No contiene lógica de negocio: solo transporte HTTP.
 *
 * Endpoints (ver API_GUIDELINES.md + backend SimpleJWT):
 *   POST /auth/login/   → { access, refresh }
 *   POST /auth/refresh/ → { access }
 *   GET  /api/health/   → { status: "ok", timestamp }
 */

import apiClient from '@/lib/axios'
import type { LoginRequest, LoginResponse, RefreshRequest, RefreshResponse } from '@/types/auth'
import type { HealthResponse } from '@/types/api'

export async function loginApi(credentials: LoginRequest): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/login/', credentials)
  return data
}

export async function refreshApi(payload: RefreshRequest): Promise<RefreshResponse> {
  const { data } = await apiClient.post<RefreshResponse>('/auth/refresh/', payload)
  return data
}

export async function healthCheckApi(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health/')
  return data
}
