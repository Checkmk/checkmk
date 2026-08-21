/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/graph_designer'
import type { paths } from 'cmk-shared-typing/typescript/openapi_internal'

import type { ServiceModel } from './types'

type CreateCustomServicePath = '/domain-types/custom_service/collections/all'

export type CustomServiceDefinition = NonNullable<
  paths[CreateCustomServicePath]['post']['requestBody']
>['content']['application/json']

type ApiConsolidation = NonNullable<CustomServiceDefinition['configuration']['consolidation']>

export type AggregationProblem = 'thresholds_missing' | 'thresholds_out_of_order'

export function aggregationProblem(
  consolidation: WireConsolidationFunction
): AggregationProblem | undefined {
  switch (consolidation.function) {
    case 'histogram_fraction_below':
    case 'histogram_preserve_fraction_below':
      return consolidation.threshold === undefined ? 'thresholds_missing' : undefined
    case 'histogram_fraction_between':
    case 'histogram_preserve_fraction_between': {
      const { lower_threshold: lower, upper_threshold: upper } = consolidation
      if (lower === undefined || upper === undefined) {
        return 'thresholds_missing'
      }
      return lower < upper ? undefined : 'thresholds_out_of_order'
    }
    default:
      return undefined
  }
}

function apiConsolidationFor(consolidation: WireConsolidationFunction): ApiConsolidation {
  switch (consolidation.function) {
    case 'histogram_quantile':
      return { type: 'histogram_quantile', percentile: consolidation.percentile }
    case 'histogram_fraction_below':
      return { type: 'histogram_fraction_below', threshold: consolidation.threshold ?? 0 }
    case 'histogram_fraction_between':
      return {
        type: 'histogram_fraction_between',
        lower_threshold: consolidation.lower_threshold ?? 0,
        upper_threshold: consolidation.upper_threshold ?? 100
      }
    case 'histogram_preserve_quantile':
      return {
        type: 'histogram_preserve_quantile',
        percentile: consolidation.percentile,
        group_by: consolidation.group_by ?? []
      }
    case 'histogram_preserve_fraction_below':
      return {
        type: 'histogram_preserve_fraction_below',
        threshold: consolidation.threshold ?? 0,
        group_by: consolidation.group_by ?? []
      }
    case 'histogram_preserve_fraction_between':
      return {
        type: 'histogram_preserve_fraction_between',
        lower_threshold: consolidation.lower_threshold ?? 0,
        upper_threshold: consolidation.upper_threshold ?? 100,
        group_by: consolidation.group_by ?? []
      }
    default:
      return { type: consolidation.function }
  }
}

export function configurationNameFor(serviceName: string): string {
  return serviceName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

export function buildCustomServiceDefinition(
  model: ServiceModel & { metricName: string; hostName: string }
): CustomServiceDefinition {
  return {
    configuration_name:
      configurationNameFor(model.serviceName) ||
      configurationNameFor(model.metricName) ||
      'custom_service',
    host_assignment: { mode: 'explicit_host', host_name: model.hostName },
    configuration: {
      metric_name: model.metricName,
      service_name_template: model.serviceName,
      ...(model.attributeFilter === undefined ? {} : { attribute_filter: model.attributeFilter }),
      consolidation: apiConsolidationFor(model.consolidation),
      consolidation_lookback: model.consolidation.lookback_seconds
    }
  }
}
