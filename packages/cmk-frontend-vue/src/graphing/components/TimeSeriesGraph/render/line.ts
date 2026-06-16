/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import {
  type CurveFactory,
  curveBasis,
  curveLinear,
  curveMonotoneX,
  line as d3Line
} from 'd3-shape'

import type { M4Bucket } from '../decimation/types'
import type { LineInterpolator } from '../types'

function curveFor(name: LineInterpolator): CurveFactory {
  switch (name) {
    case 'monotoneX':
      return curveMonotoneX
    case 'basis':
      return curveBasis
    default:
      return curveLinear
  }
}

// Per-bucket: vertical min→max line (always straight; extremes preserved).
// Between adjacent non-gap buckets: connector from previous.last → current.first,
// using the configured curve interpolator. Gaps lift the pen and split segments.
export function drawLine(
  ctx: CanvasRenderingContext2D,
  buckets: M4Bucket[],
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  color: string,
  interpolator: LineInterpolator = 'linear'
): void {
  if (buckets.length === 0) {
    return
  }
  ctx.strokeStyle = color
  ctx.lineWidth = 1.5

  // Pass 1: connector polyline through bucket boundary points, segmented at gaps.
  const segments: Array<Array<[number, number]>> = []
  let current: Array<[number, number]> = []
  for (const bucket of buckets) {
    if (bucket.gap) {
      if (current.length) {
        segments.push(current)
        current = []
      }
      continue
    }
    const xFirst = xScale(new Date(bucket.firstValueTime * 1000))
    const yFirst = yScale(bucket.firstValue)
    const xLast = xScale(new Date(bucket.lastValueTime * 1000))
    const yLast = yScale(bucket.lastValue)
    current.push([xFirst, yFirst], [xLast, yLast])
  }
  if (current.length) {
    segments.push(current)
  }

  const path = d3Line<[number, number]>()
    .x((point) => point[0])
    .y((point) => point[1])
    .curve(curveFor(interpolator))
    .context(ctx)
  for (const segment of segments) {
    ctx.beginPath()
    path(segment)
    ctx.stroke()
  }

  // Pass 2: per-bucket min→max verticals (always straight; extremes are pixel-discrete).
  ctx.beginPath()
  for (const bucket of buckets) {
    if (bucket.gap) {
      continue
    }
    const xMin = Math.round(xScale(new Date(bucket.minValueTime * 1000))) + 0.5
    const xMax = Math.round(xScale(new Date(bucket.maxValueTime * 1000))) + 0.5
    ctx.moveTo(xMin, yScale(bucket.minValue))
    ctx.lineTo(xMax, yScale(bucket.maxValue))
  }
  ctx.stroke()
}
