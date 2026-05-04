/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Notation formatters for the cmk-frontend-vue unit-format library. This is
// the canonical implementation going forward; cmk/gui/unit_formatter.py and
// the legacy port at packages/cmk-frontend/src/js/modules/number_format.ts
// are on a deprecation path and will be removed as call sites migrate to the
// Vue stack. Until then, output here must stay byte-identical with the
// Python equivalent so server- and client-rendered values agree.
import {
  type AutoPrecisionDigits,
  BASIC_DECIMAL_ATOMS,
  BASIC_TIME_ATOMS,
  Formatted,
  IEC_LARGE_PREFIXES,
  MAX_DIGITS,
  ONE_DAY,
  ONE_HOUR,
  ONE_MINUTE,
  ONE_YEAR,
  Preformatted,
  RENDER_AUTO_DIGITS,
  SI_LARGE_PREFIXES,
  SI_SMALL_PREFIXES,
  TIME_LARGE_SYMBOLS,
  TIME_SMALL_PREFIXES,
  Y_LABELS_AUTO_DIGITS,
  findPrefixPower,
  joinValueAndUnit,
  pow10,
  roundHalfToEven,
  sanitize,
  withThousandsSeparator
} from '@/lib/unit-format/notationFormatterInternals'

export type Precision = { type: 'auto' | 'strict'; digits: number }

/** A single y-axis label produced by `renderYLabels`. */
export type Label = { value: number; text: string }

/** Inclusive range of values along a positive y-axis (`0 <= start <= end`). */
export type PositiveYRange = { kind: 'positive'; start: number; end: number }

/** Inclusive range of values along a negative y-axis (`start <= end <= 0`). */
export type NegativeYRange = { kind: 'negative'; start: number; end: number }

export type YRange = PositiveYRange | NegativeYRange

// Mirrors `_stringify_small_decimal_number` in `cmk/gui/unit_formatter.py`.
// Avoids JS's scientific notation for small decimals so that values like
// 1e-7 render as "0.0000001" rather than "1e-7". Precondition: value > 0.
//
// Note: JS's String() produces scientific notation only for values < 1e-6
// (compared to Python's < 1e-4 boundary), so this helper is rarely invoked
// for the Python test fixtures — but porting the algorithm preserves the
// invariant for the values where JS does switch to scientific.
export function stringifySmallDecimalNumber(value: number): string {
  const text = String(value)
  if (!text.includes('e')) {
    return text
  }
  const decimals = Math.floor(Math.abs(Math.log10(value)))
  const mantissa = text.split('e')[0]!
  const digits = mantissa.replace('.', '')
  return `0.${'0'.repeat(decimals)}${digits}`
}

export abstract class NotationFormatter {
  // useMaxDigitsForLabels gates the MAX_DIGITS clamp on the y-labels code
  // path (see _apply_precision in unit_formatter.py). render() always passes
  // true; renderYLabels() passes this flag. DecimalFormatter overrides the
  // default to false.
  constructor(
    public symbol: string,
    public precision: Precision,
    public useMaxDigitsForLabels: boolean = true
  ) {}

  protected abstract preformatSmallNumber(
    value: number,
    usePrefix: string,
    useSymbol: string
  ): Preformatted[]
  protected abstract preformatLargeNumber(
    value: number,
    usePrefix: string,
    useSymbol: string
  ): Preformatted[]
  protected abstract compose(formatted: Formatted): string
  protected abstract computeSmallYLabelAtoms(maxY: number): number[]
  protected abstract computeLargeYLabelAtoms(maxY: number): number[]

  // Override point for formatters that need a custom number-to-string step
  // (e.g. DecimalFormatter inserts a THIN SPACE thousands separator). Mirrors
  // `_stringify_formatted_value` in `cmk/gui/unit_formatter.py`.
  protected stringifyFormattedValue(value: number): string {
    return String(value)
  }

  protected applyPrecision(
    value: number,
    computeAutoPrecisionDigits: AutoPrecisionDigits,
    useMaxDigitsForLabels: boolean
  ): number {
    const valueFloor = Math.floor(value)
    if (value === valueFloor) {
      return value
    }
    // Clamp at the boundary: toFixed throws RangeError for out-of-range or
    // non-integer digit counts. Backend wire format is trusted to be sane,
    // but we don't want a malformed value to take down a graph render.
    const requestedDigits = Math.max(0, Math.min(100, Math.trunc(this.precision.digits)))
    let digits = requestedDigits
    if (this.precision.type === 'auto') {
      const exponent = Math.abs(Math.ceil(Math.log10(value - valueFloor)))
      if (exponent > 0) {
        digits = computeAutoPrecisionDigits(exponent, requestedDigits)
      }
    }
    const finalDigits = useMaxDigitsForLabels ? Math.min(digits, MAX_DIGITS) : Math.min(digits, 100)
    return parseFloat(value.toFixed(finalDigits))
  }

  protected preformat(
    value: number,
    usePrefix: string = '',
    useSymbol: string = ''
  ): Preformatted[] {
    if (value === 0 || value === 1) {
      return [new Preformatted(value, '', this.symbol)]
    }
    if (value < 1) {
      return this.preformatSmallNumber(value, usePrefix, useSymbol)
    }
    return this.preformatLargeNumber(value, usePrefix, useSymbol)
  }

  protected postformat(
    parts: Preformatted[],
    computeAutoPrecisionDigits: AutoPrecisionDigits,
    useMaxDigitsForLabels: boolean
  ): string[] {
    const results: string[] = []
    for (const part of parts) {
      let text = this.stringifyFormattedValue(
        this.applyPrecision(part.value, computeAutoPrecisionDigits, useMaxDigitsForLabels)
      )
      if (text.includes('.')) {
        text = sanitize(text)
      }
      results.push(this.compose(new Formatted(text, part.prefix, part.symbol)))
    }
    return results
  }

  public render(value: number): string {
    // The legacy cmk-frontend port skipped the abs() below and produced
    // garbage for negative inputs; fixed here.
    let sign = ''
    let absValue = value
    if (value < 0) {
      sign = '-'
      absValue = -value
    }
    const parts = this.postformat(this.preformat(absValue), RENDER_AUTO_DIGITS, true)
    return sign + parts.join(' ')
  }

  public renderYLabels(yRange: YRange, targetNumberOfLabels: number): Label[] {
    if (targetNumberOfLabels < 0) {
      throw new Error('targetNumberOfLabels must be >= 0')
    }

    let yStartPosRounded: number
    let yEndPos: number
    let signText: '' | '-' = ''
    let signNumber = 1
    if (yRange.kind === 'positive') {
      yStartPosRounded = Math.floor(yRange.start)
      yEndPos = yRange.end
    } else {
      yStartPosRounded = Math.floor(-yRange.end)
      yEndPos = -yRange.start
      signText = '-'
      signNumber = -1
    }

    const delta = yEndPos - yStartPosRounded
    if (delta === 0 || targetNumberOfLabels === 0) {
      return []
    }

    const atoms =
      delta < 1 ? this.computeSmallYLabelAtoms(delta) : this.computeLargeYLabelAtoms(delta)

    const possibleAtoms: Array<[number, number]> = []
    for (const a of atoms) {
      const n = Math.floor(delta / a)
      if (n) {
        possibleAtoms.push([a, n])
      }
    }

    let selectedAtom: number
    if (possibleAtoms.length > 0) {
      let best = possibleAtoms[0]!
      let bestDist = Math.abs(best[1] - targetNumberOfLabels)
      for (const candidate of possibleAtoms.slice(1)) {
        const dist = Math.abs(candidate[1] - targetNumberOfLabels)
        if (dist < bestDist) {
          best = candidate
          bestDist = dist
        }
      }
      selectedAtom = best[0]
    } else {
      selectedAtom = Math.floor(delta / targetNumberOfLabels)
    }

    const positionOfFirstLabel = yStartPosRounded - (yStartPosRounded % selectedAtom)
    const nLabels = Math.floor((yEndPos - positionOfFirstLabel) / selectedAtom)
    const firstFormatted = this.preformat(
      positionOfFirstLabel || positionOfFirstLabel + selectedAtom
    )[0]!

    const labels: Label[] = []
    for (let i = 0; i <= nLabels; i++) {
      const labelPosition = positionOfFirstLabel + selectedAtom * i
      if (labelPosition === 0) {
        labels.push({ value: 0, text: '0' })
        continue
      }
      const parts = this.postformat(
        this.preformat(labelPosition, firstFormatted.prefix, firstFormatted.symbol),
        Y_LABELS_AUTO_DIGITS,
        this.useMaxDigitsForLabels
      )
      labels.push({
        value: signNumber * labelPosition,
        text: signText + parts.join(' ')
      })
    }
    return labels
  }
}

export class DecimalFormatter extends NotationFormatter {
  constructor(symbol: string, precision: Precision, useMaxDigitsForLabels: boolean = false) {
    super(symbol, precision, useMaxDigitsForLabels)
  }

  protected preformatSmallNumber(value: number): Preformatted[] {
    return [new Preformatted(value, '', this.symbol)]
  }

  protected preformatLargeNumber(value: number): Preformatted[] {
    return [new Preformatted(value, '', this.symbol)]
  }

  protected override stringifyFormattedValue(value: number): string {
    if (value > 0 && value < 1) {
      // Avoid JS scientific notation for small decimals — mirrors Python's
      // `_stringify_small_decimal_number` branch.
      return stringifySmallDecimalNumber(value)
    }
    return withThousandsSeparator(String(value))
  }

  protected compose(formatted: Formatted): string {
    return joinValueAndUnit(formatted.text, formatted.symbol)
  }

  protected computeSmallYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }
}

export class SIFormatter extends NotationFormatter {
  protected preformatSmallNumber(value: number, usePrefix: string): Preformatted[] {
    if (usePrefix) {
      const power = findPrefixPower(usePrefix, SI_SMALL_PREFIXES)
      return [new Preformatted(value * Math.pow(1000, power), usePrefix, this.symbol)]
    }
    const exponent = Math.floor(Math.log10(value)) - 1
    for (const entry of SI_SMALL_PREFIXES) {
      if (exponent <= entry.exp) {
        return [new Preformatted(value * Math.pow(1000, entry.power), entry.prefix, this.symbol)]
      }
    }
    return [new Preformatted(value, '', this.symbol)]
  }

  protected preformatLargeNumber(value: number, usePrefix: string): Preformatted[] {
    if (usePrefix) {
      const power = findPrefixPower(usePrefix, SI_LARGE_PREFIXES)
      return [new Preformatted(value / Math.pow(1000, power), usePrefix, this.symbol)]
    }
    const exponent = Math.floor(Math.log10(value))
    for (const entry of SI_LARGE_PREFIXES) {
      if (exponent >= entry.exp) {
        return [new Preformatted(value / Math.pow(1000, entry.power), entry.prefix, this.symbol)]
      }
    }
    return [new Preformatted(value, '', this.symbol)]
  }

  protected compose(formatted: Formatted): string {
    return joinValueAndUnit(formatted.text, formatted.prefix + formatted.symbol)
  }

  protected computeSmallYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }
}

export class IECFormatter extends NotationFormatter {
  protected preformatSmallNumber(value: number): Preformatted[] {
    return [new Preformatted(value, '', this.symbol)]
  }

  protected preformatLargeNumber(value: number, usePrefix: string): Preformatted[] {
    if (usePrefix) {
      const power = findPrefixPower(usePrefix, IEC_LARGE_PREFIXES)
      return [new Preformatted(value / Math.pow(1024, power), usePrefix, this.symbol)]
    }
    const exponent = Math.floor(Math.log2(value))
    for (const entry of IEC_LARGE_PREFIXES) {
      if (exponent >= entry.exp) {
        return [new Preformatted(value / Math.pow(1024, entry.power), entry.prefix, this.symbol)]
      }
    }
    return [new Preformatted(value, '', this.symbol)]
  }

  protected compose(formatted: Formatted): string {
    return joinValueAndUnit(formatted.text, formatted.prefix + formatted.symbol)
  }

  protected computeSmallYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    const exponent = Math.floor(Math.log2(maxY))
    const result: number[] = []
    for (let e = 0; e <= exponent; e++) {
      result.push(Math.pow(2, e))
    }
    return result
  }
}

export class StandardScientificFormatter extends NotationFormatter {
  protected preformatSmallNumber(value: number): Preformatted[] {
    const exponent = Math.floor(Math.log10(value))
    return [new Preformatted(value / pow10(exponent), `e${exponent}`, this.symbol)]
  }

  protected preformatLargeNumber(value: number): Preformatted[] {
    const exponent = Math.floor(Math.log10(value))
    return [new Preformatted(value / pow10(exponent), `e+${exponent}`, this.symbol)]
  }

  protected compose(formatted: Formatted): string {
    return joinValueAndUnit(formatted.text + formatted.prefix, formatted.symbol)
  }

  protected computeSmallYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }
}

export class EngineeringScientificFormatter extends NotationFormatter {
  protected preformatSmallNumber(value: number): Preformatted[] {
    const exponent = Math.floor(Math.log10(value) / 3) * 3
    return [new Preformatted(value / pow10(exponent), `e${exponent}`, this.symbol)]
  }

  protected preformatLargeNumber(value: number): Preformatted[] {
    const exponent = Math.floor(Math.log10(value) / 3) * 3
    return [new Preformatted(value / pow10(exponent), `e+${exponent}`, this.symbol)]
  }

  protected compose(formatted: Formatted): string {
    return joinValueAndUnit(formatted.text + formatted.prefix, formatted.symbol)
  }

  protected computeSmallYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }
}

export class TimeFormatter extends NotationFormatter {
  protected preformatSmallNumber(value: number, usePrefix: string): Preformatted[] {
    if (usePrefix) {
      const power = findPrefixPower(usePrefix, TIME_SMALL_PREFIXES)
      return [new Preformatted(value * Math.pow(1000, power), usePrefix, this.symbol)]
    }
    const exponent = Math.floor(Math.log10(value)) - 1
    for (const entry of TIME_SMALL_PREFIXES) {
      if (exponent <= entry.exp) {
        return [new Preformatted(value * Math.pow(1000, entry.power), entry.prefix, this.symbol)]
      }
    }
    return [new Preformatted(value, '', this.symbol)]
  }

  protected preformatLargeNumber(
    value: number,
    _usePrefix: string,
    useSymbol: string
  ): Preformatted[] {
    let chosenSymbol = useSymbol
    if (!chosenSymbol) {
      for (const entry of TIME_LARGE_SYMBOLS) {
        if (value >= entry.factor) {
          chosenSymbol = entry.symbol
          break
        }
      }
    }
    const roundedValue = roundHalfToEven(value)
    const parts: Preformatted[] = []
    switch (chosenSymbol) {
      case 'y': {
        const years = Math.floor(roundedValue / ONE_YEAR)
        parts.push(new Preformatted(years, '', 'y'))
        const days = roundHalfToEven((roundedValue - years * ONE_YEAR) / ONE_DAY)
        if (days > 0) {
          parts.push(new Preformatted(days, '', 'd'))
        }
        break
      }
      case 'd': {
        const days = Math.floor(roundedValue / ONE_DAY)
        parts.push(new Preformatted(days, '', 'd'))
        const hours = roundHalfToEven((roundedValue - days * ONE_DAY) / ONE_HOUR)
        if (days < 10 && hours > 0) {
          parts.push(new Preformatted(hours, '', 'h'))
        }
        break
      }
      case 'h': {
        const hours = Math.floor(roundedValue / ONE_HOUR)
        parts.push(new Preformatted(hours, '', 'h'))
        const minutes = roundHalfToEven((roundedValue - hours * ONE_HOUR) / ONE_MINUTE)
        if (minutes > 0) {
          parts.push(new Preformatted(minutes, '', 'min'))
        }
        break
      }
      case 'min': {
        const minutes = Math.floor(roundedValue / ONE_MINUTE)
        parts.push(new Preformatted(minutes, '', 'min'))
        const seconds = roundHalfToEven(roundedValue - minutes * ONE_MINUTE)
        if (seconds > 0) {
          parts.push(new Preformatted(seconds, '', 's'))
        }
        break
      }
      default: {
        parts.push(new Preformatted(value, '', 's'))
      }
    }
    return parts
  }

  protected compose(formatted: Formatted): string {
    return joinValueAndUnit(formatted.text, formatted.prefix + formatted.symbol)
  }

  protected computeSmallYLabelAtoms(maxY: number): number[] {
    const factor = pow10(Math.floor(Math.log10(maxY)) - 1)
    return BASIC_DECIMAL_ATOMS.map((a) => a * factor)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    if (maxY >= ONE_YEAR) {
      const q = Math.floor(maxY / ONE_YEAR)
      if (q < 5) {
        return BASIC_TIME_ATOMS.slice(22)
      }
      const exponent = Math.floor(Math.log10(q))
      return [
        ...BASIC_TIME_ATOMS.slice(22),
        ...BASIC_DECIMAL_ATOMS.map((a) => ONE_YEAR * a * pow10(exponent - 1))
      ]
    }
    if (maxY >= ONE_DAY) {
      return BASIC_TIME_ATOMS.slice(15)
    }
    if (maxY >= ONE_HOUR) {
      return BASIC_TIME_ATOMS.slice(9, 18)
    }
    if (maxY >= ONE_MINUTE) {
      return BASIC_TIME_ATOMS.slice(3, 12)
    }
    return BASIC_DECIMAL_ATOMS.slice(0, 6)
  }
}
