/**
 * services/centralAuth.service.ts
 * --------------------------------
 * Llamadas a los endpoints de autenticación centralizada (Sprint 14).
 * Todos los endpoints viven en el schema public del backend (app.localhost:8000)
 * y se consumen con centralApiClient (nunca con apiClient del tenant).
 *
 * Endpoints:
 *   POST /auth/lookup-email/    → detecta en qué complejo existe el email
 *   POST /auth/central-login/   → autentica y devuelve un one-time code
 *   POST /auth/exchange-code/   → canjea el code por par JWT (access + refresh)
 */

import { centralApiClient } from '@/lib/axios'

// ─── Tipos ───────────────────────────────────────────────────────────────────

export interface TenantMatch {
  schema_name: string
  tenant_name: string
  domain: string
}

export interface CentralLoginResponse {
  code: string
  redirect_url: string
}

export interface TokenPair {
  access: string
  refresh: string
}

// ─── API calls ───────────────────────────────────────────────────────────────

/**
 * Busca en qué complejo(s) existe una cuenta asociada al email.
 * Devuelve lista vacía si el email no tiene cuenta en ningún tenant.
 */
export async function lookupEmailApi(email: string): Promise<TenantMatch[]> {
  const { data } = await centralApiClient.post<TenantMatch[]>('/auth/lookup-email/', { email })
  return data
}

/**
 * Autentica al usuario en el complejo indicado.
 * Devuelve un one-time code y la redirect_url base del tenant.
 */
export async function centralLoginApi(
  email: string,
  password: string,
  schema_name: string,
): Promise<CentralLoginResponse> {
  const { data } = await centralApiClient.post<CentralLoginResponse>('/auth/central-login/', {
    email,
    password,
    schema_name,
  })
  return data
}

/**
 * Canjea el one-time code (recibido via ?code= en la URL del tenant) por un
 * par JWT (access + refresh). El code es de un solo uso y expira en 60 segundos.
 */
export async function exchangeCodeApi(code: string): Promise<TokenPair> {
  const { data } = await centralApiClient.post<TokenPair>('/auth/exchange-code/', { code })
  return data
}
