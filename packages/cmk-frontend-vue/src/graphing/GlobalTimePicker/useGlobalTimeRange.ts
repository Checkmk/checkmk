/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, computed, shallowRef } from 'vue'

import { useGlobalRefresh } from '../GlobalRefreshControl/useGlobalRefresh'
import { endsInThePast } from './private/timeRange'

export type ActiveTimeRange = DateTimeRange | null

// Singleton shared across the page's Vue apps. Write only via setActiveTimeRange.
// Shallow ref, always replace the value to trigger reactive updates.
// Could move to a DOM-event bus if the bundle is split.
const rangeState = shallowRef<ActiveTimeRange>(null)

// Read-only accessor for the current time range.
const activeTimeRange = computed(() => rangeState.value)

function setActiveTimeRange(value: ActiveTimeRange): void {
  rangeState.value = value
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
  setActiveTimeRange: (value: ActiveTimeRange) => void
}

export function useGlobalTimeRange(): GlobalTimeRange {
  return { activeTimeRange, setActiveTimeRange }
}
