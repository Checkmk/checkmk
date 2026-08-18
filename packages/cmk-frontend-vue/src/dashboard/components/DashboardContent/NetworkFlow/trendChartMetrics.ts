/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NetworkFlowTrendChartContent } from '@/dashboard/types/widget.ts'
import type { Metric } from '@/graphing'

/**
 * The series values are throughput, rendered in the mockups' unit style
 * (3_200_000_000 → "3.20 Gbps"). One unit for every series, so it also drives
 * the value axis.
 */
const THROUGHPUT_UNIT: Metric['metadata']['unit'] = {
  notation: 'si',
  symbol: 'bps',
  precision: { type: 'strict', digits: 2 },
  convertible: false
}

/**
 * The renderer paints on a canvas, so the series colors have to be literals
 * rather than the CSS custom properties the other network flow widgets use.
 * These are the theme-independent `-50` palette entries, in the order the flow
 * monitoring mockups ask for (green first, then the cooler/warmer accents).
 */
const SERIES_COLORS = [
  '#15d1a0', // corporate green
  '#28a2f3', // light blue
  '#ffd703', // yellow
  '#ec48b6', // pink
  '#ff8400', // orange
  '#8380ff', // purple
  '#ed3b3b' // light red
]

/** One shared stack id stacks every series into cumulative bands. */
const STACK_ID = 'network-flow-trend'

export interface TrendChartSeries {
  name: string
  dataPoints: number[]
}

/**
 * The trend chart's series as the graph engine's metrics: palette colors cycled
 * by rank, and the display mode expressed as the stack every series shares -
 * no stack id at all draws them as separate lines instead.
 */
export function trendChartMetrics(
  series: TrendChartSeries[],
  displayMode: NetworkFlowTrendChartContent['display_mode']
): Metric[] {
  return series.map((item, index) => ({
    metadata: {
      name: item.name,
      title: item.name,
      unit: THROUGHPUT_UNIT,
      color: SERIES_COLORS[index % SERIES_COLORS.length]!
    },
    render: {
      stack: displayMode === 'stacked_area' ? STACK_ID : null,
      inverse: false,
      hidden: false
    },
    data_points: item.dataPoints
  }))
}
