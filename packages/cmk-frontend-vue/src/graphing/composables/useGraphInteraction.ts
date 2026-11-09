/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import type {
  PinPayload,
  TimeRange,
  ValueRange,
  ZoomMode,
  ZoomPayload
} from '../components/TimeSeriesGraph'
import type { PanelKey, RangeChange, RequestedTimeRange, TimeRangeCommitKind } from '../types'
import { committedTimeRange, sameRequestedTimeRange } from '../utils/timeRange'
import { useGlobalPin } from './useGlobalPin'

// The per-graph interaction owner: the renderer is view-only (emit-and-wait) and this
// composable holds everything that moves it, plus the handlers that route the renderer's intents.
export function useGraphInteraction(
  getBaseline: () => TimeRange | undefined,
  getShowPin: () => boolean = () => false,
  getRequestedTimeRange?: () => RequestedTimeRange,
  onTimeRangeCommit?: (range: RequestedTimeRange, kind: TimeRangeCommitKind) => void,
  getAnsweredTimeRange?: () => RequestedTimeRange | undefined,
  getFailedTimeRange?: () => RequestedTimeRange | undefined
) {
  const peakZoomValueRange = ref<ValueRange | null>(null)
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

  function answeredTimeRange(): RequestedTimeRange | undefined {
    return getAnsweredTimeRange?.() ?? getRequestedTimeRange?.()
  }

  const dataAnswersRequest = computed(() => {
    const requested = getRequestedTimeRange?.()
    const answered = answeredTimeRange()
    return (
      requested === undefined ||
      answered === undefined ||
      sameRequestedTimeRange(requested, answered)
    )
  })

  const fetchFailed = computed(() => {
    const requested = getRequestedTimeRange?.()
    const failed = getFailedTimeRange?.()
    return (
      requested !== undefined && failed !== undefined && sameRequestedTimeRange(requested, failed)
    )
  })

  const awaitingData = computed(() => !dataAnswersRequest.value && !fetchFailed.value)

  // Tracks the committing zoom/pan session; resetTarget is the pre-session range, consumed by
  // onReset. It's the requested range, not the RRD-step-snapped baseline: publishing that would
  // drop the time picker to "Custom time range". Falls back to the baseline if nothing was
  // requested.
  const zoomSession: Ref<{ resetTarget: RequestedTimeRange } | null> = ref(null)
  const sessionSettled = ref(false)
  let peakZoomEndsWhenSettled = false

  const inspectionActive = computed(
    () => peakZoomValueRange.value !== null || (zoomSession.value !== null && sessionSettled.value)
  )

  function onSettled(): void {
    sessionSettled.value = zoomSession.value !== null
    if (peakZoomEndsWhenSettled) {
      peakZoomEndsWhenSettled = false
      peakZoomValueRange.value = null
    }
  }

  watch([getBaseline, awaitingData], () => {
    if (!awaitingData.value) {
      onSettled()
    }
  })

  function endPeakZoom(whenSettled: boolean): void {
    peakZoomEndsWhenSettled = whenSettled
    if (!whenSettled) {
      peakZoomValueRange.value = null
    }
  }

  function endSession(): void {
    zoomSession.value = null
    sessionSettled.value = false
  }

  // The host reports each change to the requested time range along with who made it, so this
  // never has to guess whether a change was its own commit echoing back.
  function onRangeChange(change: RangeChange, ownKey: PanelKey): void {
    if (change.source === ownKey) {
      return
    }
    if (change.source === 'time_picker') {
      abandonInspection()
      return
    }
    // Another group or a sibling panel moved the window: the reset target is stale, but a peak
    // zoom is still this graph's own business and stands.
    endSession()
  }

  function commitTimeRange(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
    // Canvas drag inverts pixels through a continuous scale, so the raw payload is usually
    // fractional, while the shared requestedTimeRange (and the backend) deal only with integers.
    const rounded: RequestedTimeRange = {
      start: Math.round(range.start),
      end: Math.round(range.end)
    }
    const requested = getRequestedTimeRange?.()
    // Hosts that refetch only a changed range would never land an unmoved window.
    if (
      requested !== undefined &&
      sameRequestedTimeRange(committedTimeRange(requested, rounded, kind), requested)
    ) {
      return
    }
    if (zoomSession.value === null) {
      const baseline = getBaseline()
      if (baseline !== undefined) {
        zoomSession.value = {
          resetTarget: requested ?? { start: baseline.start, end: baseline.end }
        }
      }
    }
    onTimeRangeCommit?.(rounded, kind)
  }

  function pannedTimeRange(panned: TimeRange): RequestedTimeRange {
    const drawn = getBaseline()
    const requested = getRequestedTimeRange?.()
    if (!awaitingData.value || drawn === undefined || requested === undefined) {
      return panned
    }
    const shiftSeconds = panned.start - drawn.start
    return { start: requested.start + shiftSeconds, end: requested.end + shiftSeconds }
  }

  function onZoom(payload: ZoomPayload): void {
    if (payload.valueRange) {
      peakZoomEndsWhenSettled = false
      peakZoomValueRange.value = payload.valueRange
      return
    }
    commitTimeRange(payload.timeRange, 'changed_timerange_span')
  }

  function onPan(payload: { timeRange: TimeRange }): void {
    commitTimeRange(pannedTimeRange(payload.timeRange), 'translated_timerange')
  }

  function abandonInspection(): void {
    endSession()
    endPeakZoom(awaitingData.value)
  }

  function onReset(): void {
    const endedSession = zoomSession.value
    endSession()
    if (endedSession === null) {
      endPeakZoom(awaitingData.value)
      return
    }
    const answered = answeredTimeRange()
    endPeakZoom(
      answered !== undefined && !sameRequestedTimeRange(endedSession.resetTarget, answered)
    )
    onTimeRangeCommit?.(endedSession.resetTarget, 'changed_timerange_span')
  }

  function onPinCreate(payload: PinPayload): void {
    setPin(payload.time)
  }

  return {
    viewValueRange: computed(() => peakZoomValueRange.value),
    inspectionActive,
    zoomMode,
    pinTime,
    onZoom,
    onPan,
    onBrush: commitTimeRange,
    onReset,
    onRangeChange,
    abandonInspection,
    onPinCreate,
    clearPin
  }
}
