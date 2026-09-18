/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { select } from 'd3-selection'

import { timestampAt } from '../axes/timeAxis'
import type { ShadedRegion, TimeRange } from '../types'

const SHADED_REGIONS_CLASS = 'graphing-time-series-graph__shaded-regions'
const FILL_OPACITY = 0.15

interface PlotExtent {
  top: number
  bottom: number
}

function bandEdge(
  bound: (number | null)[] | null | undefined,
  index: number,
  openTo: number,
  yScale: ScaleLinear<number, number>
): number | null {
  if (bound === null || bound === undefined) {
    return openTo
  }
  const value = bound[index]
  return value === null || value === undefined ? null : yScale(value)
}

export function regionPath(
  region: ShadedRegion,
  dataTimeRange: TimeRange,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  plot: PlotExtent
): string {
  const points = Math.max(
    region.data_points.lower?.length ?? 0,
    region.data_points.upper?.length ?? 0
  )
  const forward: string[] = []
  const backward: string[] = []
  for (let i = 0; i < points; i++) {
    const lower = bandEdge(region.data_points.lower, i, plot.bottom, yScale)
    const upper = bandEdge(region.data_points.upper, i, plot.top, yScale)
    if (lower === null || upper === null) {
      continue
    }
    const x = xScale(new Date(timestampAt(dataTimeRange, i) * 1000))
    forward.push(`${x},${upper}`)
    backward.unshift(`${x},${lower}`)
  }
  return forward.length === 0 ? '' : `M${forward.join('L')}L${backward.join('L')}Z`
}

export function drawShadedRegions(
  contextGroup: SVGGElement,
  regions: ShadedRegion[],
  dataTimeRange: TimeRange,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  plot: PlotExtent
): void {
  const group = select(contextGroup)
    .selectAll<SVGGElement, ShadedRegion[]>(`g.${SHADED_REGIONS_CLASS}`)
    .data([regions])
    .join('g')
    .classed(SHADED_REGIONS_CLASS, true)

  group
    .selectAll<SVGPathElement, ShadedRegion>('path')
    .data(regions, (region) => region.name)
    .join('path')
    .attr('d', (region) => regionPath(region, dataTimeRange, xScale, yScale, plot))
    .attr('fill', (region) => region.color)
    .attr('fill-opacity', FILL_OPACITY)
}
