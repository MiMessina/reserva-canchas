/**
 * features/courts/types.ts
 * -------------------------
 * Tipos del contrato de API para Canchas (Court) y Bloques Horarios (ScheduleBlock).
 * Mapean exactamente lo que devuelve el backend; no agregar campos que no existan.
 */

// ─── Court ───────────────────────────────────────────────────────────────────

export type CourtType = 'futbol_5' | 'futbol_7' | 'padel'

export const COURT_TYPE_LABELS: Record<CourtType, string> = {
  futbol_5: 'Futbol 5',
  futbol_7: 'Futbol 7',
  padel: 'Padel',
}

export interface Court {
  id: number
  name: string
  court_type: CourtType
  surface: string
  base_price: string        // decimal string, ej: "15000.00"
  slot_duration_minutes: number
  is_active: boolean
  created_at: string        // ISO 8601 UTC
  updated_at: string        // ISO 8601 UTC
}

export interface CreateCourtPayload {
  name: string
  court_type: CourtType
  surface?: string
  base_price: string
  slot_duration_minutes: number
}

export interface UpdateCourtPayload {
  name?: string
  court_type?: CourtType
  surface?: string
  base_price?: string
  slot_duration_minutes?: number
  is_active?: boolean
}

// ─── ScheduleBlock ────────────────────────────────────────────────────────────

/**
 * Dias de la semana: convencion del backend: 0=lunes, 1=martes, ... 6=domingo.
 */
export type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  0: 'Lunes',
  1: 'Martes',
  2: 'Miercoles',
  3: 'Jueves',
  4: 'Viernes',
  5: 'Sabado',
  6: 'Domingo',
}

export const WEEKDAY_OPTIONS: { value: Weekday; label: string }[] = [
  { value: 0, label: 'Lunes' },
  { value: 1, label: 'Martes' },
  { value: 2, label: 'Miercoles' },
  { value: 3, label: 'Jueves' },
  { value: 4, label: 'Viernes' },
  { value: 5, label: 'Sabado' },
  { value: 6, label: 'Domingo' },
]

export interface ScheduleBlock {
  id: number
  court: number             // FK id de la cancha
  weekday: Weekday
  open_time: string         // "HH:MM:SS" — hora de pared, NO convertir timezone
  close_time: string        // "HH:MM:SS" — hora de pared, NO convertir timezone
  is_active: boolean
}

export interface CreateScheduleBlockPayload {
  court: number
  weekday: Weekday
  open_time: string         // "HH:MM"
  close_time: string        // "HH:MM"
}

export interface UpdateScheduleBlockPayload {
  weekday?: Weekday
  open_time?: string
  close_time?: string
  is_active?: boolean
}

// ─── Filtros de query ─────────────────────────────────────────────────────────

export interface CourtsFilters {
  court_type?: CourtType
  is_active?: boolean
}

export interface ScheduleBlocksFilters {
  court?: number
  weekday?: Weekday
}
