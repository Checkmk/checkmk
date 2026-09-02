/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Reading the magnitude prefix off a raw perfdata unit.
 *
 * Checkmk check plug-ins may report a value in a prefixed unit ("MB", "k"),
 * and a metric without a registry entry arrives with nothing but that string.
 * These helpers turn it into a factor plus a base symbol, so such a metric can
 * still be scaled and labelled like a registered one.
 */
// Factor of a single-character SI magnitude prefix.
const SI_MULTIPLIER: Record<string, number> = {
  k: 1e3,
  K: 1e3,
  m: 1e6,
  M: 1e6,
  g: 1e9,
  G: 1e9,
  t: 1e12,
  T: 1e12
}

// Multi-character base units that begin with what looks like an SI prefix
// ("ms" is milliseconds, not mega-seconds). Treated as atomic.
const NON_SI_PREFIXED_UNITS = new Set(['ms', 'µs', 'us', 'ns', 'min'])

/** Whether the unit is nothing but a magnitude prefix ("k", "M"). */
export function isSingleCharSIPrefix(unit: string | null | undefined): boolean {
  return !!unit && unit.length === 1 && SI_MULTIPLIER[unit] !== undefined
}

/** Factor converting a value in ``unit`` to its unprefixed base unit. */
export function siScaleOf(unit: string | null | undefined): number {
  if (!unit || NON_SI_PREFIXED_UNITS.has(unit)) {
    return 1
  }
  if (unit.length === 1) {
    return SI_MULTIPLIER[unit] ?? 1
  }
  return /^[kKmMgGtT]/.test(unit) ? (SI_MULTIPLIER[unit.charAt(0)] ?? 1) : 1
}

/** ``value`` in ``unit``, converted to that unit's unprefixed base unit. */
export function normalizeMetricValue(value: number, unit?: string): number {
  return value * siScaleOf(unit)
}

/** The unit symbol left once the magnitude prefix is scaled away: "MB" → "B". */
export function baseUnit(unit: string | null | undefined): string {
  if (!unit) {
    return ''
  }
  if (NON_SI_PREFIXED_UNITS.has(unit)) {
    return unit
  }
  if (isSingleCharSIPrefix(unit)) {
    return ''
  }
  return /^[kKmMgGtT]/.test(unit) && unit.length > 1 ? unit.slice(1) : unit
}

/**
 * Split a value into its scaled numeric part and an SI prefix, so a caller can
 * concatenate the prefix onto a base symbol and get one composite unit
 * ("60.4 MB/s") instead of magnitude-then-unit with a gap ("60.4M B/s").
 */
export function splitMagnitude(value: number): { num: string; prefix: string } {
  if (value === 0) {
    return { num: '0', prefix: '' }
  }
  const magnitude = Math.abs(value)
  if (magnitude >= 1e12) {
    return { num: (value / 1e12).toFixed(1), prefix: 'T' }
  }
  if (magnitude >= 1e9) {
    return { num: (value / 1e9).toFixed(1), prefix: 'G' }
  }
  if (magnitude >= 1e6) {
    return { num: (value / 1e6).toFixed(1), prefix: 'M' }
  }
  if (magnitude >= 1e3) {
    return { num: (value / 1e3).toFixed(1), prefix: 'k' }
  }
  return {
    num:
      magnitude >= 100 ? value.toFixed(0) : magnitude >= 10 ? value.toFixed(1) : value.toFixed(2),
    prefix: ''
  }
}

/** "value unit" for a base-unit value, with the prefix folded onto the symbol. */
export function fmtValueWithUnit(value: number, unit: string | null | undefined): string {
  const symbol = baseUnit(unit)
  if (NON_SI_PREFIXED_UNITS.has(symbol)) {
    return `${Math.round(value)} ${symbol}`
  }
  const { num, prefix } = splitMagnitude(value)
  if (!symbol) {
    return num + prefix
  }
  return symbol === '%' ? `${num}${prefix}${symbol}` : `${num} ${prefix}${symbol}`
}
