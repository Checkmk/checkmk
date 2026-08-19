/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkTimeSeriesGraph, Size } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import type { ConsolidationFn } from '../consolidation'
import type { ZoomMode } from './interaction/selection'

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

export type LineInterpolator = 'linear' | 'monotoneX' | 'basis'
export type SizeMode = Size['mode']

export type { ZoomMode }

export interface ValueRange {
  min: number
  max: number
}

export interface RequestedTimeRange {
  start: number
  end: number
}

export interface ZoomPayload {
  timeRange: TimeRange
  valueRange?: ValueRange
}

export interface PinPayload {
  time: number
}

export interface TimeSeriesGraphProps extends Pick<CmkTimeSeriesGraph, 'size' | 'options'> {
  view_time_range: TimeRange
  data_time_range?: TimeRange | undefined
  metrics: Metric[]
  horizontal_lines: HorizontalLine[]
  consolidationFunction?: ConsolidationFn
  curveInterpolator?: LineInterpolator
  valueRange: ValueRange | null
  zoomMode: ZoomMode
  minTimeRange: number | null
  minValueRange: number | null
  atMinTimeZoom?: boolean
  inspecting: boolean
  panEnabled: boolean
  zoomEnabled: boolean
  pinEnabled?: boolean
  highlightedMetricName: string | null
  pinTime?: number | null
}
