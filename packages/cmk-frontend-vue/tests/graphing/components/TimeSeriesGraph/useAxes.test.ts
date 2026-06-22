/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { scaleLinear, scaleTime } from 'd3-scale'
import { describe, expect, test } from 'vitest'
import { ref } from 'vue'

import type { TimeAxisTick } from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'
import { AXIS_CLASSES, useAxes } from '@/graphing/components/TimeSeriesGraph/useAxes'

const SVG_NS = 'http://www.w3.org/2000/svg'
const PLOT_WIDTH = 400
const PLOT_HEIGHT = 200
const DAY_SECONDS = 86400

function setup() {
  const axisGroupRef = ref<SVGGElement | null>(document.createElementNS(SVG_NS, 'g') as SVGGElement)
  const plotWidth = ref(PLOT_WIDTH)
  const plotHeight = ref(PLOT_HEIGHT)
  const yStepping = ref<'binary' | 'decimal'>('decimal')
  const yTickFormatter = ref<(value: number) => string>((value) => String(value))
  const xScale = scaleTime()
    .domain([new Date(0), new Date(DAY_SECONDS * 1000)])
    .range([0, PLOT_WIDTH])
  const yScale = scaleLinear().domain([0, 1]).range([PLOT_HEIGHT, 0])

  const axes = useAxes(
    axisGroupRef,
    xScale,
    yScale,
    plotWidth,
    plotHeight,
    yStepping,
    yTickFormatter
  )
  return { axes, group: axisGroupRef.value!, xScale, yScale }
}

describe('prepareValueDomain', () => {
  test('aligns the y-domain to bounds that still contain the raw value range', () => {
    const { axes, yScale } = setup()

    axes.prepareValueDomain(3, 47)

    const [domainMin, domainMax] = yScale.domain()
    expect(domainMin).toBeLessThanOrEqual(3)
    expect(domainMax).toBeGreaterThanOrEqual(47)
  })
})

describe('drawTimeAxis', () => {
  test('draws a gridline only for ticks with a positive line width', () => {
    const { axes, group } = setup()
    const ticks: TimeAxisTick[] = [
      { position: 21600, text: '06:00', lineWidth: 2 },
      { position: 43200, text: null, lineWidth: 2 },
      { position: 64800, text: '18:00', lineWidth: 0 }
    ]

    axes.drawTimeAxis(ticks)

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines} line`)).toHaveLength(2)
  })

  test('draws a label only for ticks that carry text, rendering the tick text', () => {
    const { axes, group } = setup()
    const ticks: TimeAxisTick[] = [
      { position: 21600, text: '06:00', lineWidth: 2 },
      { position: 43200, text: null, lineWidth: 2 },
      { position: 64800, text: '18:00', lineWidth: 0 }
    ]

    axes.drawTimeAxis(ticks)

    const labels = Array.from(group.querySelectorAll(`g.${AXIS_CLASSES.timeLabels} text`))
    expect(labels.map((label) => label.textContent)).toEqual(['06:00', '18:00'])
  })

  test('positions each gridline at its tick time mapped through the x scale', () => {
    const { axes, group, xScale } = setup()
    const tick: TimeAxisTick = { position: 43200, text: '12:00', lineWidth: 2 }

    axes.drawTimeAxis([tick])

    const line = group.querySelector(`g.${AXIS_CLASSES.timeGridLines} line`)!
    const expectedX = String(xScale(new Date(tick.position * 1000)))
    expect(line.getAttribute('x1')).toBe(expectedX)
    expect(line.getAttribute('x2')).toBe(expectedX)
  })

  test('draws a single full-width baseline along the plot bottom', () => {
    const { axes, group } = setup()

    axes.drawTimeAxis([{ position: 43200, text: '12:00', lineWidth: 2 }])

    const baselines = group.querySelectorAll(`g.${AXIS_CLASSES.timeBaseline} line`)
    expect(baselines).toHaveLength(1)
    const baseline = baselines[0]!
    expect(baseline.getAttribute('x1')).toBe('0')
    expect(baseline.getAttribute('x2')).toBe(String(PLOT_WIDTH))
    expect(baseline.getAttribute('y1')).toBe(String(PLOT_HEIGHT))
    expect(baseline.getAttribute('y2')).toBe(String(PLOT_HEIGHT))
  })

  test('updates the x-axis in place across redraws instead of appending duplicate groups', () => {
    const { axes, group } = setup()

    axes.drawTimeAxis([{ position: 21600, text: '06:00', lineWidth: 2 }])
    axes.drawTimeAxis([
      { position: 21600, text: '06:00', lineWidth: 2 },
      { position: 43200, text: '12:00', lineWidth: 2 }
    ])

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines}`)).toHaveLength(1)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines} line`)).toHaveLength(2)
  })
})

describe('drawValueGrid and drawValueAxis', () => {
  test('each maintain a single SVG group across repeated redraws', () => {
    const { axes, group } = setup()

    axes.prepareValueDomain(0, 100)
    axes.drawValueGrid()
    axes.drawValueAxis()
    axes.drawValueGrid()
    axes.drawValueAxis()

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.valueGrid}`)).toHaveLength(1)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.valueAxis}`)).toHaveLength(1)
  })
})
