/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, type WritableComputedRef, computed, watch } from 'vue'

import { urlHandler } from '@/dashboard/utils'
import {
  initGlobalTime,
  restartGlobalTime,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import {
  type TimeRangeVariables,
  liveTimeRangeVariables,
  timeStartFromUrl,
  useTimeRangeVariables
} from '@/graphing/GlobalTimePicker/timeRangeUrl'
import { useGlobalTimePickerRange } from '@/graphing/GlobalTimePicker/useGlobalTimePickerRange'

export interface DashboardTimeControl {
  /** The window every widget draws, shared with the rest of the page. */
  range: WritableComputedRef<DateTimeRange>
  refreshTick: ComputedRef<number>
  /** The variables that carry the shared range, `null` for the default; the address bar keeps
   * them for the way back.
   */
  timeRangeVariables: ComputedRef<TimeRangeVariables | null>
  /** A widget picked its own window: it becomes everyone's, and stays put until Resume. */
  updateTimeRange: (range: DateTimeRange) => void
  /** Back to the time and refresh that a fresh link to the dashboard starts with. */
  resetTimeControl: () => void
}

export function useDashboardTimeControl(
  globalTimePicker: GlobalTimePickerProps,
  live?: boolean
): DashboardTimeControl {
  const { range } = useGlobalTimePickerRange(globalTimePicker.default_time_range)
  const { refreshTick, pauseRefresh } = useGlobalRefresh()
  const { setActiveTimeRange } = useGlobalTimeRange()

  const startsLive = live ?? globalTimePicker.refresh.starts_live
  initGlobalTime({
    intervalSeconds: globalTimePicker.refresh.interval_seconds,
    start: timeStartFromUrl(new URL(window.location.href), startsLive)
  })

  const defaultVariables = liveTimeRangeVariables(globalTimePicker.default_time_range)
  const rangeVariables = useTimeRangeVariables()
  const timeRangeVariables = computed(() => {
    const variables = rangeVariables.value
    return variables?.from === defaultVariables.from && variables.to === defaultVariables.to
      ? null
      : variables
  })
  watch(timeRangeVariables, (variables) =>
    urlHandler.updateCurrentUrl(urlHandler.withTimeRange(new URL(window.location.href), variables))
  )

  return {
    range,
    refreshTick,
    timeRangeVariables,
    updateTimeRange: (newRange: DateTimeRange) => {
      setActiveTimeRange(newRange, 'external')
      pauseRefresh()
    },
    resetTimeControl: () =>
      restartGlobalTime({
        intervalSeconds: globalTimePicker.refresh.interval_seconds,
        seconds: globalTimePicker.default_time_range,
        live: startsLive
      })
  }
}
