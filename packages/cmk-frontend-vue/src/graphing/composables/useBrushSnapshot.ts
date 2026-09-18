/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, shallowRef, watch } from 'vue'

import {
  DEFAULT_EDGE_FRACTION,
  overviewDomain,
  recenterOverviewDomain
} from '../components/GraphBrush/overviewRange'
import { EARLIEST_NAVIGABLE_SECONDS } from '../components/TimeSeriesGraph/interaction/timeBounds'
import type { BrushSnapshot, RequestedTimeRange, TimeInterval, TimeRangeCommitKind } from '../types'
import { sameRequestedTimeRange } from '../utils/timeRange'

interface AnsweredSnapshot<TData> {
  requestedDomain: TimeInterval
  snapshot: BrushSnapshot<TData>
}

export interface FetchedOverview<TData> {
  /** Must be the `requestedDomain` this answers. */
  requestedDomain: TimeInterval
  /** The same extent, unless the surface snapped it onto its data's grid. */
  drawnDomain: TimeInterval
  data: TData
}

export interface UseBrushSnapshot<TData> {
  requestedDomain: Readonly<Ref<TimeInterval>>
  snapshot: Readonly<Ref<BrushSnapshot<TData> | null>>
  isPending: Readonly<Ref<boolean>>
  /**
   * A surface's own supersede check does not stand in for the one here: the designer's counter
   * only advances when the next fetch starts, which its debounce defers.
   */
  onOverviewFetched: (overview: FetchedOverview<TData>) => void
  onRangeCommitted: (range: RequestedTimeRange, kind: TimeRangeCommitKind) => void
}

function fitsWithin(window: TimeInterval, domain: TimeInterval): boolean {
  return window.start >= domain.start && window.end <= domain.end
}

// Snapping both ends onto a step wider than the extent itself collapses it, and every mark would
// then be placed by a division by zero.
function drawableExtent(drawn: TimeInterval, fallback: TimeInterval): TimeInterval {
  return drawn.end > drawn.start ? drawn : fallback
}

/**
 * What the user asks for is known at once; the strip's waveform arrives a fetch later. Drawing a
 * window from one and an extent from the other is what makes the bar jump, so the two are kept
 * apart: `requestedDomain` moves immediately, the snapshot only when its data lands.
 */
export function useBrushSnapshot<TData>(options: {
  getNow: () => number
  getRequestedTimeRange: () => RequestedTimeRange
  edgeFraction?: number
}): UseBrushSnapshot<TData> {
  const edgeFraction = options.edgeFraction ?? DEFAULT_EDGE_FRACTION

  const initialRange = options.getRequestedTimeRange()
  const requestedDomain = shallowRef<TimeInterval>(
    overviewDomain(initialRange, options.getNow(), EARLIEST_NAVIGABLE_SECONDS)
  )
  const pendingWindow = shallowRef<TimeInterval>({ ...initialRange })
  const answered = shallowRef<AnsweredSnapshot<TData> | null>(null)

  function onOverviewFetched(overview: FetchedOverview<TData>): void {
    if (!sameRequestedTimeRange(overview.requestedDomain, requestedDomain.value)) {
      return
    }
    answered.value = {
      requestedDomain: overview.requestedDomain,
      snapshot: {
        drawnDomain: drawableExtent(overview.drawnDomain, overview.requestedDomain),
        window: pendingWindow.value,
        data: overview.data
      }
    }
  }

  // Recentred from `requestedDomain`, not from the drawn extent: that one is snapped to its data's
  // grid, and feeding it back drifts the request by a step per translation.
  function nextRequestedDomain(window: TimeInterval, kind: TimeRangeCommitKind): TimeInterval {
    return kind === 'changed_timerange_span'
      ? overviewDomain(window, options.getNow(), EARLIEST_NAVIGABLE_SECONDS)
      : recenterOverviewDomain(
          requestedDomain.value,
          window,
          options.getNow(),
          edgeFraction,
          EARLIEST_NAVIGABLE_SECONDS
        )
  }

  function onRangeCommitted(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
    const window: TimeInterval = { start: range.start, end: range.end }
    const current = answered.value
    requestedDomain.value = nextRequestedDomain(window, kind)
    pendingWindow.value = window
    // A brush drag is clamped to the strip it is drawn in, so a release always fits and stays put.
    if (current !== null && fitsWithin(window, current.snapshot.drawnDomain)) {
      answered.value = { ...current, snapshot: { ...current.snapshot, window } }
    }
  }

  const cameFromOutside = (range: RequestedTimeRange): boolean =>
    !sameRequestedTimeRange(range, pendingWindow.value)

  watch(options.getRequestedTimeRange, (range) => {
    if (cameFromOutside(range)) {
      onRangeCommitted(range, 'changed_timerange_span')
    }
  })

  return {
    requestedDomain: computed(() => requestedDomain.value),
    snapshot: computed(() => answered.value?.snapshot ?? null),
    isPending: computed(
      () =>
        answered.value === null ||
        !sameRequestedTimeRange(answered.value.requestedDomain, requestedDomain.value)
    ),
    onOverviewFetched,
    onRangeCommitted
  }
}
