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
}

export function drawData(
  ctx: CanvasRenderingContext2D,
  metrics: Metric[],
  invertedBuckets: M4Cache[],
  stacks: StackedSeries[],
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  options: DrawOptions,
  highlightedMetricName?: string | null
): void {
  const highlighted = highlightedMetricName ?? null

  for (let i = 0; i < metrics.length; i++) {
    if (stacks[i]!.kind === 'area-stacked') {
      ctx.globalAlpha = highlighted !== null && metrics[i]!.metadata.name !== highlighted ? 0.4 : 1
      drawStackedBand(ctx, stacks[i]!, xScale, yScale, metrics[i]!.metadata.color)
    }
  }
  for (let i = 0; i < metrics.length; i++) {
    if (stacks[i]!.kind === 'line') {
      ctx.globalAlpha = highlighted !== null && metrics[i]!.metadata.name !== highlighted ? 0.4 : 1
      drawLine(
        ctx,
        invertedBuckets[i]!,
        xScale,
        yScale,
        metrics[i]!.metadata.color,
        options.interpolator
      )
    }
  }
  ctx.globalAlpha = 1
}
