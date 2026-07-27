/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { scaleLinear, scaleTime } from 'd3-scale'
import { describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import type { TimeRange, ZoomMode } from '@/graphing/components/TimeSeriesGraph/types'
import { useZoomGesture } from '@/graphing/components/TimeSeriesGraph/useZoomGesture'

const DEFAULT_TIME_RANGE: TimeRange = { start: 1000, end: 2000, step: 60 }

// Travels on both axes at once, so only the mode can decide which axis is zoomed.
const DIAGONAL_DRAG_FROM: [number, number] = [40, 25]
const DIAGONAL_DRAG_TO: [number, number] = [120, 75]

interface GestureOptions {
  minTimeRange?: number
  timeRange?: TimeRange
}

// A 200×100px plot: x maps to the given time range (1000..2000s by default, so 1px is 5s),
// y maps screen-inverted to value 100..0. onBeforeUnmount needs a mounted harness.
function mountGesture(mode: ZoomMode, options: GestureOptions = {}) {
  const timeRange = options.timeRange ?? DEFAULT_TIME_RANGE
  const onZoom = vi.fn()
  const xScale = scaleTime()
    .domain([new Date(timeRange.start * 1000), new Date(timeRange.end * 1000)])
    .range([0, 200])
  const yScale = scaleLinear().domain([0, 100]).range([100, 0])
  let api!: ReturnType<typeof useZoomGesture>
  const harness = defineComponent({
    setup() {
      api = useZoomGesture({
        zoomMode: () => mode,
        timeRange: () => timeRange,
        minTimeRange: () => options.minTimeRange ?? null,
        minValueRange: () => null,
        plotWidth: ref(200),
        plotHeight: ref(100),
        xScale,
        yScale,
        plotCoords: (ev: MouseEvent) => ({ x: ev.clientX, y: ev.clientY }),
        onZoom
      })
      return () => h('div')
    }
  })
  render(harness)
  return { api, onZoom }
}

function drag(
  api: ReturnType<typeof useZoomGesture>,
  from: [number, number],
  to: [number, number]
): void {
  api.onPlotMouseDown(
    new MouseEvent('mousedown', { button: 0, clientX: from[0], clientY: from[1] })
  )
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: to[0], clientY: to[1] }))
  window.dispatchEvent(new MouseEvent('mouseup'))
}

describe('useZoomGesture', () => {
  test('the plot cursor hints the armed axis', () => {
    expect(mountGesture('time').api.plotCursor.value).toBe('ew-resize')
    expect(mountGesture('value').api.plotCursor.value).toBe('ns-resize')
  })

  test('there is no selection band until a drag starts', () => {
    const { api } = mountGesture('time')

    expect(api.selectionBand.value).toBeNull()
  })

  test('a time-mode drag draws a full-height band across the x span', () => {
    const { api } = mountGesture('time')

    api.onPlotMouseDown(new MouseEvent('mousedown', { button: 0, clientX: 40, clientY: 30 }))
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 120, clientY: 80 }))

    expect(api.selectionBand.value).toEqual({ x: 40, y: 0, width: 80, height: 100 })

    window.dispatchEvent(new MouseEvent('mouseup'))
  })

  test('a horizontal drag past the threshold emits a time-range zoom', () => {
    const { api, onZoom } = mountGesture('time')

    drag(api, [40, 30], [120, 30])

    expect(onZoom).toHaveBeenCalledWith({ timeRange: { start: 1200, end: 1600, step: 60 } })
  })

  test('a vertical drag past the threshold emits a value-range zoom', () => {
    const { api, onZoom } = mountGesture('value')

    drag(api, [40, 25], [40, 75])

    expect(onZoom).toHaveBeenCalledWith({
      timeRange: DEFAULT_TIME_RANGE,
      valueRange: { min: 25, max: 75 }
    })
  })

  test('a sub-threshold drag is treated as a click and emits nothing', () => {
    const { api, onZoom } = mountGesture('time')

    drag(api, [40, 30], [42, 30])

    expect(onZoom).not.toHaveBeenCalled()
  })

  test('a diagonal drag in time mode narrows the time range and leaves Y auto-scaled', () => {
    const { api, onZoom } = mountGesture('time')

    drag(api, DIAGONAL_DRAG_FROM, DIAGONAL_DRAG_TO)

    expect(onZoom).toHaveBeenCalledWith({ timeRange: { start: 1200, end: 1600, step: 60 } })
  })

  test('the same diagonal drag in value mode narrows Y and leaves the time range alone', () => {
    const { api, onZoom } = mountGesture('value')

    drag(api, DIAGONAL_DRAG_FROM, DIAGONAL_DRAG_TO)

    expect(onZoom).toHaveBeenCalledWith({
      timeRange: DEFAULT_TIME_RANGE,
      valueRange: { min: 25, max: 75 }
    })
  })
})

describe('useZoomGesture — a drag ending outside the plot', () => {
  test('clamps an X drag-end left of the plot to the visible start', () => {
    const { api, onZoom } = mountGesture('time')

    drag(api, [120, 30], [-500, 30])

    expect(onZoom).toHaveBeenCalledWith({ timeRange: { start: 1000, end: 1600, step: 60 } })
  })

  test('clamps an X drag-end right of the plot to the visible end', () => {
    const { api, onZoom } = mountGesture('time')

    drag(api, [40, 30], [900, 30])

    expect(onZoom).toHaveBeenCalledWith({ timeRange: { start: 1200, end: 2000, step: 60 } })
  })

  test('clamps a Y drag-end above the plot to the axis maximum', () => {
    const { api, onZoom } = mountGesture('value')

    drag(api, [40, 25], [40, -500])

    expect(onZoom).toHaveBeenCalledWith({
      timeRange: DEFAULT_TIME_RANGE,
      valueRange: { min: 75, max: 100 }
    })
  })

  test('clamps a Y drag-end below the plot to the axis minimum', () => {
    const { api, onZoom } = mountGesture('value')

    drag(api, [40, 75], [40, 600])

    expect(onZoom).toHaveBeenCalledWith({
      timeRange: DEFAULT_TIME_RANGE,
      valueRange: { min: 0, max: 25 }
    })
  })

  test('stays a click when only a sub-threshold sliver of the drag was on screen', () => {
    const { api, onZoom } = mountGesture('time')

    // Raw travel is large, but only 1px of it is on screen.
    drag(api, [1, 30], [-500, 30])

    expect(onZoom).not.toHaveBeenCalled()
  })
})

describe('useZoomGesture — minimum span', () => {
  test('widens a sub-minute selection to the minimum span about its centre', () => {
    const { api, onZoom } = mountGesture('time', { minTimeRange: 60 })

    // 10px of a 200px/1000s plot is 50s, under the 60s floor.
    drag(api, [100, 30], [110, 30])

    expect(onZoom).toHaveBeenCalledWith({ timeRange: { start: 1495, end: 1555, step: 60 } })
  })

  test('a further zoom inside an already-floored window leaves it unchanged', () => {
    const flooredWindow: TimeRange = { start: 1000, end: 1060, step: 60 }
    const { api, onZoom } = mountGesture('time', { minTimeRange: 60, timeRange: flooredWindow })

    drag(api, [80, 30], [120, 30])

    expect(onZoom).toHaveBeenCalledWith({ timeRange: flooredWindow })
  })
})
