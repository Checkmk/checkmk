/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'

import GraphBrush from '@/graphing/components/GraphBrush/GraphBrush.vue'
import type { Metric } from '@/graphing/components/TimeSeriesGraph'

const DOMAIN = { start: 1000, end: 2000, step: 10 }

const PLOT_LEFT = 50
const PLOT_WIDTH = 200

function makeMetric(dataPoints: (number | null)[]): Metric {
  return {
    data_points: dataPoints,
    render: { stack: null, inverse: false, hidden: false },
    metadata: { color: '#3366cc' }
  } as unknown as Metric
}

function waveformXs(container: Element): number[] {
  const path = container.querySelector('path.graphing-graph-brush__area')!
  return [...path.getAttribute('d')!.matchAll(/[ML]([\d.]+),/g)].map((match) =>
    parseFloat(match[1]!)
  )
}

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

test('fills the waveform out to the right edge of the track', () => {
  const metrics = [makeMetric(samplesFilling(DOMAIN))]

  const { container } = renderBrush({ metrics })

  expect(Math.max(...waveformXs(container))).toBeCloseTo(PLOT_LEFT + PLOT_WIDTH, 5)
})

test('leaves the samples the fetch reached past the strip off the waveform', () => {
  const STEPS_FETCHED_PAST_THE_STRIP = 2
  const dataDomainReachingPastTheStrip = {
    ...DOMAIN,
    end: DOMAIN.end + STEPS_FETCHED_PAST_THE_STRIP * DOMAIN.step
  }
  const metrics = [makeMetric(samplesFilling(dataDomainReachingPastTheStrip))]

  const { container } = renderBrush({ metrics, dataDomain: dataDomainReachingPastTheStrip })

  const drawn = waveformXs(container)
  expect(drawn).not.toHaveLength(0)
  expect(Math.max(...drawn)).toBeLessThanOrEqual(PLOT_LEFT + PLOT_WIDTH)
})
