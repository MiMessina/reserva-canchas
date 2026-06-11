/**
 * types/settings.ts
 * -----------------
 * Tipos del contrato de API para la configuracion del complejo.
 * Mapean exactamente los campos del modelo ComplexSettings del backend.
 */

export interface ComplexSettings {
  id: number
  complex_name: string
  payment_instructions: string
  cbu_alias: string
  cbu_number: string
  account_holder: string
  phone: string
  instagram: string
  whatsapp: string
  created_at: string
  updated_at: string
}

/**
 * Payload para PATCH /api/settings/
 * Todos los campos son opcionales: solo se envian los campos que cambiaron.
 */
export type UpdateComplexSettingsRequest = Partial<
  Omit<ComplexSettings, 'id' | 'created_at' | 'updated_at'>
>
