/**
 * features/users/types.ts
 * ------------------------
 * Tipos del contrato de API para Operadores (Users con rol operator).
 * Mapean exactamente lo que devuelve el backend; no agregar campos que no existan.
 */

export interface Operator {
  id: number
  email: string
  first_name: string
  last_name: string
  role: 'operator'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateOperatorPayload {
  email: string
  password: string
  first_name: string
  last_name: string
}
