/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type WritableComputedRef, computed } from 'vue'

import { useGlobalTimeRange } from './globalTimeState'
import { rollingRange } from './private/timeRange'

export interface GlobalTimePickerRange {
  /** Writing to it publishes the window to every graph on the page. */
  range: WritableComputedRef<DateTimeRange>
  returnToLiveMonitoring: () => void
}

export function useGlobalTimePickerRange(defaultTimeRangeSeconds: number): GlobalTimePickerRange {
  const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()

  const fallback = rollingRange(defaultTimeRangeSeconds)

  if (activeTimeRange.value === null) {
    setActiveTimeRange(fallback, 'time_picker')
  }

  return {
    range: computed<DateTimeRange>({
      get: () => activeTimeRange.value ?? fallback,
      set: (value: DateTimeRange) => setActiveTimeRange(value, 'time_picker')
    }),
    returnToLiveMonitoring: () =>
      setActiveTimeRange(rollingRange(defaultTimeRangeSeconds), 'time_picker')
  }
}
