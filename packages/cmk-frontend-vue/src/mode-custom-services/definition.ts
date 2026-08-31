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

export function slugForId(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

// The id has to be unique per site, and the backend rejects a duplicate. Creating the same service
// on a second host is ordinary, so the host is part of the id. A name without ASCII alphanumerics
// slugs to nothing, hence the fall back to the metric name.
export function configurationNameFor(
  model: Pick<ServiceModel, 'serviceName'> & { metricName: string; hostName: string }
): string {
  const name = slugForId(model.serviceName) || slugForId(model.metricName) || 'custom_service'
  const host = slugForId(model.hostName)
  return host === '' ? name : `${name}_on_${host}`
}

export function buildCustomServiceDefinition(
  model: ServiceModel & { metricName: string; hostName: string }
): CustomServiceDefinition {
  return {
    configuration_name: configurationNameFor(model),
    host_assignment: { mode: 'explicit_host', host_name: model.hostName },
    configuration: {
      metric_name: model.metricName,
      service_name_template: model.serviceName,
      ...(model.attributeFilter === undefined ? {} : { attribute_filter: model.attributeFilter }),
      consolidation: model.consolidation
    }
  }
}
