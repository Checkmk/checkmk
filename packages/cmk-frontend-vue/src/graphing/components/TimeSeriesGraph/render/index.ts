/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'

import type { M4Cache } from '../decimation/types'
import type { LineInterpolator, Metric } from '../types'
import { drawLine } from './line'
import { type StackedSeries, drawStackedBand } from './stacked'

export interface DrawOptions {
  interpolator: LineInterpolator
  /**
   * Stroke weights, in css pixels. Defaulted to the plot's; the brush strip is a fraction of its
   * height and at the plot's weights would read as mostly stroke.
   */
  lineWidth?: number | undefined
  bandStrokeWidth?: number | undefined
}

export function drawData(
  ctx: CanvasRenderingContext2D,
  metrics: Metric[],
  invertedBuckets: M4Cache[],
  stacks: StackedSeries[],
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  options: DrawOptions,
  highlightedMetricName: string | null
): void {
  for (let i = 0; i < metrics.length; i++) {
    // Hidden metrics (stack references) shape the stacking sums but are never painted.
    if (metrics[i]!.render.hidden) {
      continue
    }
    if (stacks[i]!.kind === 'area-stacked') {
      ctx.globalAlpha =
        highlightedMetricName !== null && metrics[i]!.metadata.name !== highlightedMetricName
          ? 0.4
          : 1
      drawStackedBand(ctx, stacks[i]!, xScale, yScale, metrics[i]!.metadata.color, {
        strokeWidth: options.bandStrokeWidth
      })
    }
  }
  for (let i = 0; i < metrics.length; i++) {
    if (metrics[i]!.render.hidden) {
      continue
    }
    if (stacks[i]!.kind === 'line') {
      ctx.globalAlpha =
        highlightedMetricName !== null && metrics[i]!.metadata.name !== highlightedMetricName
          ? 0.4
          : 1
      drawLine(
        ctx,
        invertedBuckets[i]!,
        xScale,
        yScale,
        metrics[i]!.metadata.color,
        options.interpolator,
        options.lineWidth
      )
    }
  }
  ctx.globalAlpha = 1
}
