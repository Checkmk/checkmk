/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import type { paths } from 'cmk-shared-typing/typescript/openapi_internal'

import type { ServiceModel } from './types'

type CreateCustomServicePath = '/domain-types/custom_service/collections/all'
type CustomServicePath = '/objects/custom_service/{configuration_name}'

export type CustomServiceDefinition = NonNullable<
  paths[CreateCustomServicePath]['post']['requestBody']
>['content']['application/json']

/** The body of an update: the same definition, minus the name that identifies it. */
export type CustomServiceUpdate = NonNullable<
  paths[CustomServicePath]['put']['requestBody']
>['content']['application/json']

export type CustomServiceExtensions =
  paths[CustomServicePath]['get']['responses'][200]['content']['application/json']['extensions']

const SERIES_ATTRIBUTES_MACRO = '$SERIES_ATTRIBUTES$'

const SERIES_ATTRIBUTES_SUFFIX = ` ${SERIES_ATTRIBUTES_MACRO}`

const ATTRIBUTE_KIND_ORDER = ['resource', 'scope', 'data_point'] as const

type AttributeKey = Aggregator['stages'][number]['aggregate_by'][number]

function preservedKeys(consolidation: WireConsolidationFunction): AttributeKey[] | null {
  switch (consolidation.function) {
    case 'histogram_preserve_quantile':
    case 'histogram_preserve_fraction_below':
    case 'histogram_preserve_fraction_between':
      return consolidation.group_by.map(({ kind, key }) => ({ kind, name: key }))
    default:
      return null
  }
}

// Mirrors template_attribute_scope: only the keys every grouping step groups by survive
export function appendedAttributeNames(
  consolidation: WireConsolidationFunction,
  aggregator: Aggregator | undefined
): string[] | null {
  let keys = preservedKeys(consolidation)
  for (const stage of aggregator?.stages ?? []) {
    const kept = keys
    keys =
      kept === null
        ? [...stage.aggregate_by]
        : stage.aggregate_by.filter((a) => kept.some((b) => a.kind === b.kind && a.name === b.name))
  }
  if (keys === null) {
    return null
  }
  return keys
    .sort(
      (a, b) =>
        ATTRIBUTE_KIND_ORDER.indexOf(a.kind) - ATTRIBUTE_KIND_ORDER.indexOf(b.kind) ||
        // By code unit like the check plugin, not locale-aware like localeCompare
        (a.name < b.name ? -1 : a.name > b.name ? 1 : 0)
    )
    .map((key) => key.name)
}

function serviceNameTemplate(model: ServiceModel): string {
  return model.appendSeriesAttributes
    ? `${model.serviceName.trim()}${SERIES_ATTRIBUTES_SUFFIX}`
    : model.serviceName
}

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

function customServiceBody(
  model: ServiceModel & { metricName: string; hostName: string }
): CustomServiceUpdate {
  return {
    host_assignment: { mode: 'explicit_host', host_name: model.hostName },
    configuration: {
      metric_name: model.metricName,
      service_name_template: serviceNameTemplate(model),
      ...(model.attributeFilter === undefined ? {} : { attribute_filter: model.attributeFilter }),
      consolidation: model.consolidation,
      ...(model.aggregator === undefined ? {} : { aggregator: model.aggregator })
    }
  }
}

export function buildCustomServiceDefinition(
  model: ServiceModel & { metricName: string; hostName: string }
): CustomServiceDefinition {
  return {
    configuration_name: model.configurationName,
    ...customServiceBody(model)
  }
}

export function buildCustomServiceUpdate(
  model: ServiceModel & { metricName: string; hostName: string }
): CustomServiceUpdate {
  return customServiceBody(model)
}

export function serviceModelFrom(
  configurationName: string,
  extensions: CustomServiceExtensions
): ServiceModel {
  const { host_assignment: assignment, configuration } = extensions
  // Any other template is kept verbatim, so that saving it does not rename its services
  const template = configuration.service_name_template
  const appendSeriesAttributes = template.endsWith(SERIES_ATTRIBUTES_SUFFIX)
  return {
    configurationName,
    metricName: configuration.metric_name,
    metricTypes: [],
    attributeFilter: configuration.attribute_filter,
    consolidation: configuration.consolidation,
    aggregator: configuration.aggregator,
    serviceName: appendSeriesAttributes
      ? template.slice(0, -SERIES_ATTRIBUTES_SUFFIX.length)
      : template,
    appendSeriesAttributes,
    hostName: assignment.mode === 'explicit_host' ? assignment.host_name : null
  }
}
