/**
 * features/auth/useCodeExchange.ts
 * ----------------------------------
 * Hook que se monta en la raíz del tenant.
 * Si detecta ?code= en la URL, lo intercambia por un par JWT y establece la sesión.
 *
 * Flujo:
 *   1. Lee ?code= de la URL actual.
 *   2. Lo elimina de la URL inmediatamente (window.history.replaceState) para
 *      que el code no quede expuesto ni en el historial del browser.
 *   3. Llama a exchangeCodeApi(code).
 *   4. Guarda access + refresh en localStorage (vía saveTokens de lib/axios).
 *   5. Navega al dashboard (/).
 *   Si el code es inválido/expirado → redirige a /login del tenant.
 *
 * El ref `attempted` previene doble ejecución en React StrictMode (donde los
 * effects se montan dos veces en desarrollo).
 */

import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { saveTokens } from '@/lib/axios'
import { exchangeCodeApi } from '@/services/centralAuth.service'

export function useCodeExchange() {
  const navigate = useNavigate()
  const attempted = useRef(false)

  useEffect(() => {
    // Prevenir doble ejecución en StrictMode
    if (attempted.current) return

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    if (!code) return

    attempted.current = true

    // Limpiar ?code= de la URL antes del request para no exponerlo
    params.delete('code')
    const cleanSearch = params.toString()
    const cleanUrl = window.location.pathname + (cleanSearch ? `?${cleanSearch}` : '')
    window.history.replaceState({}, '', cleanUrl)

    exchangeCodeApi(code)
      .then(({ access, refresh }) => {
        saveTokens(access, refresh)
        navigate('/', { replace: true })
      })
      .catch(() => {
        // Code inválido, ya usado o expirado → login del tenant
        navigate('/login', { replace: true })
      })
  }, [navigate])
}
