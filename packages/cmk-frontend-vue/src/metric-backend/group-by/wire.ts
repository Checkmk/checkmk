/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConsolidationGroupByKey } from 'cmk-shared-typing/typescript/graph_designer'
import { randomId } from 'cmk-ui-library/lib/randomId'

import { DEFAULT_QUANTILE } from '../histogram-params'
import { type GroupByFunction, type GroupByModel, type GroupKey, isKeyValid } from './types'

/**
 * The groupings "preserve histograms" can be paired with.
 *
 * Only "percentile by" has a fused wire consolidation, histogram_preserve_quantile.
 */
export const HISTOGRAM_PRESERVE_GROUP_BY_FUNCTIONS: readonly GroupByFunction[] = ['percentile']

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
    keys: (stored?.group_by ?? []).map(({ kind, key }) => ({ id: randomId(), level: kind, key }))
  }
}

export function groupPercentileToWire(groupBy: GroupByModel): number {
  return (groupBy.params.quantile ?? DEFAULT_QUANTILE) * 100
}

export function groupKeysToWire(keys: readonly GroupKey[]): ConsolidationGroupByKey[] {
  return keys.filter(isKeyValid).map(({ level, key }) => ({ kind: level, key }))
}
