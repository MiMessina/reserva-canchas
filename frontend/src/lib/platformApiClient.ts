/**
 * lib/platformApiClient.ts
 * ------------------------
 * Cliente HTTP para el panel de System Admin (platform).
 * Separado del apiClient de tenant para cumplir ADR-013:
 * dos "sabores" de JWT en el sistema (tenant vs platform).
 *
 * - baseURL: mismo hostname que el frontend pero puerto 8000.
 *   Ej: platform.localhost:5173 → http://platform.localhost:8000/api/platform
 * - Interceptor de request: adjunta Bearer JWT desde
 *   localStorage bajo clave PLATFORM_TOKEN_KEY.
 * - Interceptor de response: ante 401 intenta refresh una vez.
 *   Si falla, limpia sesión y redirige a /login del panel.
 *
 * REGLA: solo este archivo toca las claves de localStorage de platform.
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { RefreshResponse } from '@/types/auth'

// ─── Claves de localStorage (aisladas de las de tenant) ──────────────────────

export const PLATFORM_TOKEN_KEY = 'platform_access_token'
export const PLATFORM_REFRESH_KEY = 'platform_refresh_token'

// ─── Helpers de token ─────────────────────────────────────────────────────────

export function getPlatformAccessToken(): string | null {
  return localStorage.getItem(PLATFORM_TOKEN_KEY)
}

export function getPlatformRefreshToken(): string | null {
  return localStorage.getItem(PLATFORM_REFRESH_KEY)
}

export function savePlatformTokens(access: string, refresh: string): void {
  localStorage.setItem(PLATFORM_TOKEN_KEY, access)
  localStorage.setItem(PLATFORM_REFRESH_KEY, refresh)
}

export function clearPlatformTokens(): void {
  localStorage.removeItem(PLATFORM_TOKEN_KEY)
  localStorage.removeItem(PLATFORM_REFRESH_KEY)
}

// ─── Base URL ─────────────────────────────────────────────────────────────────
// Deriva host y puerto de VITE_API_BASE_URL (igual que axios.ts) para que
// funcione tanto en dev (:8000 directo) como en prod (Nginx en :80, sin puerto).
// Dev:  VITE_API_BASE_URL=http://localhost:8000/api  → http://platform.localhost:8000/api/platform
// Prod: VITE_API_BASE_URL=http://demo.<IP>.nip.io/api → http://platform.<IP>.nip.io/api/platform

const _baseUrl = new URL(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api')
_baseUrl.hostname = window.location.hostname
_baseUrl.pathname = '/api/platform'
const platformApiBaseUrl = _baseUrl.toString().replace(/\/$/, '')

// ─── Instancia Axios ──────────────────────────────────────────────────────────

const platformApiClient: AxiosInstance = axios.create({
  baseURL: platformApiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  // 60s: la creación de tenant corre migrate_schemas (puede tardar 10-15s).
  timeout: 60_000,
})

// ─── Interceptor: REQUEST ─────────────────────────────────────────────────────

platformApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getPlatformAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ─── Interceptor: RESPONSE ────────────────────────────────────────────────────

let isRefreshing = false
let pendingRequests: Array<(token: string) => void> = []

function onRefreshDone(newToken: string) {
  pendingRequests.forEach((cb) => cb(newToken))
  pendingRequests = []
}

function redirectToPlatformLogin() {
  clearPlatformTokens()
  window.location.href = '/login'
}

platformApiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean
    }

    const is401 = error.response?.status === 401
    const alreadyRetried = originalRequest._retry === true

    if (!is401 || alreadyRetried) {
      return Promise.reject(error)
    }

    const refresh = getPlatformRefreshToken()
    if (!refresh) {
      redirectToPlatformLogin()
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve) => {
        pendingRequests.push(resolve)
      }).then((newToken) => {
        originalRequest.headers = {
          ...(originalRequest.headers ?? {}),
          Authorization: `Bearer ${newToken}`,
        }
        return platformApiClient(originalRequest)
      })
    }

    isRefreshing = true
    originalRequest._retry = true

    try {
      const { data } = await axios.post<RefreshResponse>(
        `${platformApiBaseUrl}/auth/refresh/`,
        { refresh },
        { headers: { 'Content-Type': 'application/json' } },
      )

      const newAccess = data.access
      savePlatformTokens(newAccess, refresh)
      onRefreshDone(newAccess)

      originalRequest.headers = {
        ...(originalRequest.headers ?? {}),
        Authorization: `Bearer ${newAccess}`,
      }
      return platformApiClient(originalRequest)
    } catch {
      redirectToPlatformLogin()
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  },
)

export default platformApiClient
