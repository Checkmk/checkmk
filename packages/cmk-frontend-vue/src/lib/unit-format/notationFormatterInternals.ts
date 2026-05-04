/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Internal helpers for `notationFormatter.ts`. Everything here is used only by
// the formatter classes in that file; the longer Python-parity comments live
// here so the public surface stays scannable. Not part of the package's
// public API — do not import from outside `unit-format`.

export const MAX_DIGITS = 5

// Mirrors the lambdas hard-coded into Python's `render` and
// `render_y_labels` in `cmk/gui/unit_formatter.py`.
export type AutoPrecisionDigits = (exponent: number, digits: number) => number

export const RENDER_AUTO_DIGITS: AutoPrecisionDigits = (exp, d) => Math.max(exp + 1, d)
export const Y_LABELS_AUTO_DIGITS: AutoPrecisionDigits = (exp, d) => exp + d

// Python's round() uses banker's rounding (round-half-to-even); JS Math.round
// rounds half away from zero. The legacy Python TimeFormatter relies on
// banker's rounding for boundary cases like 182.5 days → 182 — we match that
// here so server- and client-rendered values agree during the migration.
//
// Scope: only safe for inputs whose fractional part is exactly 0.5 in IEEE
// 754 (e.g. (intA - intB * intC) / intD with small integers — what
// TimeFormatter feeds it). Do not reuse for arbitrary floating-point input.
export function roundHalfToEven(value: number): number {
  const floor = Math.floor(value)
  const diff = value - floor
  if (diff < 0.5) {
    return floor
  }
  if (diff > 0.5) {
    return floor + 1
  }
  return floor % 2 === 0 ? floor : floor + 1
}

// Symbols starting with '/' or '%' follow the value with no separator
// (e.g. "2/s", "50%"); everything else is space-separated. Same join rule
// as `_join_text_and_unit` in `cmk/gui/unit_formatter.py`, kept identical
// while the two implementations coexist.
//
// Note on call-site asymmetry: SI/IEC/Time call this as
// `joinValueAndUnit(text, prefix + symbol)` because the SI prefix sticks to
// the unit ("kB", "Mis"), while StandardScientific/EngineeringScientific call
// `joinValueAndUnit(text + prefix, symbol)` because the "eN" exponent prefix
// sticks to the value ("1.23e+5"). Either way `unit[0]` here is the first
// character the user actually sees as part of the unit string.
export function joinValueAndUnit(value: string, unit: string): string {
  if (unit && (unit[0] === '/' || unit[0] === '%')) {
    return value + unit
  }
  return unit ? `${value} ${unit}` : value
}

// THIN SPACE (U+2009) — used as the thousands separator in DecimalFormatter
// to match the legacy Python output (`f"{value:,}".replace(",", "\N{THIN
// SPACE}")` in `cmk/gui/unit_formatter.py:DecimalFormatter._stringify_formatted_value`).
const THIN_SPACE = ' '

// Mirrors Python's `f"{value:,}".replace(",", "\N{THIN SPACE}")` for the
// integer portion of a decimal string.
export function withThousandsSeparator(text: string): string {
  const dotIndex = text.indexOf('.')
  const intPart = dotIndex === -1 ? text : text.slice(0, dotIndex)
  const fracPart = dotIndex === -1 ? '' : text.slice(dotIndex)
  const sign = intPart.startsWith('-') ? '-' : ''
  const digits = sign ? intPart.slice(1) : intPart
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, THIN_SPACE)
  return `${sign}${grouped}${fracPart}`
}

// Precise integer-exponent power-of-10. V8's Math.pow with negative integer
// exponents goes via exp(n * log(10)) and accumulates a 1-ULP error
// (`pow10(-4)` returns 0.00009999999999999999, not 0.0001). Python's
// `pow(10, n)` routes through a precise division path. We need a matching
// path here so y-label atom values agree byte-for-byte with the Python
// fixtures (e.g. `2 * pow10(-4)` must be 0.0002, not 0.00019999...).
export function pow10(n: number): number {
  if (n >= 0) {
    let result = 1
    for (let i = 0; i < n; i++) {
      result *= 10
    }
    return result
  }
  let result = 1
  for (let i = 0; i < -n; i++) {
    result *= 10
  }
  return 1 / result
}

function rstrip(value: string, chars: string): string {
  let end = value.length - 1
  while (end >= 0 && chars.indexOf(value[end]!) >= 0) {
    end -= 1
  }
  return value.substring(0, end + 1)
}

export function sanitize(value: string): string {
  return rstrip(rstrip(value, '0'), '.')
}

export class Preformatted {
  constructor(
    public value: number,
    public prefix: string,
    public symbol: string
  ) {}
}

export class Formatted {
  constructor(
    public text: string,
    public prefix: string,
    public symbol: string
  ) {}
}

// Mirrors Python's _SI_SMALL_PREFIXES / _SI_LARGE_PREFIXES /
// _IEC_LARGE_PREFIXES / _TIME_SMALL_PREFIXES. Entries are listed in
// descending magnitude — formatters pick the first match.
export type PrefixEntry = { exp: number; power: number; prefix: string }

export const SI_SMALL_PREFIXES: PrefixEntry[] = [
  { exp: -24, power: 8, prefix: 'y' },
  { exp: -21, power: 7, prefix: 'z' },
  { exp: -18, power: 6, prefix: 'a' },
  { exp: -15, power: 5, prefix: 'f' },
  { exp: -12, power: 4, prefix: 'p' },
  { exp: -9, power: 3, prefix: 'n' },
  { exp: -6, power: 2, prefix: 'μ' },
  { exp: -3, power: 1, prefix: 'm' }
]

export const SI_LARGE_PREFIXES: PrefixEntry[] = [
  { exp: 24, power: 8, prefix: 'Y' },
  { exp: 21, power: 7, prefix: 'Z' },
  { exp: 18, power: 6, prefix: 'E' },
  { exp: 15, power: 5, prefix: 'P' },
  { exp: 12, power: 4, prefix: 'T' },
  { exp: 9, power: 3, prefix: 'G' },
  { exp: 6, power: 2, prefix: 'M' },
  { exp: 3, power: 1, prefix: 'k' }
]

export const IEC_LARGE_PREFIXES: PrefixEntry[] = [
  { exp: 80, power: 8, prefix: 'Yi' },
  { exp: 70, power: 7, prefix: 'Zi' },
  { exp: 60, power: 6, prefix: 'Ei' },
  { exp: 50, power: 5, prefix: 'Pi' },
  { exp: 40, power: 4, prefix: 'Ti' },
  { exp: 30, power: 3, prefix: 'Gi' },
  { exp: 20, power: 2, prefix: 'Mi' },
  { exp: 10, power: 1, prefix: 'Ki' }
]

export const TIME_SMALL_PREFIXES: PrefixEntry[] = [
  { exp: -6, power: 2, prefix: 'μ' },
  { exp: -3, power: 1, prefix: 'm' }
]

export function findPrefixPower(usePrefix: string, table: PrefixEntry[]): number {
  for (const entry of table) {
    if (entry.prefix === usePrefix) {
      return entry.power
    }
  }
  return 1
}

export const ONE_YEAR = 31536000
export const ONE_DAY = 86400
export const ONE_HOUR = 3600
export const ONE_MINUTE = 60

// Atom tables for y-axis label spacing. Mirrors `_BASIC_DECIMAL_ATOMS` and
// `_BASIC_TIME_ATOMS` in cmk/gui/unit_formatter.py.
export const BASIC_DECIMAL_ATOMS: number[] = [1, 2, 5, 10, 20, 50]

export const BASIC_TIME_ATOMS: number[] = [
  1,
  2,
  5,
  10,
  20,
  30,
  ONE_MINUTE,
  2 * ONE_MINUTE,
  5 * ONE_MINUTE,
  10 * ONE_MINUTE,
  20 * ONE_MINUTE,
  30 * ONE_MINUTE,
  ONE_HOUR,
  2 * ONE_HOUR,
  4 * ONE_HOUR,
  6 * ONE_HOUR,
  8 * ONE_HOUR,
  12 * ONE_HOUR,
  ONE_DAY,
  2 * ONE_DAY,
  5 * ONE_DAY,
  10 * ONE_DAY,
  20 * ONE_DAY,
  50 * ONE_DAY,
  100 * ONE_DAY,
  ONE_YEAR,
  2 * ONE_YEAR,
  5 * ONE_YEAR,
  10 * ONE_YEAR,
  20 * ONE_YEAR,
  50 * ONE_YEAR,
  100 * ONE_YEAR
]

export const TIME_LARGE_SYMBOLS: Array<{ factor: number; symbol: string }> = [
  { factor: ONE_YEAR, symbol: 'y' },
  { factor: ONE_DAY, symbol: 'd' },
  { factor: ONE_HOUR, symbol: 'h' },
  { factor: ONE_MINUTE, symbol: 'min' }
]
