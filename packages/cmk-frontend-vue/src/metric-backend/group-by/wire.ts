/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { ConsolidationGroupByKey } from 'cmk-shared-typing/typescript/consolidation'
import { randomId } from 'cmk-ui-library/lib/randomId'

import { DEFAULT_QUANTILE } from '../histogram-params'
import {
  type AggregationStep,
  type GroupByModel,
  type GroupKey,
  type ScalarFunction,
  isKeyValid,
  isScalarFunction
} from './types'

type AggregationStage = Aggregator['stages'][number]

// Empty keys are kept as an "aggregate everything" stage (aggregate_by: []), not dropped.
function scalarStage(fn: ScalarFunction, keys: readonly GroupKey[]): AggregationStage {
  return {
    aggregate_by: keys
      .filter(isKeyValid)
      .map(({ attributeKind, attributeKey }) => ({ kind: attributeKind, name: attributeKey })),
    aggregation_fn: { type: 'scalar', name: fn }
  }
}

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
      attributeKey: key
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
      attributeKey: key
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
      attributeKey: key
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
  return keys
    .filter(isKeyValid)
    .map(({ attributeKind, attributeKey }) => ({ kind: attributeKind, key: attributeKey }))
}

/** The aggregator a float grouping serializes to, or undefined for a non-scalar ("no grouping"). */
export function floatGroupByToAggregator(groupBy: GroupByModel): Aggregator | undefined {
  return aggregatorFromGroupBy(groupBy, [])
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
      attributeKey: name
    }))
  }
}

/**
 * The aggregator a grouping and its then steps serialize to, or absent when empty. Only a scalar
 * float grouping leads with its own stage; a histogram group-by rides the consolidation instead.
 */
export function aggregatorFromGroupBy(
  groupBy: GroupByModel,
  thenSteps: readonly AggregationStep[]
): Aggregator | undefined {
  if (groupBy.function === 'none') {
    return undefined
  }
  const stages = [
    ...(isScalarFunction(groupBy.function) ? [scalarStage(groupBy.function, groupBy.keys)] : []),
    ...thenSteps.map((step) => scalarStage(step.function, step.keys))
  ]
  return stages.length === 0 ? undefined : { stages }
}

/**
 * The then steps a stored aggregator holds: its stages past the main group-by, which owns the first
 * stage only for a scalar float grouping. `newId` mints widget-local ids, injectable for tests.
 */
export function aggregatorToThenSteps(
  aggregator: Aggregator | undefined,
  groupBy: GroupByModel,
  newId: () => string = randomId
): AggregationStep[] {
  const mainGroupByStages = isScalarFunction(groupBy.function) ? 1 : 0
  const steps: AggregationStep[] = []
  for (const stage of (aggregator?.stages ?? []).slice(mainGroupByStages)) {
    if (stage.aggregation_fn.type !== 'scalar') {
      break
    }
    steps.push({
      id: newId(),
      function: stage.aggregation_fn.name,
      keys: stage.aggregate_by.map(({ kind, name }) => ({
        id: newId(),
        attributeKind: kind,
        attributeKey: name
      }))
    })
  }
  return steps
}
