/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'

import type { ConsolidationFn } from '../../consolidation'
import type { M4Bucket } from '../decimation/types'
import type { Metric } from '../types'
import { bucketAnchorTime, selectConsolidatedValue } from './bucket'

export interface StackedBand {
  lower: number
  upper: number
  gap: boolean
  startTime: number
  endTime: number
  /** Where the band is drawn: the bucket's own anchor, which every layer of a stack agrees on. */
  anchorTime: number
}

export type StackedSeriesKind = 'line' | 'area-stacked'

export interface StackedSeries {
  kind: StackedSeriesKind
  bands: StackedBand[]
}

export function computeStackedSeries(
  metrics: Metric[],
  metricsBuckets: M4Bucket[][],
  consolidation: ConsolidationFn
): StackedSeries[] {
  const sums = new Map<string, number[]>()
  const series: StackedSeries[] = []

  for (let i = 0; i < metrics.length; i++) {
    const metric = metrics[i]!
    const buckets = metricsBuckets[i]!
    const stack = metric.render.stack

    if (stack === null) {
      series.push({
        kind: 'line',
        bands: buckets.map((bucket) => ({
          lower: 0,
          upper: bucket.gap ? NaN : selectConsolidatedValue(bucket, consolidation),
          gap: bucket.gap,
          startTime: bucket.startTime,
          endTime: bucket.endTime,
          anchorTime: bucketAnchorTime(bucket)
        }))
      })
      continue
    }

    const sum = sums.get(stack) ?? new Array<number>(buckets.length).fill(0)
    const bands = new Array<StackedBand>(buckets.length)
    for (let j = 0; j < buckets.length; j++) {
      const bucket = buckets[j]!
      const value = bucket.gap ? 0 : selectConsolidatedValue(bucket, consolidation)
      const lower = sum[j]!
      const upper = lower + value
      sum[j] = upper
      bands[j] = {
        lower,
        upper,
        gap: bucket.gap,
        startTime: bucket.startTime,
        endTime: bucket.endTime,
        anchorTime: bucketAnchorTime(bucket)
      }
    }
    sums.set(stack, sum)
    series.push({ kind: 'area-stacked', bands })
  }

  return series
}

export function drawStackedBand(
  ctx: CanvasRenderingContext2D,
  series: StackedSeries,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  color: string,
  style: { fillOpacity?: number | undefined; strokeWidth?: number | undefined } = {}
): void {
  const fillOpacity = style.fillOpacity ?? 0.45
  const strokeWidth = style.strokeWidth ?? 1
  const bandAnchorX = (band: StackedBand): number => xScale(new Date(band.anchorTime * 1000))

  let runStart = 0
  while (runStart < series.bands.length) {
    if (series.bands[runStart]!.gap) {
      runStart++
      continue
    }
    let runEnd = runStart
    while (runEnd < series.bands.length && !series.bands[runEnd]!.gap) {
      runEnd++
    }

    ctx.beginPath()
    for (let i = runStart; i < runEnd; i++) {
      const band = series.bands[i]!
      const pixelX = bandAnchorX(band)
      if (i === runStart) {
        ctx.moveTo(pixelX, yScale(band.upper))
      } else {
        ctx.lineTo(pixelX, yScale(band.upper))
      }
    }
    for (let i = runEnd - 1; i >= runStart; i--) {
      const band = series.bands[i]!
      ctx.lineTo(bandAnchorX(band), yScale(band.lower))
    }
    ctx.closePath()
    ctx.fillStyle = colorWithAlpha(color, fillOpacity)
    ctx.fill()
    ctx.strokeStyle = color
    ctx.lineWidth = strokeWidth
    ctx.stroke()

    runStart = runEnd
  }
}

function colorWithAlpha(color: string, alpha: number): string {
  const red = parseInt(color.slice(1, 3), 16)
  const green = parseInt(color.slice(3, 5), 16)
  const blue = parseInt(color.slice(5, 7), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}
