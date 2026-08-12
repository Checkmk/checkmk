/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { metricBackendRuleQuery } from '@/graphing/designer/metricBackend'
import { DEFAULT_TITLE_MACRO } from '@/graphing/designer/types'

import { metricBackendItem } from './fixtures'

const DEFAULT_TITLE = '$METRIC_NAME$ - $SERIES_ID$'

test('the query carries over metric, filter and lookback', () => {
  const item = metricBackendItem('A', {
    metric_name: 'span.latency',
    attribute_filter: { type: 'exists', key: { kind: 'resource', name: 'service.name' } },
    consolidation_function: { type: 'gauge_last', lookback_seconds: 42 }
  })

  const query = metricBackendRuleQuery(item, DEFAULT_TITLE)

  expect(query.metric_name).toBe('span.latency')
  expect(query.attribute_filter).toEqual({
    type: 'exists',
    key: { kind: 'resource', name: 'service.name' }
  })
  expect(query.aggregation_lookback).toBe(42)
})

test('the default title becomes the macros the rule understands', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', { title: DEFAULT_TITLE_MACRO }),
    DEFAULT_TITLE
  )

  expect(query.service_name_template).toBe('$METRIC_NAME$ - $SERIES_ID$')
})

test('a custom title is used as the service name template verbatim', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', { title: 'Latency $RESOURCE_ATTR.service.name$' }),
    DEFAULT_TITLE
  )

  expect(query.service_name_template).toBe('Latency $RESOURCE_ATTR.service.name$')
})

test('an embedded default title macro is expanded within a custom title', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', { title: `p95 of ${DEFAULT_TITLE_MACRO}` }),
    DEFAULT_TITLE
  )

  expect(query.service_name_template).toBe('p95 of $METRIC_NAME$ - $SERIES_ID$')
})

test('the consolidation function name is carried over', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', {
      consolidation_function: { type: 'sum_rate', lookback_seconds: 300 }
    }),
    DEFAULT_TITLE
  )

  expect(query.consolidation_function).toBe('sum_rate')
})

test('the quantile percentile is carried over', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', {
      consolidation_function: {
        type: 'histogram_quantile',
        lookback_seconds: 300,
        percentile: 99
      }
    }),
    DEFAULT_TITLE
  )

  expect(query.aggregation_histogram_percentile).toBe(99)
})

test('the fraction below threshold is carried over', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', {
      consolidation_function: {
        type: 'histogram_fraction_below',
        lookback_seconds: 300,
        threshold: 2.5
      }
    }),
    DEFAULT_TITLE
  )

  expect(query.aggregation_histogram_threshold_for_fraction_below).toBe(2.5)
})

test('the fraction between thresholds are carried over', () => {
  const query = metricBackendRuleQuery(
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

  expect(query.aggregation_histogram_lower_threshold_for_fraction_between).toBe(1)
  expect(query.aggregation_histogram_upper_threshold_for_fraction_between).toBe(3)
})

test('an ungrouped line carries no grouping', () => {
  const query = metricBackendRuleQuery(metricBackendItem('A'), DEFAULT_TITLE)

  expect(query.aggregation_histogram_group_by).toEqual([])
  expect(query.aggregator).toBeNull()
})

test('a preserve function carries its group keys and percentile', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', {
      consolidation_function: {
        type: 'histogram_preserve_quantile',
        lookback_seconds: 300,
        percentile: 99,
        group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
      }
    }),
    DEFAULT_TITLE
  )

  expect(query.consolidation_function).toBe('histogram_preserve_quantile')
  expect(query.aggregation_histogram_group_by).toEqual([{ kind: 'resource', key: 'k8s.pod.name' }])
  expect(query.aggregation_histogram_percentile).toBe(99)
})

test('the aggregator is carried over', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', {
      aggregator: {
        stages: [
          {
            aggregate_by: [{ kind: 'resource', name: 'service.name' }],
            aggregation_fn: { type: 'scalar', name: 'avg' }
          }
        ]
      }
    }),
    DEFAULT_TITLE
  )

  expect(query.aggregator).toEqual({
    stages: [
      {
        aggregate_by: [{ kind: 'resource', name: 'service.name' }],
        aggregation_fn: { type: 'scalar', name: 'avg' }
      }
    ]
  })
})

test('functions without thresholds fall back to the rule defaults', () => {
  const query = metricBackendRuleQuery(
    metricBackendItem('A', {
      consolidation_function: { type: 'sum_rate', lookback_seconds: 300 }
    }),
    DEFAULT_TITLE
  )

  expect(query.aggregation_histogram_percentile).toBe(90)
  expect(query.aggregation_histogram_threshold_for_fraction_below).toBe(0)
  expect(query.aggregation_histogram_lower_threshold_for_fraction_between).toBe(0)
  expect(query.aggregation_histogram_upper_threshold_for_fraction_between).toBe(100)
})
