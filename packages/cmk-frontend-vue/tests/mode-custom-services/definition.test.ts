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
  buildCustomServiceUpdate,
  serviceModelFrom
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

  test('carries the aggregator unchanged', () => {
    const aggregator = {
      stages: [
        {
          aggregate_by: [{ kind: 'resource' as const, name: 'k8s.namespace.name' }],
          aggregation_fn: { type: 'scalar' as const, name: 'avg' as const }
        }
      ]
    }
    expect(buildCustomServiceDefinition(model({ aggregator })).configuration.aggregator).toEqual(
      aggregator
    )
  })

  test('omits the aggregator when none is configured', () => {
    const { configuration } = buildCustomServiceDefinition(model({ aggregator: undefined }))
    expect('aggregator' in configuration).toBe(false)
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

  test('uses the entered configuration name', () => {
    expect(
      buildCustomServiceDefinition(model({ configurationName: 'my_config' })).configuration_name
    ).toBe('my_config')
  })
})

describe('buildCustomServiceUpdate', () => {
  test('sends what create sends, without the name that identifies the service', () => {
    const { configuration_name: _name, ...rest } = buildCustomServiceDefinition(model())
    expect(buildCustomServiceUpdate(model())).toEqual(rest)
  })
})

describe('serviceModelFrom', () => {
  test('restores the model a definition was built from', () => {
    const attributeFilter: AttributeFilter = {
      type: 'equals',
      key: { kind: 'resource', name: 'service.name' },
      value: 'shop'
    }
    const original = model({
      attributeFilter,
      consolidation: { type: 'gauge', function: 'gauge_max', lookback_seconds: 300 }
    })

    expect(
      serviceModelFrom(original.configurationName, buildCustomServiceUpdate(original))
    ).toEqual(original)
  })

  test('restores a model without an attribute filter or an aggregator', () => {
    const original = model({ attributeFilter: undefined, aggregator: undefined })

    expect(
      serviceModelFrom(original.configurationName, buildCustomServiceUpdate(original))
    ).toEqual(original)
  })

  test('has no host to offer for a service assigned by host name template', () => {
    const restored = serviceModelFrom('http_duration_on_web01', {
      host_assignment: {
        mode: 'host_name_template',
        host_name_template: '$RESOURCE_ATTR.service.name$'
      },
      configuration: buildCustomServiceUpdate(model()).configuration
    })

    expect(restored.hostName).toBeNull()
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
