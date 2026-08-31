/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { staticAssertNever } from 'cmk-ui-library/lib/typeUtils'

type WireConsolidationFunction = components['schemas']['ConsolidationFunction']
type ConsolidationGroupByKey = components['schemas']['ConsolidationGroupByKey']

/** The designer's flat consolidation shape, converted to and from the nested wire only at the API boundary. */
export type DesignerConsolidationFunction =
  | {
      type:
        | 'gauge_last'
        | 'gauge_max'
        | 'gauge_avg'
        | 'gauge_min'
        | 'sum_rate'
        | 'sum_last_raw'
        | 'sum_delta'
        | 'histogram_count_delta'
        | 'histogram_count_rate'
        | 'histogram_sum_rate'
        | 'histogram_sum_delta'
        | 'histogram_sum_raw'
      lookback_seconds: number
    }
  | { type: 'histogram_quantile'; lookback_seconds: number; percentile: number }
  | { type: 'histogram_fraction_below'; lookback_seconds: number; threshold: number }
  | {
      type: 'histogram_fraction_between'
      lookback_seconds: number
      lower_threshold: number
      upper_threshold: number
    }
  | {
      type: 'histogram_preserve_quantile'
      lookback_seconds: number
      percentile: number
      group_by: ConsolidationGroupByKey[]
    }
  | {
      type: 'histogram_preserve_fraction_below'
      lookback_seconds: number
      threshold: number
      group_by: ConsolidationGroupByKey[]
    }
  | {
      type: 'histogram_preserve_fraction_between'
      lookback_seconds: number
      lower_threshold: number
      upper_threshold: number
      group_by: ConsolidationGroupByKey[]
    }

export function consolidationFromWire(
  wire: WireConsolidationFunction
): DesignerConsolidationFunction {
  const lookbackSeconds = wire.lookback_seconds
  switch (wire.type) {
    case 'gauge':
    case 'sum':
      return { type: wire.function, lookback_seconds: lookbackSeconds }
    case 'histogram':
      switch (wire.function) {
        case 'histogram_count_delta':
        case 'histogram_count_rate':
        case 'histogram_sum_rate':
        case 'histogram_sum_delta':
        case 'histogram_sum_raw':
          return { type: wire.function, lookback_seconds: lookbackSeconds }
        case 'histogram_quantile':
          return {
            type: 'histogram_quantile',
            lookback_seconds: lookbackSeconds,
            percentile: wire.percentile
          }
        case 'histogram_fraction_below':
          return {
            type: 'histogram_fraction_below',
            lookback_seconds: lookbackSeconds,
            threshold: wire.threshold
          }
        case 'histogram_fraction_between':
          return {
            type: 'histogram_fraction_between',
            lookback_seconds: lookbackSeconds,
            lower_threshold: wire.lower_threshold,
            upper_threshold: wire.upper_threshold
          }
        case 'histogram_preserve_quantile':
          return {
            type: 'histogram_preserve_quantile',
            lookback_seconds: lookbackSeconds,
            percentile: wire.percentile,
            group_by: wire.group_by
          }
        case 'histogram_preserve_fraction_below':
          return {
            type: 'histogram_preserve_fraction_below',
            lookback_seconds: lookbackSeconds,
            threshold: wire.threshold,
            group_by: wire.group_by
          }
        case 'histogram_preserve_fraction_between':
          return {
            type: 'histogram_preserve_fraction_between',
            lookback_seconds: lookbackSeconds,
            lower_threshold: wire.lower_threshold,
            upper_threshold: wire.upper_threshold,
            group_by: wire.group_by
          }
        default:
          staticAssertNever(wire)
          throw new Error('unhandled consolidation function')
      }
    default:
      staticAssertNever(wire)
      throw new Error('unhandled consolidation type')
  }
}

export function consolidationToWire(
  consolidation: DesignerConsolidationFunction
): WireConsolidationFunction {
  const lookbackSeconds = consolidation.lookback_seconds
  switch (consolidation.type) {
    case 'gauge_last':
    case 'gauge_max':
    case 'gauge_avg':
    case 'gauge_min':
      return { type: 'gauge', function: consolidation.type, lookback_seconds: lookbackSeconds }
    case 'sum_rate':
    case 'sum_last_raw':
    case 'sum_delta':
      return { type: 'sum', function: consolidation.type, lookback_seconds: lookbackSeconds }
    case 'histogram_count_delta':
    case 'histogram_count_rate':
    case 'histogram_sum_rate':
    case 'histogram_sum_delta':
    case 'histogram_sum_raw':
      return { type: 'histogram', function: consolidation.type, lookback_seconds: lookbackSeconds }
    case 'histogram_quantile':
      return {
        type: 'histogram',
        function: 'histogram_quantile',
        lookback_seconds: lookbackSeconds,
        percentile: consolidation.percentile
      }
    case 'histogram_fraction_below':
      return {
        type: 'histogram',
        function: 'histogram_fraction_below',
        lookback_seconds: lookbackSeconds,
        threshold: consolidation.threshold
      }
    case 'histogram_fraction_between':
      return {
        type: 'histogram',
        function: 'histogram_fraction_between',
        lookback_seconds: lookbackSeconds,
        lower_threshold: consolidation.lower_threshold,
        upper_threshold: consolidation.upper_threshold
      }
    case 'histogram_preserve_quantile':
      return {
        type: 'histogram',
        function: 'histogram_preserve_quantile',
        lookback_seconds: lookbackSeconds,
        percentile: consolidation.percentile,
        group_by: consolidation.group_by
      }
    case 'histogram_preserve_fraction_below':
      return {
        type: 'histogram',
        function: 'histogram_preserve_fraction_below',
        lookback_seconds: lookbackSeconds,
        threshold: consolidation.threshold,
        group_by: consolidation.group_by
      }
    case 'histogram_preserve_fraction_between':
      return {
        type: 'histogram',
        function: 'histogram_preserve_fraction_between',
        lookback_seconds: lookbackSeconds,
        lower_threshold: consolidation.lower_threshold,
        upper_threshold: consolidation.upper_threshold,
        group_by: consolidation.group_by
      }
    default:
      staticAssertNever(consolidation)
      throw new Error('unhandled consolidation')
  }
}
