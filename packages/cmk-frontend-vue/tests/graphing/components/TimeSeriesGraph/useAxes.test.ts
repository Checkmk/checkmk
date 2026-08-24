/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  IECFormatter,
  type NotationFormatter
} from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { scaleLinear, scaleTime } from 'd3-scale'
import { select } from 'd3-selection'
import { describe, expect, test, vi } from 'vitest'
import { ref, shallowRef } from 'vue'

import type { TimeAxisTick } from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'
import { AXIS_CLASSES, useAxes } from '@/graphing/components/TimeSeriesGraph/useAxes'

const SVG_NS = 'http://www.w3.org/2000/svg'
const ONE_MIB = 1024 * 1024
const PLOT_WIDTH = 400
const PLOT_HEIGHT = 200
const DAY_SECONDS = 86400

// d3 records each tick's domain value as its own datum; reading it back is how a caller sees
// where the axis actually put its ticks.
function drawnTickPositions(group: Element, axisClass: string): number[] {
  return Array.from(group.querySelectorAll(`g.${axisClass} .tick`))
    .map((tick) => select(tick).datum() as number)
    .sort((first, second) => first - second)
}

// An IEC axis must step by a power of two, and every label must be a whole multiple of that step;
// a decimal step such as 10^6 bytes is what renders as "1.91 MiB" instead of "2 MiB".
function expectBinaryAlignment(positions: number[]): void {
  expect(positions.length).toBeGreaterThan(1)
  const spacing = positions[1]! - positions[0]!
  expect(Math.log2(spacing) % 1).toBe(0)
  positions.forEach((position) => expect(Math.abs(position % spacing)).toBe(0))
}

function setup(
  stepping: 'binary' | 'decimal' = 'decimal',
  formatter: NotationFormatter | null = null
) {
  const axisGroupRef = ref<SVGGElement | null>(document.createElementNS(SVG_NS, 'g') as SVGGElement)
  const plotWidth = ref(PLOT_WIDTH)
  const plotHeight = ref(PLOT_HEIGHT)
  const yStepping = ref<'binary' | 'decimal'>(stepping)
  // shallowRef: ref's deep unwrapping drops the protected members of the formatter class.
  const yFormatter = shallowRef<NotationFormatter | null>(formatter)
  const xScale = scaleTime()
    .domain([new Date(0), new Date(DAY_SECONDS * 1000)])
    .range([0, PLOT_WIDTH])
  const yScale = scaleLinear().domain([0, 1]).range([PLOT_HEIGHT, 0])

  const axes = useAxes(axisGroupRef, xScale, yScale, plotWidth, plotHeight, yStepping, yFormatter)
  return { axes, group: axisGroupRef.value!, xScale, yScale }
}

function valueAxisTickTexts(group: Element): string[] {
  return Array.from(group.querySelectorAll(`g.${AXIS_CLASSES.valueAxis} .tick text`)).map(
    (tickLabel) => tickLabel.textContent ?? ''
  )
}

function setupIec() {
  return setup('binary', new IECFormatter('B', { type: 'auto', digits: 2 }))
}

describe('prepareValueDomain', () => {
  test('aligns the y-domain to bounds that still contain the raw value range', () => {
    const { axes, yScale } = setup()

    axes.prepareValueDomain(3, 47)

    const [domainMin, domainMax] = yScale.domain()
    expect(domainMin).toBeLessThanOrEqual(3)
    expect(domainMax).toBeGreaterThanOrEqual(47)
  })

  test('keeps a band well above zero off the zero line', () => {
    const { axes, yScale } = setup()

    axes.prepareValueDomain(42, 58)

    const [domainMin, domainMax] = yScale.domain()
    expect(domainMin).toBeGreaterThan(0)
    expect(domainMax).toBeGreaterThanOrEqual(58)
  })

  test('puts the zero line of positive-only data on the plot bottom, where the x-axis is', () => {
    const { axes, yScale } = setup()

    axes.prepareValueDomain(0, 5)

    expect(yScale.domain()[0]).toBe(0)
    expect(yScale(0)).toBe(PLOT_HEIGHT)
  })

  test('leaves headroom above the domain maximum', () => {
    const { axes, yScale } = setup()

    axes.prepareValueDomain(0, 5)

    expect(yScale(yScale.domain()[1]!)).toBeGreaterThan(0)
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

    axes.drawTimeAxis(ticks, { showLabels: true })

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines} line`)).toHaveLength(2)
  })

  test('draws a label only for ticks that carry text, rendering the tick text', () => {
    const { axes, group } = setup()
    const ticks: TimeAxisTick[] = [
      { position: 21600, text: '06:00', lineWidth: 2 },
      { position: 43200, text: null, lineWidth: 2 },
      { position: 64800, text: '18:00', lineWidth: 0 }
    ]

    axes.drawTimeAxis(ticks, { showLabels: true })

    const labels = Array.from(group.querySelectorAll(`g.${AXIS_CLASSES.timeLabels} text`))
    expect(labels.map((label) => label.textContent)).toEqual(['06:00', '18:00'])
  })

  test('positions each gridline at its tick time mapped through the x scale', () => {
    const { axes, group, xScale } = setup()
    const tick: TimeAxisTick = { position: 43200, text: '12:00', lineWidth: 2 }

    axes.drawTimeAxis([tick], { showLabels: true })

    const line = group.querySelector(`g.${AXIS_CLASSES.timeGridLines} line`)!
    const expectedX = String(xScale(new Date(tick.position * 1000)))
    expect(line.getAttribute('x1')).toBe(expectedX)
    expect(line.getAttribute('x2')).toBe(expectedX)
  })

  test('draws a single full-width baseline along the plot bottom', () => {
    const { axes, group } = setup()

    axes.drawTimeAxis([{ position: 43200, text: '12:00', lineWidth: 2 }], { showLabels: true })

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

    axes.drawTimeAxis([{ position: 21600, text: '06:00', lineWidth: 2 }], { showLabels: true })
    axes.drawTimeAxis(
      [
        { position: 21600, text: '06:00', lineWidth: 2 },
        { position: 43200, text: '12:00', lineWidth: 2 }
      ],
      { showLabels: true }
    )

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines}`)).toHaveLength(1)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines} line`)).toHaveLength(2)
  })
})

describe('hidden axis labels', () => {
  const TICKS: TimeAxisTick[] = [
    { position: 21600, text: '06:00', lineWidth: 2 },
    { position: 43200, text: '12:00', lineWidth: 2 }
  ]

  test('a hidden time axis drops its labels but keeps its gridlines and baseline', () => {
    const { axes, group } = setup()

    axes.drawTimeAxis(TICKS, { showLabels: false })

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeLabels} text`)).toHaveLength(0)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeGridLines} line`)).toHaveLength(2)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.timeBaseline} line`)).toHaveLength(1)
  })

  test('a hidden value axis blanks its labels but keeps the value grid', async () => {
    const { axes, group } = setup()

    axes.prepareValueDomain(0, 100)
    axes.drawValueGrid()
    axes.drawValueAxis({ showLabels: false })

    await vi.waitFor(() => {
      expect(valueAxisTickTexts(group)).not.toHaveLength(0)
    })
    expect(valueAxisTickTexts(group).filter((label) => label !== '')).toHaveLength(0)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.valueGrid}`)).toHaveLength(1)
  })

  test('toggling the value axis back on restores its labels', async () => {
    const { axes, group } = setup()

    axes.prepareValueDomain(0, 100)
    axes.drawValueAxis({ showLabels: true })
    axes.drawValueAxis({ showLabels: false })
    axes.drawValueAxis({ showLabels: true })

    await vi.waitFor(() => {
      expect(valueAxisTickTexts(group).filter((label) => label !== '')).not.toHaveLength(0)
    })
  })
})

describe('drawValueGrid and drawValueAxis', () => {
  test('each maintain a single SVG group across repeated redraws', () => {
    const { axes, group } = setup()

    axes.prepareValueDomain(0, 100)
    axes.drawValueGrid()
    axes.drawValueAxis({ showLabels: true })
    axes.drawValueGrid()
    axes.drawValueAxis({ showLabels: true })

    expect(group.querySelectorAll(`g.${AXIS_CLASSES.valueGrid}`)).toHaveLength(1)
    expect(group.querySelectorAll(`g.${AXIS_CLASSES.valueAxis}`)).toHaveLength(1)
  })

  test('places the labels of an IEC axis on binary values, not on decimally round ones', () => {
    const { axes, group } = setupIec()

    axes.prepareValueDomain(0, 4 * ONE_MIB)
    axes.drawValueAxis({ showLabels: true })

    expectBinaryAlignment(drawnTickPositions(group, AXIS_CLASSES.valueAxis))
  })

  test('places the grid lines of an IEC axis on binary values too', () => {
    const { axes, group } = setupIec()

    axes.prepareValueDomain(0, 4 * ONE_MIB)
    axes.drawValueGrid()

    expectBinaryAlignment(drawnTickPositions(group, AXIS_CLASSES.valueGrid))
  })

  test('labels both sides of a mirrored IEC axis on binary values', () => {
    const { axes, group } = setupIec()

    axes.prepareValueDomain(-4 * ONE_MIB, 4 * ONE_MIB)
    axes.drawValueAxis({ showLabels: true })

    const positions = drawnTickPositions(group, AXIS_CLASSES.valueAxis)
    expect(positions.some((position) => position < 0)).toBe(true)
    expect(positions.some((position) => position > 0)).toBe(true)
    expectBinaryAlignment(positions)
  })
})

describe('valueTickLabels', () => {
  test('reports the labels an IEC axis draws, for sizing the margin that holds them', () => {
    const { axes } = setupIec()

    axes.prepareValueDomain(0, 4 * ONE_MIB)

    expect(axes.valueTickLabels()).toContain('4 MiB')
  })
})
