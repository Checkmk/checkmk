/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import { staticAssertNever } from 'cmk-ui-library/lib/typeUtils'

import { catalogFunctionName } from '@/metric-backend/consolidation/types'
import type { ConsolidationFunction } from '@/metric-backend/consolidation/types'
import type { GroupByModel } from '@/metric-backend/group-by/types'
import {
  groupFractionBelowThresholdToWire,
  groupFractionLowerThresholdToWire,
  groupFractionUpperThresholdToWire,
  groupKeysToWire,
  groupPercentileToWire,
  percentileGroupBy
} from '@/metric-backend/group-by/wire'

export function consolidationFunctionFromWire(
  wire: WireConsolidationFunction
): ConsolidationFunction {
  switch (wire.type) {
    case 'gauge':
      return { type: 'gauge', function: wire.function }
    case 'sum':
      return { type: 'sum', function: wire.function }
    case 'histogram':
      // The picker holds the "preserve histograms" half, the group-by clause the other.
      return { type: 'histogram', function: catalogFunctionName(wire.function) }
    default:
      staticAssertNever(wire)
      throw new Error(`unhandled consolidation type: ${JSON.stringify(wire)}`)
  }
}

export function buildConsolidationFunction(
  consolidationFunction: ConsolidationFunction | null,
  lookbackSeconds: number,
  percentile: number,
  thresholdForFractionBelow: number,
  lowerThresholdForFractionBetween: number,
  upperThresholdForFractionBetween: number,
  groupBy: GroupByModel = percentileGroupBy()
): WireConsolidationFunction {
  switch (consolidationFunction?.function) {
    case 'gauge_max':
      return { type: 'gauge', function: 'gauge_max', lookback_seconds: lookbackSeconds }
    case 'gauge_avg':
      return { type: 'gauge', function: 'gauge_avg', lookback_seconds: lookbackSeconds }
    case 'gauge_min':
      return { type: 'gauge', function: 'gauge_min', lookback_seconds: lookbackSeconds }
    case 'sum_rate':
      return { type: 'sum', function: 'sum_rate', lookback_seconds: lookbackSeconds }
    case 'sum_last_raw':
      return { type: 'sum', function: 'sum_last_raw', lookback_seconds: lookbackSeconds }
    case 'sum_delta':
      return { type: 'sum', function: 'sum_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_quantile':
      return {
        type: 'histogram',
        function: 'histogram_quantile',
        lookback_seconds: lookbackSeconds,
        percentile
      }
    case 'histogram_count_delta':
      return {
        type: 'histogram',
        function: 'histogram_count_delta',
        lookback_seconds: lookbackSeconds
      }
    case 'histogram_count_rate':
      return {
        type: 'histogram',
        function: 'histogram_count_rate',
        lookback_seconds: lookbackSeconds
      }
    case 'histogram_sum_rate':
      return {
        type: 'histogram',
        function: 'histogram_sum_rate',
        lookback_seconds: lookbackSeconds
      }
    case 'histogram_sum_delta':
      return {
        type: 'histogram',
        function: 'histogram_sum_delta',
        lookback_seconds: lookbackSeconds
      }
    case 'histogram_sum_raw':
      return {
        type: 'histogram',
        function: 'histogram_sum_raw',
        lookback_seconds: lookbackSeconds
      }
    case 'histogram_fraction_below':
      return {
        type: 'histogram',
        function: 'histogram_fraction_below',
        lookback_seconds: lookbackSeconds,
        threshold: thresholdForFractionBelow
      }
    case 'histogram_fraction_between':
      return {
        type: 'histogram',
        function: 'histogram_fraction_between',
        lookback_seconds: lookbackSeconds,
        lower_threshold: lowerThresholdForFractionBetween,
        upper_threshold: upperThresholdForFractionBetween
      }
    case 'histogram_preserve':
      // "Preserve histograms" is only half a wire function: the group-by clause it is
      // paired with names the other half and owns that half's parameters.
      switch (groupBy.function) {
        case 'percentile':
          return {
            type: 'histogram',
            function: 'histogram_preserve_quantile',
            lookback_seconds: lookbackSeconds,
            percentile: groupPercentileToWire(groupBy),
            group_by: groupKeysToWire(groupBy.keys)
          }
        case 'fraction_below':
          return {
            type: 'histogram',
            function: 'histogram_preserve_fraction_below',
            lookback_seconds: lookbackSeconds,
            threshold: groupFractionBelowThresholdToWire(groupBy),
            group_by: groupKeysToWire(groupBy.keys)
          }
        case 'fraction_between':
          return {
            type: 'histogram',
            function: 'histogram_preserve_fraction_between',
            lookback_seconds: lookbackSeconds,
            lower_threshold: groupFractionLowerThresholdToWire(groupBy),
            upper_threshold: groupFractionUpperThresholdToWire(groupBy),
            group_by: groupKeysToWire(groupBy.keys)
          }
        default:
          throw new Error(`grouping without a "preserve histograms" pairing: ${groupBy.function}`)
      }
    case 'gauge_last':
    default:
      return { type: 'gauge', function: 'gauge_last', lookback_seconds: lookbackSeconds }
  }
}
