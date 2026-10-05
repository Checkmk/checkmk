/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'

import { foldIntoBins } from '../../../utils/bins'
import type { Metric, TimeRange } from '../types'

const WIDE_BAR_PX = 12
const WIDE_BAR_GAP_PX = 4
const NARROW_BAR_PX = 4
const NARROW_BAR_GAP_PX = 1

/** One bin as drawn: the bar spans the value axis from `from` to `to`. */
export interface DrawnBar {
  start: number
  end: number
  value: number | null
  from: number
  to: number
}

export interface BarSeries {
  kind: 'bars'
  bars: DrawnBar[]
}

/**
 * The bar series of every bar metric, null for the others. Bars of one stack rest on the bars
 * below them in the same bin; a mirrored bar hangs below the baseline.
 */
export function composeBars(
  metrics: Metric[],
  dataTimeRange: TimeRange,
  binEdges: number[] | null
): (BarSeries | null)[] {
  const topOfStack = new Map<string, number[]>()
  return metrics.map((metric) => {
    const render = metric.render
    if (render.shape !== 'bar') {
      return null
    }
    if (binEdges === null) {
      throw new Error(`The bar metric ${metric.metadata.name} needs a bin unit.`)
    }
    const bins = foldIntoBins(metric.data_points, dataTimeRange, binEdges, render.aggregation)
    const bases =
      (render.stack === null ? undefined : topOfStack.get(render.stack)) ?? bins.map(() => 0)
    const tops = bins.map((bin, index) => bases[index]! + (bin.value ?? 0))
    if (render.stack !== null) {
      topOfStack.set(render.stack, tops)
    }
    const sign = render.inverse ? -1 : 1
    return {
      kind: 'bars',
      bars: bins.map((bin, index) => ({
        start: bin.start,
        end: bin.end,
        value: bin.value,
        from: sign * bases[index]!,
        to: sign * tops[index]!
      }))
    }
  })
}

function gapBeside(slotWidth: number): number {
  if (slotWidth >= WIDE_BAR_PX) {
    return WIDE_BAR_GAP_PX
  }
  return slotWidth >= NARROW_BAR_PX ? NARROW_BAR_GAP_PX : 0
}

export function drawBars(
  ctx: CanvasRenderingContext2D,
  series: BarSeries,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  color: string
): void {
  ctx.fillStyle = color
  for (const bar of series.bars) {
    if (bar.value === null || bar.from === bar.to) {
      continue
    }
    const left = xScale(new Date(bar.start * 1000))
    const right = xScale(new Date(bar.end * 1000))
    const gap = gapBeside(right - left)
    const top = Math.min(yScale(bar.from), yScale(bar.to))
    const bottom = Math.max(yScale(bar.from), yScale(bar.to))
    ctx.fillRect(left, top, Math.max(1, right - left - gap), bottom - top)
  }
}
