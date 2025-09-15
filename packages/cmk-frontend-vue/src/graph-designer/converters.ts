/**
 * Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type GraphOptionExplicitVerticalRangeBoundaries,
  type GraphOptionUnitCustom,
  type GraphOptionUnitCustomNotation,
  type GraphOptionUnitCustomNotationWithSymbol,
  type GraphOptionUnitCustomPrecision
} from 'cmk-shared-typing/typescript/graph_designer'

type UnitFirstEntryWithUnit = ['first_entry_with_unit', null]
type UnitCustomNotationTime = ['time', null]
type UnitCustomNotationWithSymbol = [
  'decimal' | 'si' | 'iec' | 'standard_scientific' | 'engineering_scientific',
  string
]
interface UnitCustomNotationAndPrecision {
  notation: UnitCustomNotationTime | UnitCustomNotationWithSymbol
  precision: GraphOptionUnitCustomPrecision
}
type UnitCustom = ['custom', UnitCustomNotationAndPrecision]

function convertToNotation(
  notation: GraphOptionUnitCustomNotation
): UnitCustomNotationTime | UnitCustomNotationWithSymbol {
  if (notation === 'time') {
    return ['time', null]
  } else {
    return [notation.type, notation.symbol]
  }
}

export function convertToUnit(
  unit: 'first_entry_with_unit' | GraphOptionUnitCustom
): UnitFirstEntryWithUnit | UnitCustom {
  // Returns:
  // [ "first_entry_with_unit", null ]
  // [ "custom", { "notation": [ "time", null ], "precision": { "type": "<MODE>", "digits": <INTEGER> } } ]
  // [ "custom", { "notation": [ "<TYPE>", "<SYMBOL>" ], "precision": { "type": "<MODE>", "digits": <INTEGER> } } ]
  if (unit === 'first_entry_with_unit') {
    return ['first_entry_with_unit', null]
  } else {
    return [
      'custom',
      {
        notation: convertToNotation(unit.notation),
        precision: { type: unit.precision.type, digits: unit.precision.digits }
      }
    ]
  }
}

export function convertFromUnit(
  unit: UnitFirstEntryWithUnit | UnitCustom
): 'first_entry_with_unit' | GraphOptionUnitCustom {
  if (unit[0] === 'first_entry_with_unit') {
    return 'first_entry_with_unit'
  }
  const unitNotation = unit[1].notation
  const unitPrecision = unit[1].precision
  if (unitNotation[0] === 'time') {
    return {
      notation: 'time',
      precision: unitPrecision
    }
  }
  return {
    notation: {
      type: unitNotation[0],
      symbol: unitNotation[1]
    },
    precision: unitPrecision
  }
}

type ExplicitVerticalRangeAuto = ['auto', null]
type ExplicitVerticalRangeExplicit = ['explicit', GraphOptionExplicitVerticalRangeBoundaries]

export function convertToExplicitVerticalRange(
  explicitVerticalRange: 'auto' | GraphOptionExplicitVerticalRangeBoundaries
): ExplicitVerticalRangeAuto | ExplicitVerticalRangeExplicit {
  // Returns:
  //  [ "auto", null ]
  //  [ "explicit", { "lower": <NUMBER>, "upper": <NUMBER> } ]
  if (explicitVerticalRange === 'auto') {
    return ['auto', null]
  } else {
    return ['explicit', { lower: explicitVerticalRange.lower, upper: explicitVerticalRange.upper }]
  }
}

export function convertFromExplicitVerticalRange(
  explicitVerticalRange: ExplicitVerticalRangeAuto | ExplicitVerticalRangeExplicit
) {
  const explicitVerticalRangeBoundaries = explicitVerticalRange[1]
  if (explicitVerticalRange[0] === 'auto' || explicitVerticalRangeBoundaries === null) {
    return 'auto'
  } else {
    return explicitVerticalRangeBoundaries
  }
}

export function extractExplicitVerticalRangeBounds(
  explicitVerticalRange: 'auto' | { lower: number; upper: number }
): { lower: number | null; upper: number | null } {
  if (
    explicitVerticalRange === 'auto' ||
    explicitVerticalRange === null ||
    typeof explicitVerticalRange !== 'object'
  ) {
    return { lower: null, upper: null }
  }
  return {
    lower: explicitVerticalRange.lower ?? null,
    upper: explicitVerticalRange.upper ?? null
  }
}

export function extractUnitFields(unit: 'first_entry_with_unit' | GraphOptionUnitCustom): {
  unitType: string
  notation: GraphOptionUnitCustomNotationWithSymbol['type'] | 'time'
  symbol: string
  precisionType: GraphOptionUnitCustomPrecision['type']
  precisionDigits: number
} {
  if (unit === 'first_entry_with_unit') {
    return {
      unitType: 'first_entry_with_unit',
      notation: 'decimal',
      symbol: '',
      precisionType: 'auto',
      precisionDigits: 2
    }
  }
  if (unit.notation === 'time') {
    return {
      unitType: 'custom',
      notation: 'time',
      symbol: '',
      precisionType: unit.precision.type,
      precisionDigits: unit.precision.digits
    }
  }
  return {
    unitType: 'custom',
    notation: unit.notation.type,
    symbol: unit.notation.symbol,
    precisionType: unit.precision.type,
    precisionDigits: unit.precision.digits
  }
}
