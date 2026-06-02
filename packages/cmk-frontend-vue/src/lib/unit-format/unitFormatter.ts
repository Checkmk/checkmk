/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Canonical frontend implementation of the unit/format pipeline. The legacy
// cmk/gui/graphing/_unit.py:user_specific_unit equivalent is on a
// deprecation path — once all callers have moved to the Vue stack the
// Python code is removed and this file is the single source of truth.
//
// The exported `UnitFormat` type is the canonical wire format; the backend
// (Pydantic) is expected to serialize unit specifications into this shape.
//
// Auto-conversion only applies to temperature symbols (°C / °F). Every
// other notation/symbol combination renders the raw value as-is.
//
// Example:
//   const { formatter, convert } = userSpecificUnit(
//     { notation: 'si', symbol: 'B', precision: { type: 'auto', digits: 2 } },
//     'celsius'
//   )
//   formatter.render(convert(rawBytes))   // → "12.34 kB"
import type { UnitFormat } from 'cmk-shared-typing/typescript/unit_format'

import {
  DecimalFormatter,
  EngineeringScientificFormatter,
  IECFormatter,
  type NotationFormatter,
  type Precision,
  SIFormatter,
  StandardScientificFormatter,
  TimeFormatter
} from '@/lib/unit-format/notationFormatter'

// `UnitFormat` is generated from packages/cmk-shared-typing/source/unit_format.json
// (the canonical wire format the backend serializes into). Re-exported here so the
// existing `@/lib/unit-format/unitFormatter` import sites stay unchanged.
export type { UnitFormat }

export type TemperatureUnit = 'celsius' | 'fahrenheit'

export type UserSpecificUnit = {
  formatter: NotationFormatter
  convert: (rawValue: number) => number
}

type Conversion = {
  symbol: string
  converter: (value: number) => number
}

function celsiusConversion(target: TemperatureUnit): Conversion {
  if (target === 'celsius') {
    return { symbol: '°C', converter: (c) => c }
  }
  if (target === 'fahrenheit') {
    return { symbol: '°F', converter: (c) => c * 1.8 + 32 }
  }
  const _exhaustive: never = target
  throw new Error(`unhandled temperature unit: ${String(_exhaustive)}`)
}

function fahrenheitConversion(target: TemperatureUnit): Conversion {
  if (target === 'celsius') {
    return { symbol: '°C', converter: (f) => (f - 32) / 1.8 }
  }
  if (target === 'fahrenheit') {
    return { symbol: '°F', converter: (f) => f }
  }
  const _exhaustive: never = target
  throw new Error(`unhandled temperature unit: ${String(_exhaustive)}`)
}

const TEMPERATURE_CONVERSION: Record<string, (target: TemperatureUnit) => Conversion> = {
  '°C': celsiusConversion,
  '°F': fahrenheitConversion
}

function makeFormatter(
  notation: UnitFormat['notation'],
  symbol: string,
  precision: Precision
): NotationFormatter {
  switch (notation) {
    case 'decimal':
      return new DecimalFormatter(symbol, precision)
    case 'si':
      return new SIFormatter(symbol, precision)
    case 'iec':
      return new IECFormatter(symbol, precision)
    case 'standard_scientific':
      return new StandardScientificFormatter(symbol, precision)
    case 'engineering_scientific':
      return new EngineeringScientificFormatter(symbol, precision)
    case 'time':
      return new TimeFormatter(symbol, precision)
    default: {
      const _exhaustive: never = notation
      throw new Error(`unhandled notation: ${String(_exhaustive)}`)
    }
  }
}

export function userSpecificUnit(
  spec: UnitFormat,
  temperatureUnit: TemperatureUnit
): UserSpecificUnit {
  const convertible = spec.convertible ?? true
  // Use Object.hasOwn to avoid resolving inherited prototype properties like
  // `toString` or `constructor` — those are NOT temperature symbols and would
  // otherwise pass through `in` and crash the converter call.
  const factory = Object.hasOwn(TEMPERATURE_CONVERSION, spec.symbol)
    ? TEMPERATURE_CONVERSION[spec.symbol]
    : undefined
  const conversion: Conversion =
    convertible && factory ? factory(temperatureUnit) : { symbol: spec.symbol, converter: (v) => v }

  return {
    formatter: makeFormatter(spec.notation, conversion.symbol, spec.precision),
    convert: conversion.converter
  }
}
