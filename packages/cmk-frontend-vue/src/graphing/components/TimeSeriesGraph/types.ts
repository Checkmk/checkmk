/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkTimeSeriesGraph, Size } from 'cmk-shared-typing/typescript/cmk_time_series_graph'

export type {
  GraphOptions,
  HorizontalLine,
  Metric,
  MetricMetadata,
  MetricRender,
  Size,
  TimeRange,
  UnitFormat,
  XAxis,
  YAxis
} from 'cmk-shared-typing/typescript/cmk_time_series_graph'

export type ConsolidationFn = 'min' | 'max' | 'avg'
export type LineInterpolator = 'linear' | 'monotoneX' | 'basis'
export type SizeMode = Size['mode']

export interface TimeSeriesGraphProps extends Pick<
  CmkTimeSeriesGraph,
  'metrics' | 'time_range' | 'size' | 'options' | 'horizontal_lines'
> {
  consolidationFunction?: ConsolidationFn
  curveInterpolator?: LineInterpolator
}
