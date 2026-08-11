/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import type { PinPayload, TimeRange, ZoomMode, ZoomPayload } from '../components/TimeSeriesGraph'
import type { RequestedTimeRange, TimeRangeCommitKind } from '../types'
import { sameRequestedTimeRange } from '../utils/timeRange'
import { useGlobalPin } from './useGlobalPin'
import { useGraphView } from './useGraphView'

// Stands in for the baseline until the first data fetch delivers one; hosts gate
// their renderer on their own timeRange, so this view is never rendered.
const EMPTY_TIME_RANGE: TimeRange = { start: 0, end: 0, step: 1 }

// The per-graph interaction owner: the renderer is view-only (emit-and-wait) and this
// composable holds everything that moves it — the view state machine, the zoom mode,
// and the pin — plus the handlers that route the renderer's intents into the machine.
export function useGraphInteraction(
  getBaseline: () => TimeRange | undefined,
  getShowPin: () => boolean = () => false,
  getRequestedTimeRange?: () => RequestedTimeRange,
  onTimeRangeCommit?: (range: RequestedTimeRange, kind: TimeRangeCommitKind) => void
) {
  const {
    timeRange: viewTimeRange,
    valueRange: viewValueRange,
    inspectionActive: viewInspectionActive,
    handleIntent
  } = useGraphView(() => getBaseline() ?? EMPTY_TIME_RANGE)

  const zoomMode = ref<ZoomMode>('time')

  const { pinTime, ensurePinLoaded, setPin, clearPin } = useGlobalPin()

  watch(
    getShowPin,
    (showPin) => {
      if (showPin) {
        ensurePinLoaded()
      }
    },
    { immediate: true }
  )

  // Tracks the current committing zoom/pan session: resetTarget is the range that was in
  // effect right before it started (consumed by onReset), lastCommittedRequest is the range
  // this session last asked onTimeRangeCommit to publish. The two always start and end
  // together, hence one nullable object rather than two separately-nullable refs.
  //
  // resetTarget is the range the page asked for, not the baseline the backend answered with:
  // the served range is snapped to the RRD step, so publishing it would end the reset on a
  // range that is a step longer than any of the time picker's presets and drop the picker to
  // "Custom time range". The baseline is the fallback for hosts that request nothing.
  const zoomSession: Ref<{
    resetTarget: RequestedTimeRange
    lastCommittedRequest: RequestedTimeRange
  } | null> = ref(null)
  const inspectionActive = computed(() => viewInspectionActive.value || zoomSession.value !== null)

  watch(getBaseline, (baseline) => {
    if (baseline !== undefined) {
      handleIntent({ kind: 'rangeCommit', timeRange: baseline })
    }
  })

  // A new requested time range that doesn't equal the last request committed from within this
  // composable indicates an outer change, i.e. triggered through the global time picker.
  // In this case we abandon the current zoom session - setting it to null.
  if (getRequestedTimeRange) {
    watch(getRequestedTimeRange, (current) => {
      if (
        zoomSession.value !== null &&
        !sameRequestedTimeRange(current, zoomSession.value.lastCommittedRequest)
      ) {
        zoomSession.value = null
      }
    })
  }

  function commitTimeRange(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
    // Canvas drag inverts pixels through a continuous scale, so the raw payload is usually
    // fractional, while the shared requestedTimeRange (and the backend) deal only with integers.
    const rounded: RequestedTimeRange = {
      start: Math.round(range.start),
      end: Math.round(range.end)
    }
    if (zoomSession.value === null) {
      const baseline = getBaseline()
      if (baseline !== undefined) {
        zoomSession.value = {
          resetTarget: getRequestedTimeRange?.() ?? { start: baseline.start, end: baseline.end },
          lastCommittedRequest: rounded
        }
      }
    } else {
      zoomSession.value = { ...zoomSession.value, lastCommittedRequest: rounded }
    }
    onTimeRangeCommit?.(rounded, kind)
  }

  function onZoom(payload: ZoomPayload): void {
    handleIntent({ kind: 'zoomTransient', ...payload })
    if (!payload.valueRange) {
      commitTimeRange(payload.timeRange, 'changed_timerange_span')
    }
  }

  function onPan(payload: { timeRange: TimeRange }): void {
    handleIntent({ kind: 'pan', timeRange: payload.timeRange })
    commitTimeRange(payload.timeRange, 'translated_timerange')
  }

  function abandonInspection(): void {
    handleIntent({ kind: 'reset' })
    zoomSession.value = null
  }

  function onReset(): void {
    const endedSession = zoomSession.value
    abandonInspection()
    if (endedSession !== null) {
      onTimeRangeCommit?.(endedSession.resetTarget, 'changed_timerange_span')
    }
  }

  function onPinCreate(payload: PinPayload): void {
    setPin(payload.time)
  }

  return {
    viewTimeRange,
    viewValueRange,
    inspectionActive,
    zoomMode,
    pinTime,
    onZoom,
    onPan,
    onBrush: commitTimeRange,
    onReset,
    abandonInspection,
    onPinCreate,
    clearPin
  }
}
