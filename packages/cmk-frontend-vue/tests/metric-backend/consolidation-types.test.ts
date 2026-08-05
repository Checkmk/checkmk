/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { consolidationFunctionFromName } from '@/metric-backend/consolidation/types'

test('resolves a persisted function name to its type/function pair', () => {
  expect(consolidationFunctionFromName('gauge_last')).toEqual({
    type: 'gauge',
    function: 'gauge_last'
  })
  expect(consolidationFunctionFromName('sum_rate')).toEqual({
    type: 'sum',
    function: 'sum_rate'
  })
  expect(consolidationFunctionFromName('histogram_fraction_between')).toEqual({
    type: 'histogram',
    function: 'histogram_fraction_between'
  })
})

test('an unknown function name resolves to null', () => {
  expect(consolidationFunctionFromName('does_not_exist')).toBeNull()
})
