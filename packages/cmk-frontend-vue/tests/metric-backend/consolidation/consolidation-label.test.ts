/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { compactFunction, functionLabel } from '@/metric-backend/consolidation/consolidation-label'
import type { ConsolidationModel } from '@/metric-backend/consolidation/types'

function model(
  partial: Partial<ConsolidationModel> & Pick<ConsolidationModel, 'type' | 'function'>
): ConsolidationModel {
  return { params: {}, lookbackSeconds: 300, ...partial }
}

test('quantile renders as a lowercase percentile token, keeping up to two decimals instead of rounding to p100', () => {
  expect(
    compactFunction(model({ type: 'histogram', function: 'quantile', params: { quantile: 0.5 } }))
  ).toBe('p50')
  expect(
    compactFunction(model({ type: 'histogram', function: 'quantile', params: { quantile: 0.999 } }))
  ).toBe('p99.9')
  expect(
    compactFunction(
      model({ type: 'histogram', function: 'quantile', params: { quantile: 0.9999 } })
    )
  ).toBe('p99.99')
})

test('fraction functions render their thresholds', () => {
  expect(
    compactFunction(
      model({ type: 'histogram', function: 'frac_below', params: { fracBelow: 0.2 } })
    )
  ).toBe('fraction <0.2')
  expect(
    compactFunction(
      model({
        type: 'histogram',
        function: 'frac_between',
        params: { fracLower: 0.1, fracUpper: 0.9 }
      })
    )
  ).toBe('fraction 0.1–0.9')
})

test('function labels differ per type for last_value', () => {
  expect(functionLabel('gauge', 'last_value')).toBe('Last recorded value')
  expect(functionLabel('sum', 'last_value')).toBe('Last recorded value (raw counter)')
  expect(functionLabel('histogram', 'last_value')).toBe('Cumulative sum field (raw)')
})
