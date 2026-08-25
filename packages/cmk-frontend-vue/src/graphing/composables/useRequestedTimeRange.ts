/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate, getLocalTimeZone } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, computed, ref, watch } from 'vue'

import { useGlobalTimeRange } from '../GlobalTimePicker/globalTimeState'
import type { RequestedTimeRange } from '../types'
import { sameRequestedTimeRange } from '../utils/timeRange'

function toRequestedTimeRange(range: DateTimeRange): RequestedTimeRange {
  return {
    start: Math.floor(range.from.toDate().getTime() / 1000),
    end: Math.floor(range.to.toDate().getTime() / 1000)
  }
}

// The reverse of toRequestedTimeRange. A RequestedTimeRange has no timezone of its own
// (it's plain unix seconds), so the currently active range's zone is reused for round-
// tripping; falls back to the browser zone if the picker hasn't published one yet.
function toDateTimeRange(range: RequestedTimeRange, timeZone: string): DateTimeRange {
  return {
    from: fromDate(new Date(range.start * 1000), timeZone),
    to: fromDate(new Date(range.end * 1000), timeZone)
  }
}

const DEFAULT_RANGE_SECONDS = 4 * 3600

export interface RequestedTimeRangeState {
  requestedTimeRange: ComputedRef<RequestedTimeRange>
  setRequestedTimeRange: (range: RequestedTimeRange) => void
  timePickerRequests: ComputedRef<number>
}

/**
 * The requested (user-chosen) time range for a graph data fetch owner.
 *
 * Seeded from the page's global time picker if one has already published a range,
 * otherwise from `initial` (default: the last four hours); follows every subsequent
 * picker change.
 *
 * Call this from the component that owns the data fetch (e.g. a graph group or a
 * standalone panel host), not from presentational components like GraphPanel.
 */
export function useRequestedTimeRange(initial?: RequestedTimeRange): RequestedTimeRangeState {
  const { activeTimeRangeState, setActiveTimeRange } = useGlobalTimeRange()

  function fallbackRange(): RequestedTimeRange {
    const now = Math.floor(Date.now() / 1000)
    return { start: now - DEFAULT_RANGE_SECONDS, end: now }
  }

  const active = activeTimeRangeState.value
  const request = ref<RequestedTimeRange>(
    active.range === null
      ? initial === undefined
        ? fallbackRange()
        : { ...initial }
      : toRequestedTimeRange(active.range)
  )
  const timePickerRequests = ref(0)

  // Mount order of the picker and the fetch owner is DOM-driven: if the picker mounts
  // later, its initial publish arrives through this watch and replaces the seed.
  watch(activeTimeRangeState, (state) => {
    if (state.range === null) {
      return
    }
    const next = toRequestedTimeRange(state.range)
    if (sameRequestedTimeRange(next, request.value)) {
      return
    }
    request.value = next
    if (state.origin === 'time_picker') {
      timePickerRequests.value += 1
    }
  })

  function setRequestedTimeRange(range: RequestedTimeRange): void {
    request.value = { start: range.start, end: range.end }
  }

  watch(request, (range) => {
    const published = activeTimeRangeState.value.range
    if (published !== null && sameRequestedTimeRange(range, toRequestedTimeRange(published))) {
      return
    }
    const timeZone = published?.from.timeZone ?? getLocalTimeZone()
    setActiveTimeRange(toDateTimeRange(range, timeZone), 'external')
  })

  return {
    requestedTimeRange: computed(() => request.value),
    setRequestedTimeRange,
    timePickerRequests: computed(() => timePickerRequests.value)
  }
}
