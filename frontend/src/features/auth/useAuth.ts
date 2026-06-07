/**
 * features/auth/useAuth.ts
 * ------------------------
 * Hook central de autenticación.
 * Expone: user (payload JWT decodificado), isAuthenticated, login, logout.
 *
 * Reglas:
 * - El token se guarda en localStorage via lib/axios.ts (TOKEN_KEY / REFRESH_KEY).
 * - El payload JWT se decodifica SOLO para presentación (no para seguridad — la
 *   autorización real la hace el backend en cada request).
 * - No se verifica la firma del JWT en el frontend (eso es responsabilidad del backend).
 */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAccessToken, saveTokens, clearTokens } from '@/lib/axios'
import { loginApi } from '@/services/auth.service'
import type { LoginRequest, JWTPayload } from '@/types/auth'

/** Decodifica el payload de un JWT sin verificar la firma. Solo para presentación. */
function decodeJWTPayload(token: string): JWTPayload | null {
  try {
    const base64 = token.split('.')[1]
    const decoded = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded) as JWTPayload
  } catch {
    return null
  }
}

function getUserFromStorage(): JWTPayload | null {
  const token = getAccessToken()
  if (!token) return null
  return decodeJWTPayload(token)
}

interface UseAuthReturn {
  user: JWTPayload | null
  isAuthenticated: boolean
  isLoggingIn: boolean
  loginError: string | null
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
}

export function useAuth(): UseAuthReturn {
  const navigate = useNavigate()
  const [user, setUser] = useState<JWTPayload | null>(getUserFromStorage)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  const login = useCallback(
    async (credentials: LoginRequest) => {
      setIsLoggingIn(true)
      setLoginError(null)
      try {
        const tokens = await loginApi(credentials)
        saveTokens(tokens.access, tokens.refresh)
        const payload = decodeJWTPayload(tokens.access)
        setUser(payload)
        navigate('/', { replace: true })
      } catch (err: unknown) {
        // Mapear errores HTTP a mensajes amigables en español rioplatense.
        if (
          err &&
          typeof err === 'object' &&
          'response' in err &&
          err.response &&
          typeof err.response === 'object' &&
          'status' in err.response
        ) {
          const status = (err.response as { status: number }).status
          if (status === 401 || status === 400) {
            setLoginError('Email o contraseña incorrectos. Revisá tus datos.')
          } else if (status >= 500) {
            setLoginError('Error del servidor. Intentá de nuevo en unos momentos.')
          } else {
            setLoginError('No se pudo iniciar sesión. Intentá de nuevo.')
          }
        } else {
          setLoginError('Sin conexión. Verificá tu red e intentá de nuevo.')
        }
      } finally {
        setIsLoggingIn(false)
      }
    },
    [navigate],
  )

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
    navigate('/login', { replace: true })
  }, [navigate])

  return {
    user,
    isAuthenticated: user !== null,
    isLoggingIn,
    loginError,
    login,
    logout,
  }
}
