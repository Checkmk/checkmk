/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import GlobalTimePickerApp from '@/graphing/GlobalTimePicker/GlobalTimePickerApp.vue'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { durationSeconds, rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'

const HOUR = 3600

const PROPS: GlobalTimePickerProps = {
  custom_time_ranges: [
    { title: 'Last 4 hours', total_seconds: 4 * HOUR },
    { title: 'Last 25 hours', total_seconds: 25 * HOUR }
  ],
  default_time_range: 4 * HOUR,
  server_time_zone: 'Europe/Berlin',
  first_day_of_week: null,
  refresh: { interval_seconds: null, starts_live: false, reloads_page_content: false }
}

const activeDurationSeconds = (): number => {
  const active = useGlobalTimeRange().activeTimeRange.value
  expect(active).not.toBeNull()
  return durationSeconds(active!)
}

describe('GlobalTimePickerApp', () => {
  // Module-level singleton: reset it so each test starts from a known state.
  beforeEach(() => {
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
    vi.unstubAllGlobals()
  })

  test('seeds the shared store with the default duration when empty', () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    expect(activeDurationSeconds()).toBe(4 * HOUR)
  })

  test('does not overwrite an already-seeded store', () => {
    useGlobalTimeRange().setActiveTimeRange(rollingRange(99), 'time_picker')
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    expect(activeDurationSeconds()).toBe(99)
  })

  test('a chip click propagates the new range to the shared store', async () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    await fireEvent.click(screen.getByRole('button', { name: 'Last 25 hours' }))
    expect(activeDurationSeconds()).toBe(25 * HOUR)
  })

  test('renders the refresh control', () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    expect(screen.getByText('Refresh off')).toBeInTheDocument()
  })

  test('the refresh the server described is the one the page runs', () => {
    const fromTheServer = { interval_seconds: 60, starts_live: true, reloads_page_content: false }

    render(GlobalTimePickerApp, { props: { ...PROPS, refresh: fromTheServer } })

    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(fromTheServer.interval_seconds)
    expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  })

  test('a page whose rows the server rendered has its content re-fetched on a refresh', () => {
    const reloadContent = vi.fn()
    vi.stubGlobal('cmk', { utils: { reload_content_now: reloadContent } })
    render(GlobalTimePickerApp, {
      props: { ...PROPS, refresh: { ...PROPS.refresh, reloads_page_content: true } }
    })

    useGlobalRefresh().resumeRefresh()

    expect(reloadContent).toHaveBeenCalledOnce()
  })

  test('a page of graphs alone leaves the surrounding page alone', () => {
    const reloadContent = vi.fn()
    vi.stubGlobal('cmk', { utils: { reload_content_now: reloadContent } })
    render(GlobalTimePickerApp, { props: { ...PROPS } })

    useGlobalRefresh().resumeRefresh()

    expect(reloadContent).not.toHaveBeenCalled()
  })

  test('a fresh page shows the configured default active, with no interaction', () => {
    render(GlobalTimePickerApp, {
      props: {
        ...PROPS,
        custom_time_ranges: [
          { title: 'Last 1 hour', total_seconds: HOUR },
          ...PROPS.custom_time_ranges
        ],
        default_time_range: HOUR
      }
    })
    expect(screen.getByRole('button', { name: 'Last 1 hour' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  })

  test('resuming the refresh reverts a zoomed range to the configured default', async () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    const seeded = rollingRange(4 * HOUR)
    useGlobalTimeRange().setActiveTimeRange(
      {
        from: seeded.from.add({ hours: 1 }),
        to: seeded.to.subtract({ hours: 2 })
      },
      'external'
    )

    await fireEvent.click(screen.getByRole('button', { name: /Resume/ }))

    expect(activeDurationSeconds()).toBe(4 * HOUR)
    expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  })

  test('the preference decides the initial selection, not the configured order', () => {
    // The preference names the *second* range, so a picker that simply took the first would fail.
    render(GlobalTimePickerApp, { props: { ...PROPS, default_time_range: 25 * HOUR } })
    expect(screen.getByRole('button', { name: 'Last 25 hours' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    expect(screen.getByRole('button', { name: 'Last 4 hours' })).toHaveAttribute(
      'aria-pressed',
      'false'
    )
  })
})
