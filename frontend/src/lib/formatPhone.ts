/**
 * Convierte números de teléfono en formato whatsapp-web.js al formato argentino legible.
 *
 * Ejemplos:
 *   "5491112345678@c.us"  → "+54 9 11 1234-5678"
 *   "5493515551234@c.us"  → "+54 9 351 555-1234"
 *   "5491112345678"       → "+54 9 11 1234-5678"
 *   "123456"              → "+123456"
 */
export function formatPhone(raw: string): string {
  // Quitar sufijo de grupo o chat individual
  const clean = raw.replace(/@(c|g)\.us$/, '')

  // Argentina móvil: empieza con "549" seguido de 10 dígitos
  const arMatch = clean.match(/^549(\d{10})$/)
  if (arMatch) {
    const local = arMatch[1]
    if (local.startsWith('11')) {
      // Buenos Aires / AMBA: código de área 11 + 8 dígitos
      const area = local.slice(0, 2)
      const part1 = local.slice(2, 6)
      const part2 = local.slice(6)
      return `+54 9 ${area} ${part1}-${part2}`
    }
    // Interior: código de área 3 dígitos + 7 dígitos
    const area = local.slice(0, 3)
    const part1 = local.slice(3, 6)
    const part2 = local.slice(6)
    return `+54 9 ${area} ${part1}-${part2}`
  }

  // Fallback: agregar "+" al inicio
  return `+${clean}`
}
