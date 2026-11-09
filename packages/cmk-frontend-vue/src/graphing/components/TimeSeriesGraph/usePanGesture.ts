/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import useId from 'cmk-ui-library/lib/useId'
import type { ScaleTime } from 'd3-scale'
import { type Ref, computed, onBeforeUnmount, ref } from 'vue'

import {
  type MeasureLabel,
  type TimeAxisTick,
  computeTimeAxis
} from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'

import { navigableBounds, withinNavigableTime } from './interaction/timeBounds'
import type { PendingTimeRange, RequestedTimeRange, TimeRange } from './types'

// A drag shorter than this is treated as a click, not a pan (mirrors the zoom threshold).
const DRAG_THRESHOLD_PX = 4

const STEP_FRACTION_OF_SPAN = 0.25

export interface PanGestureOptions {
  panEnabled: () => boolean
  timeRange: () => TimeRange
  pendingTimeRange: () => PendingTimeRange | null
  measureLabel: MeasureLabel
  plotWidth: Ref<number>
  // The same instance the renderer draws with, so ruler ticks stay aligned with the plot.
  xScale: ScaleTime<number, number>
  plotCoords: (ev: MouseEvent) => { x: number; y: number } | null
  onStart: () => void
  onCommit: (timeRange: TimeRange) => void
}

export function usePanGesture(options: PanGestureOptions) {
  const dragging = ref(false)
  const dragDx = ref(0)
  const dragRulerTicks = ref<TimeAxisTick[]>([])
  let pressX = 0
  let rulerDxAtPress = 0
  const panClipId = `pan-clip-${useId()}`

  const pendingPanTimeRange = computed(() => {
    const pending = options.pendingTimeRange()
    return pending?.kind === 'pan' ? pending.timeRange : null
  })

  function rulerDxTo(target: RequestedTimeRange): number {
    const view = options.timeRange()
    const viewSpan = view.end - view.start
    return viewSpan > 0 ? -((target.start - view.start) / viewSpan) * options.plotWidth.value : 0
  }

  function rulerTicksAround(window: RequestedTimeRange): TimeAxisTick[] {
    const view = options.timeRange()
    const viewSpan = view.end - view.start
    if (viewSpan <= 0) {
      return []
    }
    const start = window.start - viewSpan
    const end = window.end + viewSpan
    const width = ((end - start) / viewSpan) * options.plotWidth.value
    return computeTimeAxis(start, end, width, options.measureLabel)
  }

  const panActive = computed(() => dragging.value || pendingPanTimeRange.value !== null)
  const panDx = computed(() => {
    if (dragging.value) {
      return rulerDxAtPress + dragDx.value
    }
    const pending = pendingPanTimeRange.value
    return pending === null ? 0 : rulerDxTo(pending)
  })
  const panRulerTicks = computed(() => {
    if (dragging.value) {
      return dragRulerTicks.value
    }
    const pending = pendingPanTimeRange.value
    return pending === null ? [] : rulerTicksAround(pending)
  })
  const panCursor = computed(() => (dragging.value ? 'grabbing' : 'ew-resize'))

  function panTickX(tick: TimeAxisTick): number {
    return options.xScale(new Date(tick.position * 1000))
  }

  function onPanMouseDown(ev: MouseEvent): void {
    if (ev.button !== 0 || !options.panEnabled()) {
      return
    }
    const point = options.plotCoords(ev)
    if (!point) {
      return
    }
    ev.preventDefault()
    const pending = pendingPanTimeRange.value
    rulerDxAtPress = pending === null ? 0 : rulerDxTo(pending)
    dragRulerTicks.value = rulerTicksAround(pending ?? options.timeRange())
    pressX = point.x
    dragDx.value = 0
    dragging.value = true
    options.onStart()
    window.addEventListener('mousemove', onPanDragMove)
    window.addEventListener('mouseup', onPanDragEnd)
  }

  function onPanDragMove(ev: MouseEvent): void {
    const point = options.plotCoords(ev)
    if (!point) {
      return
    }
    dragDx.value = point.x - pressX
  }

  // Commits only this drag's own travel: the host adds it to the window still on its way.
  function onPanDragEnd(): void {
    window.removeEventListener('mousemove', onPanDragMove)
    window.removeEventListener('mouseup', onPanDragEnd)
    const dx = dragDx.value
    dragging.value = false
    dragDx.value = 0
    dragRulerTicks.value = []
    if (Math.abs(dx) < DRAG_THRESHOLD_PX) {
      return
    }
    const range = options.timeRange()
    const span = range.end - range.start
    const shiftSeconds = -(dx / options.plotWidth.value) * span
    options.onCommit(
      withinNavigableTime(
        {
          start: range.start + shiftSeconds,
          end: range.end + shiftSeconds,
          step: range.step
        },
        navigableBounds()
      )
    )
  }

  function panBySteps(direction: -1 | 1): void {
    if (!options.panEnabled()) {
      return
    }
    const range = options.timeRange()
    const shiftSeconds = direction * (range.end - range.start) * STEP_FRACTION_OF_SPAN
    options.onCommit(
      withinNavigableTime(
        {
          start: range.start + shiftSeconds,
          end: range.end + shiftSeconds,
          step: range.step
        },
        navigableBounds()
      )
    )
  }

  onBeforeUnmount(() => {
    window.removeEventListener('mousemove', onPanDragMove)
    window.removeEventListener('mouseup', onPanDragEnd)
  })

  return {
    panActive,
    panDx,
    panRulerTicks,
    panClipId,
    panCursor,
    panTickX,
    onPanMouseDown,
    panBySteps
  }
}
