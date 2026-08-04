/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import { type Ref, computed, onBeforeUnmount, ref } from 'vue'

import {
  type SelectionPoints,
  clampPixelToPlot,
  clampSpan,
  selectionRect
} from './interaction/selection'
import type { TimeRange, ZoomMode, ZoomPayload } from './types'

// A drag shorter than this on the active axis is treated as a click, not a zoom.
const DRAG_THRESHOLD_PX = 4

function atFloor(span: number, floor: number | null): boolean {
  return floor !== null && span <= floor
}

export interface ZoomGestureOptions {
  zoomMode: () => ZoomMode
  timeRange: () => TimeRange
  minTimeRange: () => number | null
  minValueRange: () => number | null
  valueRange: () => { min: number; max: number } | null
  // Whether time zoom has nothing left to give. Supplied rather than derived: the drawn window
  // is snapped to the data step, so it never reaches minTimeRange however far the user zooms.
  atTimeFloor: () => boolean
  // Plot dimensions in CSS px.
  plotWidth: Ref<number>
  plotHeight: Ref<number>
  // The live scale instances the renderer draws with, used to invert pixels → time/value.
  xScale: ScaleTime<number, number>
  yScale: ScaleLinear<number, number>
  // Shared with the pan gesture, so the owning component (the canvas-ref owner) supplies it.
  plotCoords: (ev: MouseEvent) => { x: number; y: number } | null
  onZoom: (payload: ZoomPayload) => void
  // Fired instead of arming a drag when the view is already at the floor. Carries where the
  // press happened, in plot-relative pixels.
  onZoomRefused?: (point: { x: number; y: number }) => void
}

export function useZoomGesture(options: ZoomGestureOptions) {
  // Drag rectangle in plot-relative pixels; null = no drag in progress.
  const selection = ref<SelectionPoints | null>(null)

  // Infinity while auto-scaling: with no fixed window there is no floor to be at.
  function valueSpan(): number {
    const range = options.valueRange()
    return range === null ? Number.POSITIVE_INFINITY : range.max - range.min
  }

  function atFloorForMode(): boolean {
    if (options.zoomMode() === 'value') {
      return atFloor(valueSpan(), options.minValueRange())
    }
    return options.atTimeFloor()
  }

  const plotCursor = computed(() => {
    if (selection.value !== null) {
      return 'zoom-in'
    }
    return options.zoomMode() === 'value' ? 'ns-resize' : 'ew-resize'
  })
  const selectionBand = computed(() =>
    selection.value
      ? selectionRect(options.zoomMode(), selection.value, {
          left: 0,
          top: 0,
          width: options.plotWidth.value,
          height: options.plotHeight.value
        })
      : null
  )

  function onPlotMouseDown(ev: MouseEvent): void {
    if (ev.button !== 0) {
      return
    }
    const point = options.plotCoords(ev)
    if (!point) {
      return
    }
    // Refused before the drag is armed, so no band is ever drawn at the floor.
    if (atFloorForMode()) {
      options.onZoomRefused?.(point)
      return
    }
    selection.value = { x0: point.x, y0: point.y, x1: point.x, y1: point.y }
    window.addEventListener('mousemove', onPlotDragMove)
    window.addEventListener('mouseup', onPlotDragEnd)
  }

  function onPlotDragMove(ev: MouseEvent): void {
    const current = selection.value
    const point = options.plotCoords(ev)
    if (!current || !point) {
      return
    }
    selection.value = { ...current, x1: point.x, y1: point.y }
  }

  function onPlotDragEnd(): void {
    window.removeEventListener('mousemove', onPlotDragMove)
    window.removeEventListener('mouseup', onPlotDragEnd)
    const drag = selection.value
    selection.value = null
    if (!drag) {
      return
    }
    // Thresholding the clamped pixels keeps a drag whose visible part is sub-threshold a
    // click, however far outside the plot the cursor travelled.
    if (options.zoomMode() === 'value') {
      const fromY = clampPixelToPlot(drag.y0, options.plotHeight.value)
      const toY = clampPixelToPlot(drag.y1, options.plotHeight.value)
      if (Math.abs(toY - fromY) < DRAG_THRESHOLD_PX) {
        return
      }
      const valueA = options.yScale.invert(fromY)
      const valueB = options.yScale.invert(toY)
      const [min, max] = clampSpan(
        [Math.min(valueA, valueB), Math.max(valueA, valueB)],
        options.minValueRange()
      )
      options.onZoom({ timeRange: options.timeRange(), valueRange: { min, max } })
      return
    }
    const fromX = clampPixelToPlot(Math.min(drag.x0, drag.x1), options.plotWidth.value)
    const toX = clampPixelToPlot(Math.max(drag.x0, drag.x1), options.plotWidth.value)
    if (toX - fromX < DRAG_THRESHOLD_PX) {
      return
    }
    const range = options.timeRange()
    const timeA = (options.xScale.invert(fromX) as Date).getTime() / 1000
    const timeB = (options.xScale.invert(toX) as Date).getTime() / 1000
    const [start, end] = clampSpan([timeA, timeB], options.minTimeRange())
    // step is carried unchanged: a time-zoom-in redraws held data, so it only feeds the
    // tick-density heuristic, never a refetch.
    options.onZoom({ timeRange: { start, end, step: range.step } })
  }

  onBeforeUnmount(() => {
    window.removeEventListener('mousemove', onPlotDragMove)
    window.removeEventListener('mouseup', onPlotDragEnd)
  })

  return { selectionBand, plotCursor, onPlotMouseDown }
}
