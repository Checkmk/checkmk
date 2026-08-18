/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, within } from '@testing-library/vue'
import { timeZoneRegionLabel } from 'cmk-ui-library/components/date-time/dateTimeUtils'
import TimeZoneInfo from 'cmk-ui-library/components/date-time/private/display/TimeZoneInfo.vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import { TZ_BERLIN, TZ_TOKYO, TZ_UTC, YMD, makeSettings } from '../../dateTimeTestFixtures'

const SETTINGS = makeSettings({ timeZone: TZ_BERLIN, dateFormat: YMD, hourCycle: 24 })

const renderInfo = (serverTimeZone?: string) =>
  render(TimeZoneInfo, {
    props: { settings: SETTINGS, ...(serverTimeZone ? { serverTimeZone } : {}) }
  })

const entryOf = (view: ReturnType<typeof renderInfo>, label: string) =>
  view.getByText(label).closest<HTMLElement>('.cmk-time-zone-info__entry')!

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-06-10T10:00:00Z'))
})

afterEach(() => {
  vi.useRealTimers()
})

describe('TimeZoneInfo', () => {
  test('the displayed zone is named by its region, spoken only through the badge', () => {
    const view = renderInfo()
    const entry = entryOf(view, 'Timezone:')

    expect(entry.querySelector('.cmk-tag')).toHaveAttribute('aria-hidden', 'true')
    expect(within(entry).getByText(timeZoneRegionLabel(TZ_BERLIN))).toHaveAttribute(
      'aria-hidden',
      'true'
    )
  })

  test('the server readout is the current instant in the server zone', () => {
    // 2026-06-10T10:00:00Z is 2026-06-10 19:00 in Tokyo (UTC+9). ISO date + 24h time.
    const view = renderInfo(TZ_TOKYO)
    expect(entryOf(view, 'Current server time:').textContent).toContain('2026-06-10, 19:00')
  })

  test('the server readout is an em dash without a server zone', () => {
    const view = renderInfo()
    expect(entryOf(view, 'Current server time:').textContent).toContain('—')
  })

  test('the server readout follows the clock while it is shown', async () => {
    const view = renderInfo(TZ_UTC)
    expect(entryOf(view, 'Current server time:').textContent).toContain('2026-06-10, 10:00')

    await vi.advanceTimersByTimeAsync(60_100)
    await nextTick()

    expect(entryOf(view, 'Current server time:').textContent).toContain('2026-06-10, 10:01')
  })
})
