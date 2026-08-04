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

import { endOfCurrentDaySeconds, withinNavigableTime } from './interaction/timeBounds'
import type { TimeRange } from './types'

// A drag shorter than this is treated as a click, not a pan (mirrors the zoom threshold).
const DRAG_THRESHOLD_PX = 4

// The ruler extends one span either side of the visible window so labels slide in during a drag.
const PAN_RULER_SPANS = 3

const STEP_FRACTION_OF_SPAN = 0.25

export interface PanGestureOptions {
  panEnabled: () => boolean
  timeRange: () => TimeRange
  measureLabel: MeasureLabel
  plotWidth: Ref<number>
  // The same instance the renderer draws with, so ruler ticks stay aligned with the plot.
  xScale: ScaleTime<number, number>
  plotCoords: (ev: MouseEvent) => { x: number; y: number } | null
  onStart: () => void
  onCommit: (timeRange: TimeRange) => void
}

export function usePanGesture(options: PanGestureOptions) {
  const panDx = ref(0)
  const panActive = ref(false)
  const panRulerTicks = ref<TimeAxisTick[]>([])
  let panAnchorX = 0
  const panCursor = computed(() => (panActive.value ? 'grabbing' : 'ew-resize'))
  const panClipId = `pan-clip-${useId()}`

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
    const range = options.timeRange()
    const span = range.end - range.start
    panRulerTicks.value = computeTimeAxis(
      range.start - span,
      range.end + span,
      options.plotWidth.value * PAN_RULER_SPANS,
      range.step,
      options.measureLabel
    )
    panAnchorX = point.x
    panDx.value = 0
    panActive.value = true
    options.onStart()
    window.addEventListener('mousemove', onPanDragMove)
    window.addEventListener('mouseup', onPanDragEnd)
  }

  function onPanDragMove(ev: MouseEvent): void {
    const point = options.plotCoords(ev)
    if (!point) {
      return
    }
    panDx.value = point.x - panAnchorX
  }

  function onPanDragEnd(): void {
    window.removeEventListener('mousemove', onPanDragMove)
    window.removeEventListener('mouseup', onPanDragEnd)
    const dx = panDx.value
    panActive.value = false
    panDx.value = 0
    panRulerTicks.value = []
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
        endOfCurrentDaySeconds()
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
        endOfCurrentDaySeconds()
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
