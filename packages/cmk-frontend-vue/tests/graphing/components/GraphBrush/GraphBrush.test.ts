/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'
import { beforeEach, expect, test, vi } from 'vitest'

import GraphBrush from '@/graphing/components/GraphBrush/GraphBrush.vue'
import type { Metric } from '@/graphing/components/TimeSeriesGraph'

const DOMAIN = { start: 1000, end: 2000, step: 10 }

const PLOT_LEFT = 50
const PLOT_WIDTH = 200

function makeMetric(dataPoints: (number | null)[], render: Partial<Metric['render']> = {}): Metric {
  return {
    data_points: dataPoints,
    render: { stack: null, inverse: false, hidden: false, ...render },
    metadata: { name: 'm', color: '#3366cc' }
  } as unknown as Metric
}

// The waveform is painted onto a canvas, which jsdom does not implement. Record the points and
// the paint operations so the real draw path runs and can be asserted on.
let drawnPoints: Array<[number, number]> = []
let paintOps: string[] = []

function createCanvasContextStub(): CanvasRenderingContext2D {
  const state: Record<string | symbol, unknown> = {}
  return new Proxy(state, {
    get: (target, prop) => {
      if (prop === 'moveTo' || prop === 'lineTo') {
        return (x: number, y: number) => void drawnPoints.push([x, y])
      }
      if (prop === 'fill' || prop === 'stroke') {
        return () => void paintOps.push(prop)
      }
      return prop in target ? target[prop] : () => undefined
    },
    set: (target, prop, value) => {
      target[prop] = value
      return true
    }
  }) as unknown as CanvasRenderingContext2D
}

beforeEach(() => {
  drawnPoints = []
  paintOps = []
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(createCanvasContextStub())
})

// Canvas coordinates are strip-local: the canvas is positioned at plotLeft, so 0 is the track's
// left edge and PLOT_WIDTH its right.
const waveformXs = (): number[] => drawnPoints.map(([x]) => x)

// jsdom reports an all-zero bounding rect, so client coordinates are the SVG-local ones.
function renderBrush(overrides: Record<string, unknown> = {}) {
  return render(GraphBrush, {
    props: {
      metrics: [],
      domain: DOMAIN,
      dataDomain: DOMAIN,
      window: { start: 1400, end: 1600 },
      minSpan: null,
      width: 300,
      plotLeft: PLOT_LEFT,
      plotWidth: PLOT_WIDTH,
      ...overrides
    }
  })
}

function samplesFilling(domain: { start: number; end: number; step: number }): number[] {
  const count = (domain.end - domain.start) / domain.step
  return Array.from({ length: count }, (_, index) => index + 1)
}

async function dragFrom(
  container: Element,
  from: { x: number; y: number },
  toX: number
): Promise<void> {
  const svg = container.querySelector('svg')!
  await fireEvent.mouseDown(svg, { button: 0, clientX: from.x, clientY: from.y })
  await fireEvent.mouseMove(window, { clientX: toX, clientY: from.y })
  await fireEvent.mouseUp(window)
}

test('drag starting on the track updates the time range', async () => {
  const { container, emitted } = renderBrush()

  await dragFrom(container, { x: 150, y: 30 }, 100)

  expect(emitted()['update:requestedTimeRange']).toHaveLength(1)
})

test('drag starting left of the track is ignored', async () => {
  const { container, emitted } = renderBrush()

  await dragFrom(container, { x: 10, y: 30 }, 100)

  expect(emitted()['update:requestedTimeRange']).toBeUndefined()
})

test('drag starting below the track is ignored', async () => {
  const { container, emitted } = renderBrush()

  await dragFrom(container, { x: 150, y: 60 }, 100)

  expect(emitted()['update:requestedTimeRange']).toBeUndefined()
})

const PX_PER_SECOND = PLOT_WIDTH / (DOMAIN.end - DOMAIN.start)

test('spans the track rather than stopping short of its edges', () => {
  const metrics = [makeMetric(samplesFilling(DOMAIN))]

  renderBrush({ metrics })

  // A value is placed at the end of the interval it covers, so the first one sits a step in.
  const drawn = waveformXs()
  expect(Math.min(...drawn)).toBeLessThanOrEqual(DOMAIN.step * PX_PER_SECOND)
  expect(Math.max(...drawn)).toBeGreaterThanOrEqual(PLOT_WIDTH)
})

test('draws the strip extent, not everything the fetch reached past it', () => {
  const STEPS_FETCHED_PAST_THE_STRIP = 2
  const dataDomainReachingPastTheStrip = {
    ...DOMAIN,
    end: DOMAIN.end + STEPS_FETCHED_PAST_THE_STRIP * DOMAIN.step
  }
  const metrics = [makeMetric(samplesFilling(dataDomainReachingPastTheStrip))]

  renderBrush({ metrics, dataDomain: dataDomainReachingPastTheStrip })

  // The renderer carries one bucket past each edge so a curve leaving the strip is drawn to it;
  // what it must not do is stretch the strip over the whole fetched extent.
  const fetchedEndPx = (dataDomainReachingPastTheStrip.end - DOMAIN.start) * PX_PER_SECOND
  const drawn = waveformXs()
  expect(drawn).not.toHaveLength(0)
  expect(Math.max(...drawn)).toBeLessThan(fetchedEndPx)
})

test('draws a metric with no stack group as a stroked line, never as a filled area', () => {
  const metrics = [makeMetric(samplesFilling(DOMAIN), { stack: null })]

  renderBrush({ metrics })

  expect(paintOps).toContain('stroke')
  expect(paintOps).not.toContain('fill')
})

test('draws a grouped metric as a filled area, the way the plot does', () => {
  const metrics = [makeMetric(samplesFilling(DOMAIN), { stack: 'g1' })]

  renderBrush({ metrics })

  expect(paintOps).toContain('fill')
})
