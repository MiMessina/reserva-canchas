/**
 * services/auth.service.ts
 * ------------------------
 * Llamadas a la API de autenticación.
 * Usa el cliente axios central (lib/axios.ts).
 * No contiene lógica de negocio: solo transporte HTTP.
 *
 * Endpoints (ver API_GUIDELINES.md + backend SimpleJWT):
 *   POST /auth/login/                   → { access, refresh }
 *   POST /auth/refresh/                 → { access }
 *   GET  /api/health/                   → { status: "ok", timestamp }
 *   POST /auth/password-reset/          → {} (envía email con link de reset)
 *   POST /auth/password-reset/confirm/  → {} (confirma el reset con uid+token)
 */

import apiClient, { publicApiClient } from '@/lib/axios'
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

/**
 * Solicita el envío del email de recuperación de contraseña.
 * No requiere JWT — usa publicApiClient.
 * El backend siempre responde 200 para no revelar si el email existe.
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await publicApiClient.post('/auth/password-reset/', { email })
}

/**
 * Confirma el reset de contraseña con el uid y token del link recibido por email.
 * No requiere JWT — usa publicApiClient.
 * Lanza error con código INVALID_RESET_LINK si el link expiró o ya fue usado.
 */
export async function confirmPasswordReset(
  uid: string,
  token: string,
  new_password: string,
): Promise<void> {
  await publicApiClient.post('/auth/password-reset/confirm/', { uid, token, new_password })
}
