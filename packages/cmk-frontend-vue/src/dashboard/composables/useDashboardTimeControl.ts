/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import type { ComputedRef, WritableComputedRef } from 'vue'

import {
  initGlobalRefresh,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { useGlobalTimePickerRange } from '@/graphing/GlobalTimePicker/useGlobalTimePickerRange'

export interface DashboardTimeControl {
  /** The window every widget draws, shared with the rest of the page. */
  range: WritableComputedRef<DateTimeRange>
  refreshTick: ComputedRef<number>
  /** A widget picked its own window: it becomes everyone's, and stays put until Resume. */
  updateTimeRange: (range: DateTimeRange) => void
}

export function useDashboardTimeControl(
  globalTimePicker: GlobalTimePickerProps,
  live?: boolean
): DashboardTimeControl {
  const { range } = useGlobalTimePickerRange(globalTimePicker.default_time_range)
  const { refreshTick, pauseRefresh } = useGlobalRefresh()
  const { setActiveTimeRange } = useGlobalTimeRange()

  initGlobalRefresh({
    intervalSeconds: globalTimePicker.refresh.interval_seconds,
    live: live ?? globalTimePicker.refresh.starts_live
  })

  return {
    range,
    refreshTick,
    updateTimeRange: (newRange: DateTimeRange) => {
      setActiveTimeRange(newRange, 'external')
      pauseRefresh()
    }
  }
}
