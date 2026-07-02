/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  compactFunction,
  functionOptionLabel
} from '@/metric-backend/consolidation/consolidation-label'
import {
  CONSOLIDATION_CATALOG,
  type ConsolidationModel,
  type MetricType
} from '@/metric-backend/consolidation/types'

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
      model({
        type: 'histogram',
        function: 'fraction_below',
        params: { fractionBelowThreshold: 0.2 }
      })
    )
  ).toBe('fraction <0.2')
  expect(
    compactFunction(
      model({
        type: 'histogram',
        function: 'fraction_between',
        params: { fractionLowerThreshold: 0.1, fractionUpperThreshold: 0.9 }
      })
    )
  ).toBe('fraction 0.1–0.9')
})

test('functions marked as raw are rendered accordingly', () => {
  for (const [type, specs] of Object.entries(CONSOLIDATION_CATALOG) as [
    MetricType,
    (typeof CONSOLIDATION_CATALOG)[MetricType]
  ][]) {
    for (const spec of specs) {
      const label = functionOptionLabel(type, spec.fn, spec.raw)
      if (spec.raw) {
        expect(label).toMatch(/ \(raw\)$/)
      } else {
        expect(label).not.toMatch(/ \(raw\)$/)
      }
    }
  }
})
