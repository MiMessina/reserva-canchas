/**
 * Tipos del contrato de autenticación.
 * Mapean exactamente la respuesta de SimpleJWT del backend.
 * No agregar campos que el backend no devuelva.
 */

export interface TokenPair {
  access: string
  refresh: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse extends TokenPair {}

export interface RefreshRequest {
  refresh: string
}

export interface RefreshResponse {
  access: string
}

/** Payload decodificado del JWT (sin verificar firma — solo presentación). */
export interface JWTPayload {
  user_id: number
  email: string
  /** Rol del usuario: tenant_admin | operator | player */
  role: 'tenant_admin' | 'operator' | 'player'
  exp: number
  iat: number
}
