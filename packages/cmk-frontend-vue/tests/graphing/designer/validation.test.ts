/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  newConstantDraft,
  newMetricBackendDraft,
  newRrdMetricDraft,
  newRrdQueryDraft,
  newScalarDraft
} from '@/graphing/designer/drafts'
import { isValid, validateDesign, validateRow } from '@/graphing/designer/validation'

import {
  constantItem,
  formulaItem,
  items,
  metricBackendItem,
  rrdMetricItem,
  rrdQueryItem,
  scalarItem
} from './fixtures'

describe('validateRow', () => {
  test('a fresh RRD metric draft is missing host, service and metric', () => {
    expect(validateRow(newRrdMetricDraft('A', '#123456'))).toEqual([
      { id: 'A', field: 'host_name', code: 'required' },
      { id: 'A', field: 'service_name', code: 'required' },
      { id: 'A', field: 'metric_name', code: 'required' }
    ])
  })

  test('a fresh scalar draft is missing host, service and metric', () => {
    expect(validateRow(newScalarDraft('A', '#123456'))).toEqual([
      { id: 'A', field: 'host_name', code: 'required' },
      { id: 'A', field: 'service_name', code: 'required' },
      { id: 'A', field: 'metric_name', code: 'required' }
    ])
  })

  test('a query and a metric backend source only need a metric', () => {
    expect(validateRow(newRrdQueryDraft('A'))).toEqual([
      { id: 'A', field: 'metric_name', code: 'required' }
    ])
    expect(validateRow(newMetricBackendDraft('B'))).toEqual([
      { id: 'B', field: 'metric_name', code: 'required' }
    ])
  })

  test('a blank metric name is as missing as an unset one', () => {
    expect(validateRow(rrdMetricItem('A', { metric_name: '  ' }))).toEqual([
      { id: 'A', field: 'metric_name', code: 'required' }
    ])
  })

  test('a constant needs a value, and a cleared input counts as unset', () => {
    expect(validateRow(newConstantDraft('A', '#123456'))).toEqual([
      { id: 'A', field: 'value', code: 'required' }
    ])
    expect(validateRow(constantItem('A', { value: Number.NaN }))).toEqual([
      { id: 'A', field: 'value', code: 'required' }
    ])
    expect(validateRow(constantItem('A', { value: 0 }))).toEqual([])
  })

  test('an infinite constant is reported apart from a missing one', () => {
    expect(validateRow(constantItem('A', { value: Number.POSITIVE_INFINITY }))).toEqual([
      { id: 'A', field: 'value', code: 'not-finite' }
    ])
  })

  test('a blank title blocks the save', () => {
    expect(validateRow(rrdMetricItem('A', { title: '   ' }))).toEqual([
      { id: 'A', field: 'title', code: 'required' }
    ])
  })

  test('a blank title also disqualifies a formula, whose fields are otherwise always set', () => {
    expect(validateRow(formulaItem('A', { title: '' }))).toEqual([
      { id: 'A', field: 'title', code: 'required' }
    ])
  })

  test('a sub-second lookback is out of range', () => {
    const consolidation = { type: 'gauge_last', lookback_seconds: 0 } as const
    expect(validateRow(metricBackendItem('A', { consolidation_function: consolidation }))).toEqual([
      { id: 'A', field: 'consolidation_function', code: 'lookback-too-small' }
    ])
  })

  test('a percentile outside 0 to 100 is out of range', () => {
    const consolidation = {
      type: 'histogram_quantile',
      lookback_seconds: 300,
      percentile: 500
    } as const
    expect(validateRow(metricBackendItem('A', { consolidation_function: consolidation }))).toEqual([
      { id: 'A', field: 'consolidation_function', code: 'percentile-out-of-range' }
    ])
  })

  test('a cleared fraction-below threshold is not a number', () => {
    const consolidation = {
      type: 'histogram_fraction_below',
      lookback_seconds: 300,
      threshold: Number.NaN
    } as const
    expect(validateRow(metricBackendItem('A', { consolidation_function: consolidation }))).toEqual([
      { id: 'A', field: 'consolidation_function', code: 'not-finite' }
    ])
  })

  test('fraction-between thresholds must be ordered', () => {
    const consolidation = {
      type: 'histogram_fraction_between',
      lookback_seconds: 300,
      lower_threshold: 5,
      upper_threshold: 5
    } as const
    expect(validateRow(metricBackendItem('A', { consolidation_function: consolidation }))).toEqual([
      { id: 'A', field: 'consolidation_function', code: 'thresholds-unordered' }
    ])
  })

  test('the formula rules that span sources are not a source rule', () => {
    expect(validateRow(formulaItem('D', { ast: { op: 'ref', id: 'nope' } }))).toEqual([])
  })
})

describe('isValid', () => {
  test('wire items are accepted, whatever their type', () => {
    for (const item of [
      rrdMetricItem('A'),
      rrdQueryItem('B'),
      metricBackendItem('C'),
      constantItem('D'),
      formulaItem('E'),
      scalarItem('F')
    ]) {
      expect(isValid(item)).toBe(true)
    }
  })

  test('a source the rules reject is not accepted, however filled in', () => {
    const consolidation = {
      type: 'histogram_quantile',
      lookback_seconds: 300,
      percentile: 500
    } as const
    expect(isValid(metricBackendItem('A', { consolidation_function: consolidation }))).toBe(false)
    expect(isValid(newRrdMetricDraft('B', '#123456'))).toBe(false)
  })
})

describe('validateDesign', () => {
  test('a graph with no sources is valid', () => {
    expect(validateDesign([])).toEqual([])
  })

  test('a fully configured graph has nothing blocking it', () => {
    expect(validateDesign(items)).toEqual([])
  })

  test('a formula pointing at a source that is still being filled in', () => {
    const design = [newRrdMetricDraft('A', '#123456'), formulaItem('D')]

    expect(validateDesign(design)).toContainEqual({
      id: 'D',
      field: 'ast',
      code: 'ref-incomplete',
      ref: 'A'
    })
  })

  test('a bare reference to a dynamic query needs consolidating', () => {
    const design = [rrdQueryItem('C'), formulaItem('D', { ast: { op: 'ref', id: 'C' } })]

    expect(validateDesign(design)).toEqual([
      { id: 'D', field: 'ast', code: 'needs-consolidation', ref: 'C' }
    ])
  })

  test('a reference to no source at all stays unknown', () => {
    const design = [rrdMetricItem('A'), formulaItem('D', { ast: { op: 'ref', id: 'Z' } })]

    expect(validateDesign(design)).toEqual([
      { id: 'D', field: 'ast', code: 'unknown-ref', ref: 'Z' }
    ])
  })

  test('a formula cannot reference itself', () => {
    const design = [formulaItem('D', { ast: { op: 'ref', id: 'D' } })]

    expect(validateDesign(design)).toEqual([{ id: 'D', field: 'ast', code: 'self-ref', ref: 'D' }])
  })

  test('formulas cannot form a cycle', () => {
    const design = [
      formulaItem('D', { ast: { op: 'ref', id: 'F' } }),
      formulaItem('F', { ast: { op: 'ref', id: 'D' } })
    ]

    expect(validateDesign(design)).toContainEqual({
      id: 'D',
      field: 'ast',
      code: 'cyclic-ref',
      ref: 'F'
    })
  })

  test('an RRD formula cannot reach into the metrics backend', () => {
    const design = [metricBackendItem('E'), formulaItem('D', { ast: { op: 'ref', id: 'E' } })]

    expect(validateDesign(design)).toEqual([
      { id: 'D', field: 'ast', code: 'domain-mismatch', ref: 'E' }
    ])
  })

  test('each source contributes its own blockers', () => {
    const design = [newRrdQueryDraft('A'), newConstantDraft('B', '#123456')]

    expect(validateDesign(design)).toEqual([
      { id: 'A', field: 'metric_name', code: 'required' },
      { id: 'B', field: 'value', code: 'required' }
    ])
  })
})
