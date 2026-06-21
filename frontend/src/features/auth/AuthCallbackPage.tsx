/**
 * features/auth/AuthCallbackPage.tsx
 * ------------------------------------
 * Ruta pública /auth/callback — destino del redirect tras login centralizado.
 *
 * Patrón OAuth2/OIDC: ruta pública dedicada para intercambiar el OTC por JWT.
 * Elimina la race condition donde useCodeExchange vivía en TenantRootLayout:
 * el Navigate de ProtectedRoute limpiaba la URL antes de que el effect pudiera
 * leer ?code=, ya que los effects en hijos se ejecutan antes que en el padre.
 *
 * Flujo:
 *   1. Leer ?code= de la URL (useSearchParams de React Router).
 *   2. Si no hay código → redirigir a /login (acceso directo sin código).
 *   3. Llamar exchangeCodeApi(code).
 *   4. Éxito → saveTokens() + navigate('/').
 *   5. Error → navigate('/login?error=expired') (código inválido o expirado).
 */

import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { saveTokens } from '@/lib/axios'
import { exchangeCodeApi } from '@/services/centralAuth.service'
import { Spinner } from '@/components/Spinner'

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const attempted = useRef(false)

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true

    const code = searchParams.get('code')

    if (!code) {
      navigate('/login', { replace: true })
      return
    }

    exchangeCodeApi(code)
      .then(({ access, refresh }) => {
        saveTokens(access, refresh)
        navigate('/', { replace: true })
      })
      .catch(() => {
        navigate('/login?error=expired', { replace: true })
      })
  }, [navigate, searchParams])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" />
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          Iniciando sesión…
        </p>
      </div>
    </div>
  )
}
