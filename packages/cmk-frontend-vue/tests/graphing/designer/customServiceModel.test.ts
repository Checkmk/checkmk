/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { customServiceModelFor } from '@/graphing/designer/telemetryMetrics'
import { DEFAULT_TITLE_MACRO } from '@/graphing/designer/types'

import { metricBackendItem } from './fixtures'

const DEFAULT_TITLE = '$METRIC_NAME$ - $SERIES_ID$'

test('the model carries over metric and filter', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', {
      metric_name: 'span.latency',
      attribute_filter: { type: 'exists', key: { kind: 'resource', name: 'service.name' } }
    }),
    DEFAULT_TITLE
  )

  expect(model.metricName).toBe('span.latency')
  expect(model.attributeFilter).toEqual({
    type: 'exists',
    key: { kind: 'resource', name: 'service.name' }
  })
  expect(model.hostName).toBeNull()
})

test('the row title becomes the service name, with the default title macro expanded', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', { title: `p95 of ${DEFAULT_TITLE_MACRO}` }),
    DEFAULT_TITLE
  )

  expect(model.serviceName).toBe('p95 of $METRIC_NAME$ - $SERIES_ID$')
})

test('a gauge consolidation maps to the gauge wire shape', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', {
      consolidation_function: { type: 'gauge_avg', lookback_seconds: 42 }
    }),
    DEFAULT_TITLE
  )

  expect(model.consolidation).toEqual({
    type: 'gauge',
    function: 'gauge_avg',
    lookback_seconds: 42
  })
})

test('a sum consolidation maps to the sum wire shape', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', {
      consolidation_function: { type: 'sum_rate', lookback_seconds: 300 }
    }),
    DEFAULT_TITLE
  )

  expect(model.consolidation).toEqual({
    type: 'sum',
    function: 'sum_rate',
    lookback_seconds: 300
  })
})

test('a histogram quantile keeps its percentile', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', {
      consolidation_function: {
        type: 'histogram_quantile',
        lookback_seconds: 300,
        percentile: 99
      }
    }),
    DEFAULT_TITLE
  )

  expect(model.consolidation).toEqual({
    type: 'histogram',
    function: 'histogram_quantile',
    lookback_seconds: 300,
    percentile: 99
  })
})

test('a histogram fraction function keeps its thresholds', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', {
      consolidation_function: {
        type: 'histogram_fraction_between',
        lookback_seconds: 300,
        lower_threshold: 1,
        upper_threshold: 3
      }
    }),
    DEFAULT_TITLE
  )

  expect(model.consolidation).toEqual({
    type: 'histogram',
    function: 'histogram_fraction_between',
    lookback_seconds: 300,
    lower_threshold: 1,
    upper_threshold: 3
  })
})

test('a preserve function keeps its group keys', () => {
  const model = customServiceModelFor(
    metricBackendItem('A', {
      consolidation_function: {
        type: 'histogram_preserve_fraction_below',
        lookback_seconds: 300,
        threshold: 2.5,
        group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
      }
    }),
    DEFAULT_TITLE
  )

  expect(model.consolidation).toEqual({
    type: 'histogram',
    function: 'histogram_preserve_fraction_below',
    lookback_seconds: 300,
    threshold: 2.5,
    group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
  })
})

test('the aggregator is carried over', () => {
  const aggregator = {
    stages: [
      {
        aggregate_by: [{ kind: 'resource' as const, name: 'service.name' }],
        aggregation_fn: { type: 'scalar' as const, name: 'avg' as const }
      }
    ]
  }
  const model = customServiceModelFor(metricBackendItem('A', { aggregator }), DEFAULT_TITLE)

  expect(model.aggregator).toEqual(aggregator)
})

test('an ungrouped line yields no aggregator', () => {
  const model = customServiceModelFor(metricBackendItem('A'), DEFAULT_TITLE)

  expect(model.aggregator).toBeUndefined()
})
