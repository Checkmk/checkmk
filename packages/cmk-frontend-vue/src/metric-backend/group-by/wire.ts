/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { ConsolidationGroupByKey } from 'cmk-shared-typing/typescript/graph_designer'
import { randomId } from 'cmk-ui-library/lib/randomId'

import { DEFAULT_QUANTILE } from '../histogram-params'
import { type GroupByFunction, type GroupByModel, type GroupKey, isKeyValid } from './types'

/**
 * The "percentile by" clause a stored histogram_preserve_quantile describes, or a fresh
 * one when nothing is stored yet.
 *
 * Percentiles are stored 0 to 100, while the widget edits a 0 to 1 quantile.
 */
export function percentileGroupBy(stored?: {
  percentile: number
  group_by?: readonly ConsolidationGroupByKey[]
}): GroupByModel {
  return {
    function: 'percentile',
    params: { quantile: stored === undefined ? DEFAULT_QUANTILE : stored.percentile / 100 },
    keys: (stored?.group_by ?? []).map(({ kind, key }) => ({
      id: randomId(),
      attributeKind: kind,
      key
    }))
  }
}

export function groupPercentileToWire(groupBy: GroupByModel): number {
  return (groupBy.params.quantile ?? DEFAULT_QUANTILE) * 100
}

/**
 * The "fraction below by" clause a stored histogram_preserve_fraction_below describes,
 * or a fresh one when nothing is stored yet.
 */
export function fractionBelowGroupBy(stored?: {
  threshold: number
  group_by?: readonly ConsolidationGroupByKey[] | undefined
}): GroupByModel {
  return {
    function: 'fraction_below',
    params: stored === undefined ? {} : { fractionBelowThreshold: stored.threshold },
    keys: (stored?.group_by ?? []).map(({ kind, key }) => ({
      id: randomId(),
      attributeKind: kind,
      key
    }))
  }
}

export function groupFractionBelowThresholdToWire(groupBy: GroupByModel): number {
  return groupBy.params.fractionBelowThreshold ?? 0
}

/**
 * The "fraction between by" clause a stored histogram_preserve_fraction_between describes,
 * or a fresh one when nothing is stored yet.
 */
export function fractionBetweenGroupBy(stored?: {
  lower_threshold: number
  upper_threshold: number
  group_by?: readonly ConsolidationGroupByKey[] | undefined
}): GroupByModel {
  return {
    function: 'fraction_between',
    params:
      stored === undefined
        ? {}
        : {
            fractionLowerThreshold: stored.lower_threshold,
            fractionUpperThreshold: stored.upper_threshold
          },
    keys: (stored?.group_by ?? []).map(({ kind, key }) => ({
      id: randomId(),
      attributeKind: kind,
      key
    }))
  }
}

export function groupFractionLowerThresholdToWire(groupBy: GroupByModel): number {
  return groupBy.params.fractionLowerThreshold ?? 0
}

export function groupFractionUpperThresholdToWire(groupBy: GroupByModel): number {
  return groupBy.params.fractionUpperThreshold ?? 0
}

export function groupKeysToWire(keys: readonly GroupKey[]): ConsolidationGroupByKey[] {
  return keys.filter(isKeyValid).map(({ attributeKind, key }) => ({ kind: attributeKind, key }))
}

const SCALAR_FUNCTIONS = ['avg', 'min', 'max', 'sum', 'count'] as const
type ScalarFunction = (typeof SCALAR_FUNCTIONS)[number]

function isScalarFunction(fn: GroupByFunction): fn is ScalarFunction {
  return (SCALAR_FUNCTIONS as readonly string[]).includes(fn)
}

/** The aggregator a float grouping serializes to, or undefined when there is nothing to group. */
export function floatGroupByToAggregator(groupBy: GroupByModel): Aggregator | undefined {
  if (!isScalarFunction(groupBy.function)) {
    return undefined
  }
  const aggregateBy = groupBy.keys
    .filter(isKeyValid)
    .map(({ attributeKind, key }) => ({ kind: attributeKind, name: key }))
  // A scalar function without any valid key has nothing to group by, so it is no aggregator.
  if (aggregateBy.length === 0) {
    return undefined
  }
  return {
    stages: [
      { aggregate_by: aggregateBy, aggregation_fn: { type: 'scalar', name: groupBy.function } }
    ]
  }
}

/**
 * The float grouping a stored aggregator describes, or a "no grouping" model when absent.
 *
 * `newId` mints the widget-local key ids; injectable so tests can assert deterministic output.
 */
export function aggregatorToFloatGroupBy(
  aggregator: Aggregator | undefined,
  newId: () => string = randomId
): GroupByModel {
  const stage = aggregator?.stages[0]
  // Stored JSON is unvalidated here, so a non-scalar (histogram) stage must degrade to no grouping.
  if (stage === undefined || stage.aggregation_fn.type !== 'scalar') {
    return { function: 'none', params: {}, keys: [] }
  }
  return {
    function: stage.aggregation_fn.name,
    params: {},
    keys: stage.aggregate_by.map(({ kind, name }) => ({
      id: newId(),
      attributeKind: kind,
      key: name
    }))
  }
}
