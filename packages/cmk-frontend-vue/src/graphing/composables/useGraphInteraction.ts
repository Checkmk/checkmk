/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import type { PinPayload, TimeRange, ZoomMode, ZoomPayload } from '../components/TimeSeriesGraph'
import type { PanelKey, RangeChange, RequestedTimeRange, TimeRangeCommitKind } from '../types'
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
    transientTimeRange,
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

  // Tracks the committing zoom/pan session; resetTarget is the pre-session range, consumed by
  // onReset. It's the requested range, not the RRD-step-snapped baseline: publishing that would
  // drop the time picker to "Custom time range". Falls back to the baseline if nothing was
  // requested.
  const zoomSession: Ref<{ resetTarget: RequestedTimeRange } | null> = ref(null)
  const inspectionActive = computed(() => viewInspectionActive.value || zoomSession.value !== null)

  watch(getBaseline, (baseline) => {
    if (baseline !== undefined) {
      handleIntent({ kind: 'rangeCommit', timeRange: baseline })
    }
  })

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
    zoomSession.value = null
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
          resetTarget: getRequestedTimeRange?.() ?? { start: baseline.start, end: baseline.end }
        }
      }
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
    transientTimeRange,
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
