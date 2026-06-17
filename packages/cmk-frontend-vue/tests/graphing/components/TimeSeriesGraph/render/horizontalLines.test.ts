/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear } from 'd3-scale'
import { describe, expect, test } from 'vitest'

import { drawHorizontalLines } from '@/graphing/components/TimeSeriesGraph/render/horizontalLines'
import type { HorizontalLine } from '@/graphing/components/TimeSeriesGraph/types'

const SVG_NS = 'http://www.w3.org/2000/svg'
const GROUP_SELECTOR = 'g.graphing-time-series-graph__horizontal-lines'
const LINE_SELECTOR = 'g.graphing-time-series-graph__horizontal-lines line'

const plotWidth = 200
// Non-identity scale, so a rendered y proves the threshold value was mapped through the
// scale rather than coincidentally echoing the input value.
const yScale = ((value: number) => 200 - value) as unknown as ScaleLinear<number, number>

const WARN: HorizontalLine = { name: 'warn', value: 30, color: '#ffa500' }
const CRIT: HorizontalLine = { name: 'crit', value: 70, color: '#ff0000' }

function makeContextGroup(): SVGGElement {
  return document.createElementNS(SVG_NS, 'g') as SVGGElement
}

function renderedLines(contextGroup: SVGGElement): SVGLineElement[] {
  return Array.from(contextGroup.querySelectorAll<SVGLineElement>(LINE_SELECTOR))
}

describe('drawHorizontalLines', () => {
  test('renders each threshold as a full-width horizontal line at its scaled value', () => {
    const contextGroup = makeContextGroup()
    const thresholds = [WARN, CRIT]

    drawHorizontalLines(contextGroup, thresholds, yScale, plotWidth)

    const actual = renderedLines(contextGroup).map((line) => ({
      x1: line.getAttribute('x1'),
      x2: line.getAttribute('x2'),
      y1: line.getAttribute('y1'),
      y2: line.getAttribute('y2'),
      stroke: line.getAttribute('stroke'),
      dashed: line.hasAttribute('stroke-dasharray')
    }))
    const expected = thresholds.map((threshold) => {
      const y = String(yScale(threshold.value))
      return { x1: '0', x2: String(plotWidth), y1: y, y2: y, stroke: threshold.color, dashed: true }
    })
    expect(actual).toEqual(expected)
  })

  test('groups the rendered lines under a single container', () => {
    const contextGroup = makeContextGroup()

    drawHorizontalLines(contextGroup, [WARN, CRIT], yScale, plotWidth)

    expect(contextGroup.querySelectorAll(GROUP_SELECTOR)).toHaveLength(1)
  })

  test('updates lines in place across redraws instead of appending duplicates', () => {
    const contextGroup = makeContextGroup()

    drawHorizontalLines(contextGroup, [WARN, CRIT], yScale, plotWidth)
    const lineBeforeRedraw = renderedLines(contextGroup)[0]!
    drawHorizontalLines(contextGroup, [{ ...WARN, value: 35 }, CRIT], yScale, plotWidth)

    const linesAfterRedraw = renderedLines(contextGroup)
    expect(contextGroup.querySelectorAll(GROUP_SELECTOR)).toHaveLength(1)
    expect(linesAfterRedraw).toHaveLength(2)
    expect(linesAfterRedraw[0]).toBe(lineBeforeRedraw)
    expect(linesAfterRedraw[0]!.getAttribute('y1')).toBe(String(yScale(35)))
  })

  test('drops the line for a threshold removed on the next draw', () => {
    const contextGroup = makeContextGroup()

    drawHorizontalLines(contextGroup, [WARN, CRIT], yScale, plotWidth)
    drawHorizontalLines(contextGroup, [CRIT], yScale, plotWidth)

    const remaining = renderedLines(contextGroup)
    expect(remaining).toHaveLength(1)
    expect(remaining[0]!.getAttribute('stroke')).toBe(CRIT.color)
  })
})
