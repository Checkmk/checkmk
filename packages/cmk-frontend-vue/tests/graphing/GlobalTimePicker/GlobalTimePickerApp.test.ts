/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { beforeEach, describe, expect, test } from 'vitest'

import GlobalTimePickerApp from '@/graphing/GlobalTimePicker/GlobalTimePickerApp.vue'
import { durationSeconds, rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'
import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/useGlobalTimeRange'

const HOUR = 3600

const PROPS: GlobalTimePickerProps = {
  custom_time_ranges: [
    { title: 'Last 4 hours', total_seconds: 4 * HOUR },
    { title: 'Last 25 hours', total_seconds: 25 * HOUR }
  ],
  default_time_range: 4 * HOUR,
  server_time_zone: 'America/Los_Angeles'
}

const activeDurationSeconds = (): number => {
  const active = useGlobalTimeRange().activeTimeRange.value
  expect(active).not.toBeNull()
  return durationSeconds(active!)
}

describe('GlobalTimePickerApp', () => {
  // The store is a module-level singleton; reset it so each test starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null)
  })

  test('seeds the shared store with the default duration when empty', () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    expect(activeDurationSeconds()).toBe(4 * HOUR)
  })

  test('does not overwrite an already-seeded store', () => {
    useGlobalTimeRange().setActiveTimeRange(rollingRange(99))
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    expect(activeDurationSeconds()).toBe(99)
  })

  test('a chip click propagates the new range to the shared store', async () => {
    render(GlobalTimePickerApp, { props: { ...PROPS } })
    await fireEvent.click(screen.getByRole('button', { name: 'Last 25 hours' }))
    expect(activeDurationSeconds()).toBe(25 * HOUR)
  })
})
