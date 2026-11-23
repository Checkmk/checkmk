/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import TimeZoneInfo from 'cmk-ui-library/components/date-time/private/display/TimeZoneInfo.vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import { TZ_BERLIN, TZ_TOKYO, TZ_UTC, YMD, makeSettings } from '../../dateTimeTestFixtures'

const SETTINGS = makeSettings({ timeZone: TZ_BERLIN, dateFormat: YMD, hourCycle: 24 })

const renderInfo = (serverTimeZone?: string) =>
  render(TimeZoneInfo, {
    props: { settings: SETTINGS, ...(serverTimeZone ? { serverTimeZone } : {}) }
  })

const serverLine = (view: ReturnType<typeof renderInfo>) => view.getByText(/^Server time: /)

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-06-10T10:00:00Z'))
})

afterEach(() => {
  vi.useRealTimers()
})

describe('TimeZoneInfo', () => {
  test('the displayed zone reads as region plus abbreviation and offset', () => {
    // 2026-06-10 is summer time in Berlin.
    const view = renderInfo()
    expect(view.getByText('Timezone: Europe, Berlin (CEST, UTC+2)')).toBeInTheDocument()
  })

  test('the server readout is the current instant in the server zone', () => {
    // 2026-06-10T10:00:00Z is 2026-06-10 19:00 in Tokyo (UTC+9). ISO date + 24h time.
    const view = renderInfo(TZ_TOKYO)
    expect(serverLine(view)).toHaveTextContent('Server time: 2026-06-10, 19:00 (UTC+9)')
  })

  test('the server readout is an em dash without a server zone', () => {
    const view = renderInfo()
    expect(serverLine(view)).toHaveTextContent('Server time: —')
  })

  test('the server readout follows the clock while it is shown', async () => {
    const view = renderInfo(TZ_UTC)
    expect(serverLine(view)).toHaveTextContent('2026-06-10, 10:00')

    await vi.advanceTimersByTimeAsync(60_100)
    await nextTick()

    expect(serverLine(view)).toHaveTextContent('2026-06-10, 10:01')
  })
})
