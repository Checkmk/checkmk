/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CustomGraphOptions } from '@/graphing/designer/api'
import { yAxisUnitOf } from '@/graphing/designer/yAxisUnit'

function options(unit: CustomGraphOptions['unit']): CustomGraphOptions {
  return {
    unit,
    explicit_vertical_range: { type: 'auto' },
    omit_zero_metrics: false
  }
}

test('leaves the axis to the drawn metrics when no unit is configured', () => {
  expect(yAxisUnitOf(options({ type: 'first_entry_with_unit' }))).toBeNull()
})

test('maps a configured unit onto the axis, never converting the symbol', () => {
  const unit = yAxisUnitOf(
    options({
      type: 'custom',
      notation: { notation: 'iec', symbol: 'B' },
      precision: { type: 'strict', digits: 3 }
    })
  )
  expect(unit).toEqual({
    notation: 'iec',
    symbol: 'B',
    precision: { type: 'strict', digits: 3 },
    convertible: false
  })
})

test('labels a time unit in seconds, which is the only symbol it has', () => {
  const unit = yAxisUnitOf(
    options({
      type: 'custom',
      notation: { notation: 'time' },
      precision: { type: 'auto', digits: 2 }
    })
  )
  expect(unit).toEqual({
    notation: 'time',
    symbol: 's',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  })
})
