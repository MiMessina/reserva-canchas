/**
 * Tests de lib/datetime.ts
 * Verifica que la conversión UTC → Buenos Aires sea correcta.
 * Buenos Aires siempre es UTC-3 (sin horario de verano).
 */

import { describe, it, expect } from 'vitest'
import {
  formatDateTimeBA,
  formatTimeBA,
  toLocalDateStringBA,
} from './datetime'

describe('datetime helpers (UTC → America/Argentina/Buenos_Aires)', () => {
  // 2026-06-05T20:00:00Z = 17:00 hs en Buenos Aires (UTC-3)
  const utcMidnight = '2026-06-05T03:00:00Z'   // → 00:00 BA
  const utcNoon     = '2026-06-05T15:00:00Z'   // → 12:00 BA
  const utcEvening  = '2026-06-05T20:00:00Z'   // → 17:00 BA

  it('formatTimeBA convierte 20:00 UTC a 17:00 BA', () => {
    expect(formatTimeBA(utcEvening)).toBe('17:00')
  })

  it('formatTimeBA convierte 03:00 UTC a 00:00 BA', () => {
    expect(formatTimeBA(utcMidnight)).toBe('00:00')
  })

  it('formatTimeBA convierte 15:00 UTC a 12:00 BA', () => {
    expect(formatTimeBA(utcNoon)).toBe('12:00')
  })

  it('formatDateTimeBA devuelve fecha y hora en formato es-AR', () => {
    const result = formatDateTimeBA(utcEvening)
    // Debe contener la fecha local de BA y la hora 17:00
    expect(result).toContain('17:00')
    expect(result).toContain('05')
    expect(result).toContain('06')
    expect(result).toContain('2026')
  })

  it('toLocalDateStringBA devuelve YYYY-MM-DD en hora BA', () => {
    // 2026-06-05T02:59:59Z es 2026-06-04 23:59:59 en BA
    expect(toLocalDateStringBA('2026-06-05T02:59:59Z')).toBe('2026-06-04')
    // 2026-06-05T03:00:00Z es 2026-06-05 00:00:00 en BA
    expect(toLocalDateStringBA('2026-06-05T03:00:00Z')).toBe('2026-06-05')
  })

  it('acepta un objeto Date ademas de string', () => {
    const date = new Date('2026-06-05T20:00:00Z')
    expect(formatTimeBA(date)).toBe('17:00')
  })
})
