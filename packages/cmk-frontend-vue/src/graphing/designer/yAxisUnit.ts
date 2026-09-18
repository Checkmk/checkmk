/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UnitFormat } from '../components/TimeSeriesGraph'
import type { CustomGraphOptions } from './api'

/** The unit the preview labels its value axis in, or null to leave it to the drawn metrics. */
export function yAxisUnitOf(graphOptions: CustomGraphOptions): UnitFormat | null {
  const unit = graphOptions.unit
  if (unit.type === 'first_entry_with_unit') {
    return null
  }
  return {
    notation: unit.notation.notation,
    symbol: unit.notation.notation === 'time' ? 's' : unit.notation.symbol,
    precision: unit.precision,
    // A symbol the user typed is a label: a literal '°C' must not be converted as a temperature.
    convertible: false
  }
}
