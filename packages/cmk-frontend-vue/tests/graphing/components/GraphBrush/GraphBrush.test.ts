/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'

import GraphBrush from '@/graphing/components/GraphBrush/GraphBrush.vue'

const DOMAIN = { start: 1000, end: 2000, step: 10 }

// jsdom reports an all-zero bounding rect, so client coordinates are the SVG-local ones.
function renderBrush() {
  return render(GraphBrush, {
    props: {
      metrics: [],
      domain: DOMAIN,
      window: { start: 1400, end: 1600 },
      minSpan: null,
      width: 300,
      plotLeft: 50,
      plotWidth: 200
    }
  })
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
