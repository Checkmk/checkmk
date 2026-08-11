/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, computed, shallowRef } from 'vue'

import { useGlobalRefresh } from '../GlobalRefreshControl/useGlobalRefresh'
import { endsInThePast } from './private/timeRange'

export type TimeRangeOrigin = 'time_picker' | 'external'

export type ActiveTimeRange = DateTimeRange | null

export interface ActiveTimeRangeState {
  range: ActiveTimeRange
  origin: TimeRangeOrigin
}

// Singleton shared across the page's Vue apps. Write only via setActiveTimeRange.
// Shallow ref, always replace the value to trigger reactive updates.
// Could move to a DOM-event bus if the bundle is split.
const state = shallowRef<ActiveTimeRangeState>({ range: null, origin: 'time_picker' })

// Read-only accessor for the current time range.
const activeTimeRangeState = computed(() => state.value)
const activeTimeRange = computed(() => state.value.range)

function setActiveTimeRange(value: ActiveTimeRange, origin: TimeRangeOrigin): void {
  state.value = { range: value, origin }
  pauseRefreshForRangeEndingInThePast(value)
}

// Such a window cannot gain new data. One-way: resuming stays the user's call.
function pauseRefreshForRangeEndingInThePast(value: ActiveTimeRange): void {
  if (value !== null && endsInThePast(value)) {
    useGlobalRefresh().setRefreshPaused(true)
  }
}

export interface GlobalTimeRange {
  activeTimeRange: ComputedRef<ActiveTimeRange>
  activeTimeRangeState: ComputedRef<ActiveTimeRangeState>
  setActiveTimeRange: (value: ActiveTimeRange, origin: TimeRangeOrigin) => void
}

export function useGlobalTimeRange(): GlobalTimeRange {
  return { activeTimeRange, activeTimeRangeState, setActiveTimeRange }
}
