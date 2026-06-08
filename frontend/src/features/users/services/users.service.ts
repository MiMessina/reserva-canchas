/**
 * features/users/services/users.service.ts
 * ------------------------------------------
 * Llamadas a la API de Usuarios (operadores del complejo).
 * Usa el cliente axios central (lib/axios.ts).
 * No contiene logica de negocio: solo transporte HTTP.
 *
 * Endpoints:
 *   GET    /api/users/       → lista de operadores (tenant_admin, JWT)
 *   POST   /api/users/       → crear operador (tenant_admin, JWT)
 *   DELETE /api/users/{id}/  → baja logica del operador (tenant_admin, JWT)
 */

import apiClient from '@/lib/axios'
import type { PaginatedResponse } from '@/types/api'
import type { CreateOperatorPayload, Operator } from '../types'

export async function getOperators(): Promise<PaginatedResponse<Operator>> {
  const { data } = await apiClient.get<PaginatedResponse<Operator>>('/users/')
  return data
}

export async function createOperator(
  payload: CreateOperatorPayload,
): Promise<Operator> {
  const { data } = await apiClient.post<Operator>('/users/', payload)
  return data
}

export async function deleteOperator(id: number): Promise<void> {
  await apiClient.delete(`/users/${id}/`)
}
