/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import DashboardRefreshControl from '@/dashboard/components/DashboardRefreshControl.vue'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import {
  durationSeconds,
  endsNow,
  rollingRange
} from '@/graphing/GlobalTimePicker/private/timeRange'

const HOUR = 3600

describe('DashboardRefreshControl', () => {
  // Module-level singleton: reset it so each test starts from a known state.
  beforeEach(() => {
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
  })

  it('resuming after a zoom goes back to the rolling default window', async () => {
    const lastFourHours = rollingRange(4 * HOUR)
    // A widget zoomed into one past hour, which paused the refresh.
    useGlobalTimeRange().setActiveTimeRange(
      { from: lastFourHours.from.add({ hours: 1 }), to: lastFourHours.from.add({ hours: 2 }) },
      'external'
    )
    render(DashboardRefreshControl, {
      props: { defaultTimeRange: 4 * HOUR, intervalChoicesSeconds: [30, 60, 90] }
    })

    await userEvent.click(screen.getByRole('button', { name: /Resume/ }))

    const active = useGlobalTimeRange().activeTimeRange.value!
    expect(durationSeconds(active)).toBe(4 * HOUR)
    expect(endsNow(active)).toBe(true)
    expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  })
})
