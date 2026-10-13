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
  BASIC_DECIMAL_ATOMS,
  BASIC_TIME_ATOMS,
  Formatted,
  IEC_LARGE_PREFIXES,
  MAX_DIGITS,
  MIN_LABELS_PER_AXIS,
  ONE_DAY,
  ONE_HOUR,
  ONE_MINUTE,
  ONE_YEAR,
  ON_MULTIPLE_TOLERANCE,
  Preformatted,
  SI_LARGE_PREFIXES,
  SI_SMALL_PREFIXES,
  TIME_LARGE_SYMBOLS,
  TIME_SMALL_PREFIXES,
  decimalAtoms,
  findPrefixPower,
  joinValueAndUnit,
  pow10,
  roundHalfToEven,
  sanitize,
  withThousandsSeparator
} from 'cmk-ui-library/lib/unit-format/notationFormatterInternals'

export type Precision = { type: 'auto' | 'strict'; digits: number }

function decimalsNeededToWrite(spacing: number): number {
  return Math.max(0, Math.ceil(-Math.log10(spacing)))
}

export function precisionForSpacing(unitPrecision: Precision, spacing: number): Precision {
  return {
    type: unitPrecision.type,
    digits: Math.max(unitPrecision.digits, decimalsNeededToWrite(spacing))
  }
}

/**
 * The resolution in the unit `part` is displayed in. `preformat` scaled the raw value by a prefix
 * factor (2 000 000 B reads as 2 MB), and a resolution of 2 000 B scales with it to 0.002 MB;
 * counting the raw resolution's decimals would round 1.996 MB and 1.998 MB both to 2 MB.
 */
function displayedResolution(resolution: number, rawValue: number, part: Preformatted): number {
  return rawValue === 0 ? resolution : resolution * Math.abs(part.value / rawValue)
}

export function multiplesWithin(start: number, end: number, spacing: number): number[] {
  const firstIndex = Math.ceil(start / spacing - ON_MULTIPLE_TOLERANCE)
  const lastIndex = Math.floor(end / spacing + ON_MULTIPLE_TOLERANCE)
  const multiples: number[] = []
  for (let index = firstIndex; index <= lastIndex; index++) {
    multiples.push(index * spacing)
  }
  return multiples
}

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
    precision: Precision,
    useMaxDigitsForLabels: boolean
  ): number {
    const valueFloor = Math.floor(value)
    if (value === valueFloor) {
      return value
    }
    // Clamp at the boundary: toFixed throws RangeError for out-of-range or
    // non-integer digit counts. Backend wire format is trusted to be sane,
    // but we don't want a malformed value to take down a graph render.
    const requestedDigits = Math.max(0, Math.min(100, Math.trunc(precision.digits)))
    let digits = requestedDigits
    if (precision.type === 'auto') {
      const exponent = Math.abs(Math.ceil(Math.log10(value - valueFloor)))
      if (exponent > 0) {
        digits = Math.max(exponent + 1, requestedDigits)
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

  /**
   * `rawValue` is the value the parts were preformatted from; `resolution` the gap in raw units
   * two rendered values must stay apart by, or null for the unit's own precision.
   */
  protected postformat(
    parts: Preformatted[],
    rawValue: number,
    resolution: number | null,
    useMaxDigitsForLabels: boolean
  ): string[] {
    const results: string[] = []
    for (const part of parts) {
      const precision =
        resolution === null
          ? this.precision
          : precisionForSpacing(this.precision, displayedResolution(resolution, rawValue, part))
      let text = this.stringifyFormattedValue(
        this.applyPrecision(part.value, precision, useMaxDigitsForLabels)
      )
      if (text.includes('.')) {
        text = sanitize(text)
      }
      results.push(this.compose(new Formatted(text, part.prefix, part.symbol)))
    }
    return results
  }

  /**
   * `resolution` is the gap two rendered values must stay apart by, such as a graph's axis
   * spacing; null renders at the unit's own precision.
   */
  public render(value: number, resolution: number | null = null): string {
    // The legacy cmk-frontend port skipped the abs() below and produced
    // garbage for negative inputs; fixed here.
    let sign = ''
    let absValue = value
    if (value < 0) {
      sign = '-'
      absValue = -value
    }
    const parts = this.postformat(this.preformat(absValue), absValue, resolution, true)
    return sign + parts.join(' ')
  }

  protected selectLabelSpacing(span: number, targetNumberOfLabels: number): number {
    const labelCount = (atom: number): number => Math.floor(span / atom)
    const atomsFillingTheSpan = (atoms: number[]): number[] =>
      atoms.filter((atom) => labelCount(atom) >= MIN_LABELS_PER_AXIS)

    const notationAtoms =
      span < 1 ? this.computeSmallYLabelAtoms(span) : this.computeLargeYLabelAtoms(span)
    const fromNotation = atomsFillingTheSpan(notationAtoms)
    const candidates =
      fromNotation.length > 0 ? fromNotation : atomsFillingTheSpan(decimalAtoms(span))
    if (candidates.length === 0) {
      return span / MIN_LABELS_PER_AXIS
    }
    return candidates.reduce((best, atom) =>
      Math.abs(labelCount(atom) - targetNumberOfLabels) <
      Math.abs(labelCount(best) - targetNumberOfLabels)
        ? atom
        : best
    )
  }

  private renderLabelText(
    position: number,
    sharedUnit: Preformatted,
    spacing: number,
    signText: string
  ): string {
    const parts = this.postformat(
      this.preformat(position, sharedUnit.prefix, sharedUnit.symbol),
      position,
      spacing,
      this.useMaxDigitsForLabels
    )
    return signText + parts.join(' ')
  }

  public renderYLabels(yRange: YRange, targetNumberOfLabels: number): Label[] {
    if (targetNumberOfLabels < 0) {
      throw new Error('targetNumberOfLabels must be >= 0')
    }
    const [lowMagnitude, highMagnitude] =
      yRange.kind === 'positive' ? [yRange.start, yRange.end] : [-yRange.end, -yRange.start]
    const signText = yRange.kind === 'positive' ? '' : '-'
    const signNumber = yRange.kind === 'positive' ? 1 : -1

    const span = highMagnitude - lowMagnitude
    if (span <= 0 || targetNumberOfLabels === 0) {
      return []
    }

    const spacing = this.selectLabelSpacing(span, targetNumberOfLabels)
    const positions = multiplesWithin(lowMagnitude, highMagnitude, spacing)
    const sharedUnit = this.preformat(positions.find((position) => position !== 0) ?? spacing)[0]!

    return positions.map((position) =>
      position === 0
        ? { value: 0, text: '0' }
        : {
            value: signNumber * position,
            text: this.renderLabelText(position, sharedUnit, spacing, signText)
          }
    )
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
    return decimalAtoms(maxY)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    return decimalAtoms(maxY)
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
    return decimalAtoms(maxY)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    return decimalAtoms(maxY)
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
    return decimalAtoms(maxY)
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
    return decimalAtoms(maxY)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    return decimalAtoms(maxY)
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
    return decimalAtoms(maxY)
  }

  protected computeLargeYLabelAtoms(maxY: number): number[] {
    return decimalAtoms(maxY)
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
    return decimalAtoms(maxY)
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
