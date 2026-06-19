/**
 * features/platform-admin/types.ts
 * ---------------------------------
 * Tipos del contrato de API del panel de System Admin.
 * Mapean exactamente los campos que devuelven los endpoints
 * /api/platform/tenants/ del backend.
 *
 * REGLA (ADR-013): estos tipos son exclusivos del panel de platform.
 * No se mezclan con los tipos de tenant (courts, bookings, etc.).
 */

export type BotMode = 'mock' | 'production'

export interface Tenant {
  id: number
  name: string
  schema_name: string
  domain: string
  is_active: boolean
  bot_mode: BotMode
  created_at: string
}

export interface TenantCreatePayload {
  name: string
  schema_name: string
  domain: string
  admin_email: string
  admin_password: string
  bot_mode?: BotMode
}

export interface TenantUpdatePayload {
  name?: string
  bot_mode?: BotMode
}

/** Payload del JWT de platform (sin verificar firma — solo presentación). */
export interface PlatformJWTPayload {
  user_id: number
  email: string
  is_superuser: boolean
  exp: number
  iat: number
}
