/**
 * lib/axios.ts
 * ------------
 * Cliente HTTP central de la aplicación.
 * - baseURL: VITE_API_BASE_URL (inyectada por Vite desde .env).
 * - Interceptor de request: adjunta Bearer JWT si hay token en localStorage.
 * - Interceptor de response: ante 401 intenta refresh una vez y reintenta.
 *   Si el refresh falla, limpia la sesión y redirige a /login.
 *
 * REGLA: solo este archivo habla con localStorage para tokens.
 * Los componentes y hooks no tocan localStorage directamente.
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { RefreshResponse } from '@/types/auth'

// Claves de localStorage. Centralizadas acá para evitar typos.
export const TOKEN_KEY = 'canchaYA_access'
export const REFRESH_KEY = 'canchaYA_refresh'

// ─── Helpers de token ─────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function saveTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// ─── Instancia Axios ──────────────────────────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  timeout: 15_000,
})

// ─── Interceptor: REQUEST ─────────────────────────────────────────────────────
// Adjunta el Access Token si existe.

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ─── Interceptor: RESPONSE ────────────────────────────────────────────────────
// Ante 401: intenta refresh UNA vez y reintenta la request original.
// Si el refresh también falla: limpia tokens y manda a /login.

let isRefreshing = false
let pendingRequests: Array<(token: string) => void> = []

function onRefreshDone(newToken: string) {
  pendingRequests.forEach((cb) => cb(newToken))
  pendingRequests = []
}

function redirectToLogin() {
  clearTokens()
  // Navegación imperativa fuera de React Router; recarga la página para limpiar estado.
  window.location.href = '/login'
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean
    }

    const is401 = error.response?.status === 401
    const alreadyRetried = originalRequest._retry === true

    // Si no es 401 o ya reintentamos, rechazar directamente.
    if (!is401 || alreadyRetried) {
      return Promise.reject(error)
    }

    const refresh = getRefreshToken()
    if (!refresh) {
      redirectToLogin()
      return Promise.reject(error)
    }

    // Evitar múltiples refresh simultáneos: encolar los requests pendientes.
    if (isRefreshing) {
      return new Promise<string>((resolve) => {
        pendingRequests.push(resolve)
      }).then((newToken) => {
        originalRequest.headers = {
          ...(originalRequest.headers ?? {}),
          Authorization: `Bearer ${newToken}`,
        }
        return apiClient(originalRequest)
      })
    }

    // Primer request que detecta el 401: hace el refresh.
    isRefreshing = true
    originalRequest._retry = true

    try {
      const { data } = await axios.post<RefreshResponse>(
        `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'}/auth/refresh/`,
        { refresh },
        { headers: { 'Content-Type': 'application/json' } },
      )

      const newAccess = data.access
      saveTokens(newAccess, refresh)
      onRefreshDone(newAccess)

      // Reintentar la request original con el nuevo token.
      originalRequest.headers = {
        ...(originalRequest.headers ?? {}),
        Authorization: `Bearer ${newAccess}`,
      }
      return apiClient(originalRequest)
    } catch {
      // Refresh falló: sesión expirada, limpiar y redirigir.
      redirectToLogin()
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  },
)

export default apiClient
