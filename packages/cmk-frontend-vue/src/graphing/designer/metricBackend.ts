/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationGroupByKey } from 'cmk-shared-typing/typescript/consolidation'

import {
  DEFAULT_HISTOGRAM_PERCENTILE,
  DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
  DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
  DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN
} from '@/metric-backend/histogram-params'

import { DEFAULT_TITLE_MACRO, type MetricBackendItem } from './types'

/** One query of the `special_agents:custom_query_metric_backend` rule value. */
export interface MetricBackendRuleQuery {
  metric_name: string
  attribute_filter: AttributeFilter
  aggregation_lookback: number
  consolidation_function: MetricBackendItem['consolidation_function']['type']
  aggregation_histogram_group_by: ConsolidationGroupByKey[]
  aggregator: Aggregator | null
  aggregation_histogram_percentile: number
  aggregation_histogram_threshold_for_fraction_below: number
  aggregation_histogram_lower_threshold_for_fraction_between: number
  aggregation_histogram_upper_threshold_for_fraction_between: number
  service_name_template: string
}

/** The rule query prefilled from a designer row, with the row's title as the service name. */
export function metricBackendRuleQuery(
  item: MetricBackendItem,
  defaultTitle: string
): MetricBackendRuleQuery {
  const consolidation = item.consolidation_function
  return {
    metric_name: item.metric_name,
    attribute_filter: item.attribute_filter,
    aggregation_lookback: consolidation.lookback_seconds,
    consolidation_function: consolidation.type,
    aggregation_histogram_group_by: 'group_by' in consolidation ? consolidation.group_by : [],
    aggregator: item.aggregator ?? null,
    // Each API consolidation variant carries exactly the fields its function uses, so
    // field presence selects the right functions without a name list.
    aggregation_histogram_percentile:
      'percentile' in consolidation ? consolidation.percentile : DEFAULT_HISTOGRAM_PERCENTILE,
    aggregation_histogram_threshold_for_fraction_below:
      'threshold' in consolidation ? consolidation.threshold : DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
    aggregation_histogram_lower_threshold_for_fraction_between:
      'lower_threshold' in consolidation
        ? consolidation.lower_threshold
        : DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
    aggregation_histogram_upper_threshold_for_fraction_between:
      'upper_threshold' in consolidation
        ? consolidation.upper_threshold
        : DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN,
    service_name_template: item.title.replaceAll(DEFAULT_TITLE_MACRO, defaultTitle)
  }
}
