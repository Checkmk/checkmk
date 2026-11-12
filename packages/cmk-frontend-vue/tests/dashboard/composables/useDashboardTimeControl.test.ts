/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

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
    refresh: {
      interval_seconds: null,
      interval_choices_seconds: [30, 60, 90],
      starts_live: startsLive,
      reloads_page_content: false
    }
  }
}

describe('useDashboardTimeControl', () => {
  const pageUrl = window.location.href

  // Module-level singleton: reset it so each test starts from a known state.
  beforeEach(() => {
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
    vi.restoreAllMocks()
    window.history.replaceState({}, '', pageUrl)
  })

  function addressBarVariables(): Record<string, string> {
    return Object.fromEntries(new URL(window.location.href).searchParams)
  }

  it.each([
    { startsLive: true, paused: false },
    { startsLive: false, paused: true }
  ])('starts_live=$startsLive starts the refresh with paused=$paused', ({ startsLive, paused }) => {
    useDashboardTimeControl(globalTimePicker(startsLive))

    expect(useGlobalRefresh().refreshPaused.value).toBe(paused)
  })

  it('starts paused on the fixed window a link carried', () => {
    const [start, end] = [Date.parse('2026-01-01T00:00:00Z'), Date.parse('2026-01-01T04:00:00Z')]
    window.history.replaceState({}, '', `?name=main&from=${start}&to=${end}`)

    useDashboardTimeControl(globalTimePicker(true))

    const active = useGlobalTimeRange().activeTimeRange.value!
    expect([active.from.toDate().getTime(), active.to.toDate().getTime()]).toEqual([start, end])
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })

  it("a widget's time range becomes the shared range and pauses the refresh", () => {
    const { updateTimeRange } = useDashboardTimeControl(globalTimePicker(true))
    // Ends now: a window in the past would pause the refresh on its own.
    const picked = rollingRange(HOUR)

    updateTimeRange(picked)

    expect(useGlobalTimeRange().activeTimeRange.value).toEqual(picked)
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })

  it('writes a picked live range into the address bar as its duration', async () => {
    window.history.replaceState({}, '', '?name=main')
    useDashboardTimeControl(globalTimePicker(true))

    useGlobalTimeRange().setActiveTimeRange(rollingRange(HOUR), 'time_picker')
    await nextTick()

    expect(addressBarVariables()).toEqual({ name: 'main', from: 'now-3600s', to: 'now' })
  })

  it("writes a widget's range into the address bar as its two instants", async () => {
    window.history.replaceState({}, '', '?name=main')
    const { updateTimeRange } = useDashboardTimeControl(globalTimePicker(true))
    const picked = rollingRange(HOUR)

    updateTimeRange(picked)
    await nextTick()

    expect(addressBarVariables()).toEqual({
      name: 'main',
      from: String(picked.from.toDate().getTime()),
      to: String(picked.to.toDate().getTime())
    })
  })

  it('leaves the address bar alone while a live range rolls on', async () => {
    useDashboardTimeControl(globalTimePicker(true))
    useGlobalTimeRange().setActiveTimeRange(rollingRange(HOUR), 'time_picker')
    await nextTick()
    const replaceState = vi.spyOn(window.history, 'replaceState')

    useGlobalRefresh().refreshOnce()
    await nextTick()

    expect(replaceState).not.toHaveBeenCalled()
  })
})
