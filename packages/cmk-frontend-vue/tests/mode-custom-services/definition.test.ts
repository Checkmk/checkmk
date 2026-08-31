/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import { describe, expect, test } from 'vitest'

import {
  aggregationProblem,
  buildCustomServiceDefinition,
  configurationNameFor,
  slugForId
} from '@/mode-custom-services/definition'
import { type ServiceModel, emptyService } from '@/mode-custom-services/types'

type CompleteModel = ServiceModel & { metricName: string; hostName: string }

function model(overrides: Partial<CompleteModel> = {}): CompleteModel {
  return {
    ...emptyService(),
    metricName: 'otel.http.duration',
    serviceName: 'HTTP duration',
    hostName: 'web01',
    ...overrides
  }
}

describe('buildCustomServiceDefinition', () => {
  test('assigns the selected host explicitly', () => {
    expect(buildCustomServiceDefinition(model()).host_assignment).toEqual({
      mode: 'explicit_host',
      host_name: 'web01'
    })
  })

  test('carries the service name as the service name template', () => {
    expect(buildCustomServiceDefinition(model()).configuration.service_name_template).toBe(
      'HTTP duration'
    )
  })

  test('carries the selected metric', () => {
    expect(buildCustomServiceDefinition(model()).configuration.metric_name).toBe(
      'otel.http.duration'
    )
  })

  test('carries the attribute filter unchanged', () => {
    const attributeFilter: AttributeFilter = {
      type: 'equals',
      key: { kind: 'resource', name: 'service.name' },
      value: 'shop'
    }
    expect(
      buildCustomServiceDefinition(model({ attributeFilter })).configuration.attribute_filter
    ).toEqual(attributeFilter)
  })

  test('carries the lookback window of the consolidation', () => {
    const definition = buildCustomServiceDefinition(
      model({ consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 300 } })
    )
    expect(definition.configuration.consolidation.lookback_seconds).toBe(300)
  })

  test('omits the attribute filter when none is configured', () => {
    const { configuration } = buildCustomServiceDefinition(model({ attributeFilter: undefined }))
    expect('attribute_filter' in configuration).toBe(false)
  })

  test('carries a parameterless consolidation through unchanged', () => {
    const definition = buildCustomServiceDefinition(
      model({ consolidation: { type: 'sum', function: 'sum_rate', lookback_seconds: 120 } })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'sum',
      function: 'sum_rate',
      lookback_seconds: 120
    })
  })

  test('keeps the percentile of a histogram quantile', () => {
    const definition = buildCustomServiceDefinition(
      model({
        consolidation: {
          type: 'histogram',
          function: 'histogram_quantile',
          lookback_seconds: 120,
          percentile: 99
        }
      })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'histogram',
      function: 'histogram_quantile',
      lookback_seconds: 120,
      percentile: 99
    })
  })

  test('keeps both thresholds of a fraction between', () => {
    const definition = buildCustomServiceDefinition(
      model({
        consolidation: {
          type: 'histogram',
          function: 'histogram_fraction_between',
          lookback_seconds: 120,
          lower_threshold: 10,
          upper_threshold: 50
        }
      })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'histogram',
      function: 'histogram_fraction_between',
      lookback_seconds: 120,
      lower_threshold: 10,
      upper_threshold: 50
    })
  })

  test('keeps the group by keys of a preserving consolidation', () => {
    const definition = buildCustomServiceDefinition(
      model({
        consolidation: {
          type: 'histogram',
          function: 'histogram_preserve_quantile',
          lookback_seconds: 120,
          percentile: 95,
          group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
        }
      })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'histogram',
      function: 'histogram_preserve_quantile',
      lookback_seconds: 120,
      percentile: 95,
      group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
    })
  })

  test('keeps the threshold of a fraction below', () => {
    const definition = buildCustomServiceDefinition(
      model({
        consolidation: {
          type: 'histogram',
          function: 'histogram_fraction_below',
          lookback_seconds: 120,
          threshold: 0.25
        }
      })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'histogram',
      function: 'histogram_fraction_below',
      lookback_seconds: 120,
      threshold: 0.25
    })
  })

  test('keeps the threshold and group by of a preserving fraction below', () => {
    const definition = buildCustomServiceDefinition(
      model({
        consolidation: {
          type: 'histogram',
          function: 'histogram_preserve_fraction_below',
          lookback_seconds: 120,
          threshold: 0.5,
          group_by: [{ kind: 'data_point', key: 'pod' }]
        }
      })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'histogram',
      function: 'histogram_preserve_fraction_below',
      lookback_seconds: 120,
      threshold: 0.5,
      group_by: [{ kind: 'data_point', key: 'pod' }]
    })
  })

  test('keeps both thresholds and group by of a preserving fraction between', () => {
    const definition = buildCustomServiceDefinition(
      model({
        consolidation: {
          type: 'histogram',
          function: 'histogram_preserve_fraction_between',
          lookback_seconds: 120,
          lower_threshold: 1,
          upper_threshold: 9,
          group_by: [{ kind: 'scope', key: 'otel.library.name' }]
        }
      })
    )
    expect(definition.configuration.consolidation).toEqual({
      type: 'histogram',
      function: 'histogram_preserve_fraction_between',
      lookback_seconds: 120,
      lower_threshold: 1,
      upper_threshold: 9,
      group_by: [{ kind: 'scope', key: 'otel.library.name' }]
    })
  })

  test('derives the identifier from the service name and the host', () => {
    expect(buildCustomServiceDefinition(model()).configuration_name).toBe('http_duration_on_web01')
  })

  test('falls back to the metric when the service name yields no identifier', () => {
    const definition = buildCustomServiceDefinition(
      model({ serviceName: '\u5ef6\u8fdf\u6642\u9593' })
    )
    expect(definition.configuration_name).toBe('otel_http_duration_on_web01')
  })

  test('falls back to a constant when neither name yields an identifier', () => {
    const definition = buildCustomServiceDefinition(
      model({ serviceName: '\u5ef6\u8fdf', metricName: '\u5ef6\u8fdf' })
    )
    expect(definition.configuration_name).toBe('custom_service_on_web01')
  })

  test('gives the same service on two hosts distinct identifiers', () => {
    expect(buildCustomServiceDefinition(model({ hostName: 'web01' })).configuration_name).not.toBe(
      buildCustomServiceDefinition(model({ hostName: 'web02' })).configuration_name
    )
  })
})

describe('aggregationProblem', () => {
  test('reports a missing single threshold', () => {
    expect(
      aggregationProblem({
        type: 'histogram',
        function: 'histogram_fraction_below',
        lookback_seconds: 120
      } as ConsolidationFunction)
    ).toBe('thresholds_missing')
  })

  test('reports a partially filled threshold pair', () => {
    expect(
      aggregationProblem({
        type: 'histogram',
        function: 'histogram_fraction_between',
        lookback_seconds: 120,
        lower_threshold: 10
      } as ConsolidationFunction)
    ).toBe('thresholds_missing')
  })

  test('reports a pair the endpoint would reject', () => {
    expect(
      aggregationProblem({
        type: 'histogram',
        function: 'histogram_preserve_fraction_between',
        lookback_seconds: 120,
        lower_threshold: 50,
        upper_threshold: 10
      } as ConsolidationFunction)
    ).toBe('thresholds_out_of_order')
  })

  test('passes a complete pair', () => {
    expect(
      aggregationProblem({
        type: 'histogram',
        function: 'histogram_fraction_between',
        lookback_seconds: 120,
        lower_threshold: 10,
        upper_threshold: 50
      })
    ).toBeUndefined()
  })

  test('passes a consolidation that takes no thresholds', () => {
    expect(
      aggregationProblem({ type: 'gauge', function: 'gauge_last', lookback_seconds: 120 })
    ).toBeUndefined()
  })
})

describe('slugForId', () => {
  test.each([
    ['HTTP duration', 'http_duration'],
    ['otel.http.server.duration', 'otel_http_server_duration'],
    ['  Latency (p99)!  ', 'latency_p99'],
    ['already_fine', 'already_fine'],
    ['\u5ef6\u8fdf\u6642\u9593', ''],
    ['!!!', '']
  ])('turns %o into %o', (serviceName, expected) => {
    expect(slugForId(serviceName)).toBe(expected)
  })
})

describe('configurationNameFor', () => {
  test('scopes the identifier to the host', () => {
    expect(
      configurationNameFor({
        serviceName: 'HTTP duration',
        metricName: 'otel.http.duration',
        hostName: 'web-01.example.com'
      })
    ).toBe('http_duration_on_web_01_example_com')
  })
})
