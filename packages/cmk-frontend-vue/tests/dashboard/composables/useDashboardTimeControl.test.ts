/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useDashboardTimeControl } from '@/dashboard/composables/useDashboardTimeControl'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'

const HOUR = 3600

function globalTimePicker(startsLive: boolean): GlobalTimePickerProps {
  return {
    custom_time_ranges: [],
    default_time_range: 4 * HOUR,
    server_time_zone: 'Europe/Berlin',
    first_day_of_week: null,
    refresh: { interval_seconds: null, starts_live: startsLive, reloads_page_content: false }
  }
}

describe('useDashboardTimeControl', () => {
  // Module-level singleton: reset it so each test starts from a known state.
  beforeEach(() => {
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
  })

  it.each([
    { startsLive: true, paused: false },
    { startsLive: false, paused: true }
  ])('starts_live=$startsLive starts the refresh with paused=$paused', ({ startsLive, paused }) => {
    useDashboardTimeControl(globalTimePicker(startsLive))

    expect(useGlobalRefresh().refreshPaused.value).toBe(paused)
  })

  it("a widget's time range becomes the shared range and pauses the refresh", () => {
    const { updateTimeRange } = useDashboardTimeControl(globalTimePicker(true))
    // Ends now: a window in the past would pause the refresh on its own.
    const picked = rollingRange(HOUR)

    updateTimeRange(picked)

    expect(useGlobalTimeRange().activeTimeRange.value).toEqual(picked)
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })
})
