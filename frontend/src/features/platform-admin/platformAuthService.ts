/**
 * features/platform-admin/platformAuthService.ts
 * ------------------------------------------------
 * Servicio de autenticación del panel de System Admin.
 * Solo habla con /api/platform/auth/.
 *
 * REGLA (ADR-013): el JWT de platform no se mezcla con el JWT de tenant.
 * Las claves de localStorage son distintas (PLATFORM_TOKEN_KEY / PLATFORM_REFRESH_KEY).
 * Solo este archivo toca esas claves a nivel de negocio de auth.
 */

import platformApiClient, {
  savePlatformTokens,
  clearPlatformTokens,
  getPlatformAccessToken,
} from '@/lib/platformApiClient'
import type { PlatformJWTPayload } from './types'

interface PlatformLoginResponse {
  access: string
  refresh: string
}

/** Decodifica el payload de un JWT sin verificar la firma. Solo para presentación. */
function decodePlatformJWT(token: string): PlatformJWTPayload | null {
  try {
    const base64 = token.split('.')[1]
    const decoded = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded) as PlatformJWTPayload
  } catch {
    return null
  }
}

/**
 * Login con credenciales de superuser Django.
 * Guarda los tokens en localStorage y retorna el payload del JWT.
 */
export async function loginPlatform(
  email: string,
  password: string,
): Promise<PlatformJWTPayload> {
  const { data } = await platformApiClient.post<PlatformLoginResponse>(
    '/auth/login/',
    { email, password },
  )
  savePlatformTokens(data.access, data.refresh)
  const payload = decodePlatformJWT(data.access)
  if (!payload) {
    throw new Error('El token recibido no es válido.')
  }
  return payload
}

/** Limpia los tokens de platform del localStorage. */
export function logoutPlatform(): void {
  clearPlatformTokens()
}

/** Retorna el payload del JWT de platform si hay sesión activa. */
export function getPlatformUser(): PlatformJWTPayload | null {
  const token = getPlatformAccessToken()
  if (!token) return null
  return decodePlatformJWT(token)
}
