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
  minValueRange?: number
  timeRange?: TimeRange
  valueRange?: { min: number; max: number }
  atTimeFloor?: boolean
}

// A 200×100px plot: x maps to the given time range (1000..2000s by default, so 1px is 5s),
// y maps screen-inverted to value 100..0. onBeforeUnmount needs a mounted harness.
function mountGesture(mode: ZoomMode, options: GestureOptions = {}) {
  const timeRange = options.timeRange ?? DEFAULT_TIME_RANGE
  const onZoom = vi.fn()
  const onZoomRefused = vi.fn()
  const onPlotClick = vi.fn()
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
        minValueRange: () => options.minValueRange ?? null,
        valueRange: () => options.valueRange ?? null,
        atTimeFloor: () => options.atTimeFloor ?? false,
        plotWidth: ref(200),
        plotHeight: ref(100),
        xScale,
        yScale,
        plotCoords: (ev: MouseEvent) => ({ x: ev.clientX, y: ev.clientY }),
        onZoom,
        onZoomRefused,
        onPlotClick
      })
      return () => h('div')
    }
  })
  render(harness)
  return { api, onZoom, onZoomRefused, onPlotClick }
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
  window.dispatchEvent(new MouseEvent('mouseup', { clientX: to[0], clientY: to[1] }))
}

describe('useZoomGesture', () => {
  test('a refused zoom reports where the press happened, so the reason can be shown there', () => {
    const { api, onZoomRefused } = mountGesture('time', { atTimeFloor: true })

    drag(api, [40, 25], [90, 70])

    expect(onZoomRefused).toHaveBeenCalledWith({ x: 40, y: 25 })
  })

  test('a refusal never draws a selection band, so no zoom area can be dragged out', () => {
    const { api } = mountGesture('time', { atTimeFloor: true })

    api.onPlotMouseDown(new MouseEvent('mousedown', { button: 0, clientX: 40, clientY: 25 }))
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 120, clientY: 60 }))

    expect(api.selectionBand.value).toBeNull()

    window.dispatchEvent(new MouseEvent('mouseup', { clientX: 120, clientY: 60 }))
  })

  test('a refusal is reported once', () => {
    const { api, onZoomRefused } = mountGesture('time', { atTimeFloor: true })

    drag(api, [40, 25], [90, 70])

    expect(onZoomRefused).toHaveBeenCalledTimes(1)
  })

  test('a view wider than the minimum time range still zooms', () => {
    const { api, onZoom, onZoomRefused } = mountGesture('time', { minTimeRange: 60 })

    drag(api, [0, 25], [200, 25])

    expect(onZoomRefused).not.toHaveBeenCalled()
    expect(onZoom).toHaveBeenCalledTimes(1)
  })

  test('a drag narrower than the floor still zooms, clamped up to it', () => {
    // 1px is 5s, so a 50px drag asks for 250s against a 300s floor: clamped, not refused.
    const { api, onZoom, onZoomRefused } = mountGesture('time', { minTimeRange: 300 })

    drag(api, [40, 25], [90, 25])

    expect(onZoomRefused).not.toHaveBeenCalled()
    const { timeRange } = onZoom.mock.calls[0]![0]
    expect(timeRange.end - timeRange.start).toBeCloseTo(300)
  })

  test('no floor configured never refuses a zoom', () => {
    const { api, onZoomRefused } = mountGesture('time')

    drag(api, [40, 25], [50, 25])

    expect(onZoomRefused).not.toHaveBeenCalled()
  })

  test('an auto-scaled value axis has no floor to be at, so peak zoom is never refused', () => {
    const { api, onZoom, onZoomRefused } = mountGesture('value', { minValueRange: 10 })

    drag(api, [40, 20], [40, 80])

    expect(onZoomRefused).not.toHaveBeenCalled()
    expect(onZoom).toHaveBeenCalledTimes(1)
  })

  test('a value axis already at its minimum span refuses the zoom', () => {
    const { api, onZoom, onZoomRefused } = mountGesture('value', {
      minValueRange: 10,
      valueRange: { min: 40, max: 50 }
    })

    drag(api, [40, 20], [40, 80])

    expect(onZoom).not.toHaveBeenCalled()
    expect(onZoomRefused).toHaveBeenCalledTimes(1)
  })

  test('the cursor names the zoom while a drag is under way', () => {
    const { api } = mountGesture('time')

    api.onPlotMouseDown(new MouseEvent('mousedown', { button: 0, clientX: 40, clientY: 25 }))

    expect(api.plotCursor.value).toBe('zoom-in')

    window.dispatchEvent(new MouseEvent('mouseup', { clientX: 40, clientY: 25 }))
    expect(api.plotCursor.value).toBe('ew-resize')
  })

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

    window.dispatchEvent(new MouseEvent('mouseup', { clientX: 120, clientY: 80 }))
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
    const { api, onZoom, onPlotClick } = mountGesture('time')

    drag(api, [40, 30], [42, 30])

    expect(onZoom).not.toHaveBeenCalled()
    expect(onPlotClick).toHaveBeenCalledTimes(1)
  })

  test('a drag past the threshold is a zoom, not a click', () => {
    const { api, onPlotClick } = mountGesture('time')

    drag(api, [40, 30], [120, 30])

    expect(onPlotClick).not.toHaveBeenCalled()
  })

  test('a sub-threshold press in value mode reports a click on the vertical axis', () => {
    const { api, onZoom, onPlotClick } = mountGesture('value')

    drag(api, [40, 30], [40, 32])

    expect(onZoom).not.toHaveBeenCalled()
    expect(onPlotClick).toHaveBeenCalledTimes(1)
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

  test('a click at the zoom floor still reports, though no band was armed', () => {
    const { api, onZoom, onPlotClick } = mountGesture('time', { atTimeFloor: true })

    drag(api, [80, 30], [81, 30])

    expect(onZoom).not.toHaveBeenCalled()
    expect(onPlotClick).toHaveBeenCalledTimes(1)
  })

  // The refusal answers an attempted zoom, which a click at the floor is not.
  test('a click at the zoom floor is not refused', () => {
    const { api, onZoomRefused } = mountGesture('time', { atTimeFloor: true })

    drag(api, [80, 30], [81, 30])

    expect(onZoomRefused).not.toHaveBeenCalled()
  })

  // A release needs no preceding move, so the gesture is classified on the releasing event.
  test('a press and release far apart is a zoom even with no move between them', () => {
    const { api, onZoom, onPlotClick } = mountGesture('time')

    api.onPlotMouseDown(new MouseEvent('mousedown', { button: 0, clientX: 40, clientY: 30 }))
    window.dispatchEvent(new MouseEvent('mouseup', { clientX: 120, clientY: 30 }))

    expect(onPlotClick).not.toHaveBeenCalled()
    expect(onZoom).toHaveBeenCalledTimes(1)
  })

  test('a further zoom is refused once time zoom is at its floor, not re-applied', () => {
    const { api, onZoom, onZoomRefused, onPlotClick } = mountGesture('time', {
      atTimeFloor: true
    })

    drag(api, [80, 30], [120, 30])

    expect(onZoom).not.toHaveBeenCalled()
    expect(onZoomRefused).toHaveBeenCalledTimes(1)
    expect(onPlotClick).not.toHaveBeenCalled()
  })

  // The served window is snapped to the data step, so it stays wider than the floor even at
  // maximum zoom. Reading the limit off it would leave the refusal unreachable.
  test('a window wider than the floor still zooms while the floor is not reported reached', () => {
    const flooredWindow: TimeRange = { start: 1000, end: 1060, step: 60 }
    const { api, onZoom, onZoomRefused } = mountGesture('time', {
      minTimeRange: 60,
      timeRange: flooredWindow,
      atTimeFloor: false
    })

    drag(api, [80, 30], [120, 30])

    expect(onZoomRefused).not.toHaveBeenCalled()
    expect(onZoom).toHaveBeenCalledTimes(1)
  })
})
