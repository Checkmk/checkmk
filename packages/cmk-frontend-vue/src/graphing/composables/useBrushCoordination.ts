/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, readonly, ref, watch } from 'vue'

import {
  DEFAULT_EDGE_FRACTION,
  overviewDomain,
  recenterOverviewDomain
} from '../components/GraphBrush/overviewRange'
import type { TimeRange } from '../components/TimeSeriesGraph/types'
import type { RequestedTimeRange, TimeInterval, TimeRangeCommitKind } from '../types'

export function useBrushCoordination(
  getNow: () => number,
  getRequestedRange: () => RequestedTimeRange,
  opts?: { edgeFraction?: number }
) {
  const edgeFraction = opts?.edgeFraction ?? DEFAULT_EDGE_FRACTION

  const initialRange = getRequestedRange()
  const graphRange: Ref<RequestedTimeRange> = ref({ ...initialRange })
  const brushWindow: Ref<TimeInterval> = ref({ start: initialRange.start, end: initialRange.end })
  const brushDomain: Ref<TimeInterval> = ref(overviewDomain(initialRange, getNow()))

  function setGraphRange(range: RequestedTimeRange): void {
    graphRange.value = { start: range.start, end: range.end }
  }
  function setBrushWindow(window: TimeInterval): void {
    brushWindow.value = { start: window.start, end: window.end }
  }
  function reseedBrushDomain(range: RequestedTimeRange): void {
    brushDomain.value = overviewDomain(range, getNow())
  }
  function syncBrushDomain(window: TimeInterval): void {
    brushDomain.value = recenterOverviewDomain(brushDomain.value, window, getNow(), edgeFraction)
  }

  function onExternalRange(range: RequestedTimeRange): void {
    setGraphRange(range)
    reseedBrushDomain(range)
    setBrushWindow(range)
  }

  function onBrushChange(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
    setGraphRange(range)
    setBrushWindow(range)
    if (kind === 'changed_timerange_span') {
      reseedBrushDomain(range)
    } else {
      syncBrushDomain(range)
    }
  }

  function onGraphView(view: TimeRange): void {
    setBrushWindow(view)
    syncBrushDomain(view)
  }

  // A range this composable did not itself commit came from outside, i.e. the global time
  // picker: that reseeds the strip, where its own commits only slide it.
  watch(getRequestedRange, (range) => {
    if (range.start !== graphRange.value.start || range.end !== graphRange.value.end) {
      onExternalRange(range)
    }
  })

  return {
    graphRange,
    brushDomain: readonly(brushDomain),
    brushWindow,
    setGraphRange,
    setBrushWindow,
    onExternalRange,
    onBrushChange,
    onGraphView
  }
}
