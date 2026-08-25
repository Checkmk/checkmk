/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { afterEach, beforeEach, describe, expect, test } from 'vitest'

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
  default_refresh_time: null
}

const activeDurationSeconds = (): number => {
  const active = useGlobalTimeRange().activeTimeRange.value
  expect(active).not.toBeNull()
  return durationSeconds(active!)
}

describe('GlobalTimePickerApp', () => {
  // The stores are module-level singletons; reset them so each test starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
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

  test('a preferred refresh time preselects the interval but stays paused', () => {
    render(GlobalTimePickerApp, { props: { ...PROPS, default_refresh_time: 60 } })
    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })

  test('no refresh preference keeps the default interval', () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
  })

  test('a second app does not clobber an interval the user chose in the meantime', () => {
    render(GlobalTimePickerApp, { props: { ...PROPS, default_refresh_time: 60 } })
    useGlobalRefresh().setRefreshIntervalSeconds(90)
    render(GlobalTimePickerApp, { props: { ...PROPS, default_refresh_time: 60 } })
    expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(90)
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
