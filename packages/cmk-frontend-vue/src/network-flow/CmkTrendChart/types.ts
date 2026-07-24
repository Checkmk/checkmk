/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ChartColor } from '../colors'

/** Whether the series are drawn as separate lines or as cumulative stacked areas. */
export type TrendChartDisplayMode = 'lines' | 'stacked_area'

export interface TrendChartSeries {
  /** Series label, e.g. "HTTP" or "AS15169". */
  name: string
  /** Per-minute values over the displayed window, oldest first. */
  dataPoints: number[]
  /** Smallest per-minute value; shown in the legend. */
  minimum: number
  /** Largest per-minute value; shown in the legend. */
  maximum: number
  /** Mean per-minute value; shown in the legend. */
  average: number
  /** Most recent per-minute value; shown in the legend. */
  last: number
}

/** A series with its resolved (index-assigned) palette color for plot and legend. */
export interface TrendChartSeriesWithColor extends TrendChartSeries {
  color: ChartColor
}

export interface CmkTrendChartProps {
  /** The series to plot, already ranked (they keep this order in the stack and legend). */
  series: TrendChartSeries[]
  /** Line or stacked-area rendering. */
  displayMode: TrendChartDisplayMode
  /**
   * Formats a value for the y-axis ticks and the legend statistics, e.g. a
   * throughput formatter rendering 3_200_000_000 as "3.20 Gbps".
   */
  formatValue: (value: number) => string
  /** When true, legend series names render as buttons emitting `seriesClick`. */
  clickableSeries?: boolean
}

// The per-series palette, cycled by series index. Ordered to match the flow
// monitoring mockups (green first, then the cooler/warmer accents).
export const TREND_SERIES_PALETTE: ChartColor[] = [
  'green',
  'blue',
  'yellow',
  'magenta',
  'orange',
  'purple',
  'red'
]
