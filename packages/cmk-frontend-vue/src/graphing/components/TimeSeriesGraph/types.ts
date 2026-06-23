/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkTimeSeriesGraph, Size } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export type {
  GraphOptions,
  Size,
  UnitFormat,
  XAxis,
  YAxis
} from 'cmk-shared-typing/typescript/cmk_time_series_graph'

// The visible data (metrics, horizontal lines, resampled range) is produced by the graph data-fetch
// REST API, not the data-less render shell, so these mirror that endpoint's response models.
export type Metric = components['schemas']['ApiMetric']
export type MetricMetadata = components['schemas']['ApiMetricMetadata']
export type MetricRender = components['schemas']['ApiMetricRender']
export type HorizontalLine = components['schemas']['ApiHorizontalLine']
export type TimeRange = components['schemas']['ApiTimeRange']

export type ConsolidationFn = 'min' | 'max' | 'avg'
export type LineInterpolator = 'linear' | 'monotoneX' | 'basis'
export type SizeMode = Size['mode']

export interface TimeSeriesGraphProps extends Pick<CmkTimeSeriesGraph, 'size' | 'options'> {
  time_range: TimeRange
  metrics: Metric[]
  horizontal_lines: HorizontalLine[]
  consolidationFunction?: ConsolidationFn
  curveInterpolator?: LineInterpolator
}
