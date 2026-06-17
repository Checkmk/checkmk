/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear } from 'd3-scale'
import { select } from 'd3-selection'

import type { HorizontalLine } from '../types'

const HORIZONTAL_LINES_CLASS = 'graphing-time-series-graph__horizontal-lines'

export function drawHorizontalLines(
  contextGroup: SVGGElement,
  lines: HorizontalLine[],
  yScale: ScaleLinear<number, number>,
  plotWidth: number
): void {
  const linesGroup = select(contextGroup)
    .selectAll<SVGGElement, HorizontalLine[]>(`g.${HORIZONTAL_LINES_CLASS}`)
    .data([lines])
    .join('g')
    .classed(HORIZONTAL_LINES_CLASS, true)

  linesGroup
    .selectAll<SVGLineElement, HorizontalLine>('line')
    .data(lines, (line) => line.name)
    .join('line')
    .attr('x1', 0)
    .attr('x2', plotWidth)
    .attr('y1', (line) => yScale(line.value))
    .attr('y2', (line) => yScale(line.value))
    .attr('stroke', (line) => line.color)
    .attr('stroke-dasharray', '4,3')
}
