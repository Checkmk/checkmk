/**
 * Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {
  type GraphOptionUnitCustom,
  type GraphOptionUnitCustomNotation,
  type GraphOptionExplicitVerticalRangeBoundaries
} from 'cmk-shared-typing/typescript/graph_designer'

function convertToNotation(notation: GraphOptionUnitCustomNotation) {
  if (notation === 'time') {
    return ['time', null]
  } else {
    return [notation.type, notation.symbol]
  }
}

export function convertToUnit(unit: 'first_entry_with_unit' | GraphOptionUnitCustom) {
  // [ "first_entry_with_unit", null ]
  // [ "custom", { "notation": [ "<TYPE>", "<SYMBOL>" ], "precision": { "type": "<MODE>", "digits": <INTEGER> } } ]
  // [ "custom", { "notation": [ "time", null ], "precision": { "type": "<MODE>", "digits": <INTEGER> } } ]
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

export function convertToExplicitVerticalRange(
  explicitVerticalRange: 'auto' | GraphOptionExplicitVerticalRangeBoundaries
) {
  //  [ "auto", null ]
  //  [ "explicit", { "lower": <NUMBER>, "upper": <NUMBER> } ]
  if (explicitVerticalRange === 'auto') {
    return ['auto', null]
  } else {
    return ['explicit', { lower: explicitVerticalRange.lower, upper: explicitVerticalRange.upper }]
  }
}
