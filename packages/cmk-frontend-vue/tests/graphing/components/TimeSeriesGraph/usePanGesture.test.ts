/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { scaleLinear, scaleTime } from 'd3-scale'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import type { TimeRange } from '@/graphing/components/TimeSeriesGraph/types'
import { usePanGesture } from '@/graphing/components/TimeSeriesGraph/usePanGesture'
import { useZoomGesture } from '@/graphing/components/TimeSeriesGraph/useZoomGesture'

// Well inside the navigable axis, so no test below pans into a bound it did not mean to.
const TIME_RANGE: TimeRange = { start: 1_700_000_000, end: 1_700_001_000, step: 60 }
const SPAN_SECONDS = 1_000
const PLOT_WIDTH = 200
const PLOT_HEIGHT = 100
// Any y inside the plot; the pan gesture reads the cursor's x only.
const CURSOR_Y = 90
const PRESS_X = 100
const DRAG_DISTANCE_PX = 40
// DRAG_DISTANCE_PX of a PLOT_WIDTH plot spanning SPAN_SECONDS.
const DRAG_SECONDS = 200

type PanGesture = ReturnType<typeof usePanGesture>
type ZoomGesture = ReturnType<typeof useZoomGesture>

function buildScales(range: TimeRange = TIME_RANGE) {
  const xScale = scaleTime()
    .domain([new Date(range.start * 1000), new Date(range.end * 1000)])
    .range([0, PLOT_WIDTH])
  const yScale = scaleLinear().domain([0, 100]).range([PLOT_HEIGHT, 0])
  return { xScale, yScale }
}

// useId and onBeforeUnmount need a mounted harness.
function mountPan(options: { panEnabled?: boolean; timeRange?: TimeRange } = {}) {
  const timeRange = options.timeRange ?? TIME_RANGE
  const onCommit = vi.fn()
  const onStart = vi.fn()
  const { xScale } = buildScales(timeRange)
  let api!: PanGesture
  const harness = defineComponent({
    setup() {
      api = usePanGesture({
        panEnabled: () => options.panEnabled ?? true,
        timeRange: () => timeRange,
        measureLabel: (text: string) => text.length * 6,
        plotWidth: ref(PLOT_WIDTH),
        xScale,
        plotCoords: (ev: MouseEvent) => ({ x: ev.clientX, y: ev.clientY }),
        onStart,
        onCommit
      })
      return () => h('div')
    }
  })
  render(harness)
  return { api, onCommit, onStart }
}

// The two gestures share the plot-coordinate mapping, so this is where cross-talk shows up.
function mountBothGestures() {
  const onZoom = vi.fn()
  const onCommit = vi.fn()
  const { xScale, yScale } = buildScales()
  let pan!: PanGesture
  let zoom!: ZoomGesture
  const plotCoords = (ev: MouseEvent) => ({ x: ev.clientX, y: ev.clientY })
  const harness = defineComponent({
    setup() {
      pan = usePanGesture({
        panEnabled: () => true,
        timeRange: () => TIME_RANGE,
        measureLabel: (text: string) => text.length * 6,
        plotWidth: ref(PLOT_WIDTH),
        xScale,
        plotCoords,
        onStart: () => {},
        onCommit
      })
      zoom = useZoomGesture({
        zoomMode: () => 'time',
        timeRange: () => TIME_RANGE,
        minTimeRange: () => null,
        minValueRange: () => null,
        valueRange: () => null,
        atTimeFloor: () => false,
        plotWidth: ref(PLOT_WIDTH),
        plotHeight: ref(PLOT_HEIGHT),
        xScale,
        yScale,
        plotCoords,
        onZoom
      })
      return () => h('div')
    }
  })
  render(harness)
  return { pan, zoom, onZoom, onCommit }
}

function moveTo(x: number): void {
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: CURSOR_Y }))
}

function releaseMouse(): void {
  window.dispatchEvent(new MouseEvent('mouseup'))
}

/** Press and travel without releasing, leaving the gesture mid-drag. */
function startPan(api: PanGesture, fromX: number, toX: number): void {
  api.onPanMouseDown(new MouseEvent('mousedown', { button: 0, clientX: fromX, clientY: CURSOR_Y }))
  moveTo(toX)
}

/** A whole drag: press, travel, release. */
function pan(api: PanGesture, fromX: number, toX: number): void {
  startPan(api, fromX, toX)
  releaseMouse()
}

function zoomDrag(api: ZoomGesture, fromX: number, toX: number): void {
  api.onPlotMouseDown(new MouseEvent('mousedown', { button: 0, clientX: fromX, clientY: 30 }))
  moveTo(toX)
  releaseMouse()
}

/** The single range the gesture committed. */
function committedRange(onCommit: ReturnType<typeof mountPan>['onCommit']): TimeRange {
  expect(onCommit).toHaveBeenCalledTimes(1)
  return onCommit.mock.calls[0]![0] as TimeRange
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePanGesture — the end of the navigable axis', () => {
  function rangeEndingToday(spanSeconds: number): TimeRange {
    const endOfToday = new Date()
    endOfToday.setHours(23, 59, 59, 999)
    const end = Math.floor(endOfToday.getTime() / 1000)
    return { start: end - spanSeconds, end, step: 60 }
  }

  test('a drag towards the future stops at the end of the current day', () => {
    const { api, onCommit } = mountPan({ timeRange: rangeEndingToday(SPAN_SECONDS) })

    pan(api, PRESS_X, PRESS_X - DRAG_DISTANCE_PX)

    const endOfToday = new Date()
    endOfToday.setHours(23, 59, 59, 999)
    expect(committedRange(onCommit).end).toBe(Math.floor(endOfToday.getTime() / 1000))
  })

  test('a window held at the bound keeps its span', () => {
    const { api, onCommit } = mountPan({ timeRange: rangeEndingToday(SPAN_SECONDS) })

    pan(api, PRESS_X, PRESS_X - DRAG_DISTANCE_PX)

    const committed = committedRange(onCommit)
    expect(committed.end - committed.start).toBe(SPAN_SECONDS)
  })
})

describe('usePanGesture', () => {
  test('a drag to the right shifts the window back by the time the drag covers', () => {
    const { api, onCommit } = mountPan()

    pan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(TIME_RANGE.start - committedRange(onCommit).start).toBe(DRAG_SECONDS)
  })

  test('a drag to the left shifts the window forward by the same amount', () => {
    const { api, onCommit } = mountPan()

    pan(api, PRESS_X, PRESS_X - DRAG_DISTANCE_PX)

    expect(committedRange(onCommit).start - TIME_RANGE.start).toBe(DRAG_SECONDS)
  })

  test('panning moves the window without resizing it or changing its resolution', () => {
    const { api, onCommit } = mountPan()

    pan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    const committed = committedRange(onCommit)
    expect(committed.end - committed.start).toBe(SPAN_SECONDS)
    expect(committed.step).toBe(TIME_RANGE.step)
  })

  test('a sub-threshold drag is treated as a click and commits nothing', () => {
    const { api, onCommit } = mountPan()

    pan(api, PRESS_X, PRESS_X + 2)

    expect(onCommit).not.toHaveBeenCalled()
  })

  test('an unfinished drag commits nothing, however many frames it spans', () => {
    const { api, onCommit } = mountPan()

    startPan(api, PRESS_X, PRESS_X + 10)
    moveTo(125)
    moveTo(140)

    // Committing here would fire a data request per frame.
    expect(onCommit).not.toHaveBeenCalled()
  })

  test('releasing after several frames commits exactly once', () => {
    const { api, onCommit } = mountPan()
    startPan(api, PRESS_X, PRESS_X + 10)
    moveTo(125)
    moveTo(140)

    releaseMouse()

    expect(onCommit).toHaveBeenCalledTimes(1)
  })

  test('the drag offset tracks the cursor while the drag lasts', () => {
    const { api } = mountPan()

    startPan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(api.panActive.value).toBe(true)
    expect(api.panDx.value).toBe(DRAG_DISTANCE_PX)
  })

  test('releasing ends the drag and clears its offset', () => {
    const { api } = mountPan()
    startPan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    releaseMouse()

    expect(api.panActive.value).toBe(false)
    expect(api.panDx.value).toBe(0)
  })

  test('the sliding ruler holds no ticks before a drag starts', () => {
    const { api } = mountPan()

    expect(api.panRulerTicks.value).toEqual([])
  })

  test('the sliding ruler is populated while the drag lasts', () => {
    const { api } = mountPan()

    startPan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(api.panRulerTicks.value.length).toBeGreaterThan(0)
  })

  test('releasing empties the sliding ruler again', () => {
    const { api } = mountPan()
    startPan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    releaseMouse()

    expect(api.panRulerTicks.value).toEqual([])
  })

  test('starting a pan announces the gesture so the host can drop the hover', () => {
    const { api, onStart } = mountPan()

    startPan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(onStart).toHaveBeenCalledTimes(1)
  })

  test('the gesture is inert when panning is disabled', () => {
    const { api, onCommit, onStart } = mountPan({ panEnabled: false })

    pan(api, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(api.panActive.value).toBe(false)
    expect(onStart).not.toHaveBeenCalled()
    expect(onCommit).not.toHaveBeenCalled()
  })
})

describe('usePanGesture — disambiguated from the zoom gesture', () => {
  test('no zoom selection band is drawn while panning', () => {
    const { pan: panApi, zoom } = mountBothGestures()

    startPan(panApi, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(zoom.selectionBand.value).toBeNull()
  })

  test('a completed pan commits a pan and never a zoom', () => {
    const { pan: panApi, onZoom, onCommit } = mountBothGestures()

    pan(panApi, PRESS_X, PRESS_X + DRAG_DISTANCE_PX)

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onZoom).not.toHaveBeenCalled()
  })

  test('a zoom drag never activates the pan', () => {
    const { zoom, onZoom, onCommit } = mountBothGestures()

    zoomDrag(zoom, 40, 120)

    expect(onZoom).toHaveBeenCalledTimes(1)
    expect(onCommit).not.toHaveBeenCalled()
  })

  test('a wheel event neither pans nor zooms', () => {
    const { pan: panApi, zoom, onZoom, onCommit } = mountBothGestures()

    window.dispatchEvent(new WheelEvent('wheel', { deltaY: -240, clientX: 100, clientY: 50 }))

    expect(panApi.panActive.value).toBe(false)
    expect(zoom.selectionBand.value).toBeNull()
    expect(onZoom).not.toHaveBeenCalled()
    expect(onCommit).not.toHaveBeenCalled()
  })
})
