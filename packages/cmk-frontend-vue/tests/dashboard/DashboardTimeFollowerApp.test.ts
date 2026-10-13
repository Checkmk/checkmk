/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardTimeFollowerApp from '@/dashboard/DashboardTimeFollowerApp.vue'
import type { DashboardTimeRangeMessage } from '@/dashboard/lib/dashboardTimeRangeMessage'
import {
  resetGlobalTimeState,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'

const reloadContentNow = vi.fn()

function message(tick: number, start = '2026-01-01T00:00:00.000Z'): DashboardTimeRangeMessage {
  return {
    type: 'cmk:dashboard:time-range',
    range: { start, end: '2026-01-01T01:00:00.000Z' },
    tick
  }
}

function post(
  data: unknown,
  { origin = window.location.origin, source = window.parent as MessageEventSource } = {}
): void {
  window.dispatchEvent(new MessageEvent('message', { data, origin, source }))
}

function publishedStart(): string | undefined {
  return useGlobalTimeRange().activeTimeRange.value?.from.toAbsoluteString()
}

beforeEach(() => {
  vi.stubGlobal('cmk', { utils: { reload_content_now: reloadContentNow } })
  render(DashboardTimeFollowerApp)
})

afterEach(() => {
  resetGlobalTimeState()
  reloadContentNow.mockReset()
  vi.unstubAllGlobals()
})

describe('DashboardTimeFollowerApp', () => {
  it('shows the time range of the dashboard', () => {
    post(message(0))

    expect(publishedStart()).toBe('2026-01-01T00:00:00.000Z')
  })

  it('does not reload the content it just loaded', () => {
    post(message(4))

    expect(reloadContentNow).not.toHaveBeenCalled()
  })

  it('reloads the content on each tick of the dashboard', () => {
    post(message(4))

    post(message(5))

    expect(reloadContentNow).toHaveBeenCalledOnce()
  })

  it('does not reload when only the time range changes', () => {
    post(message(4))

    post(message(4, '2026-01-01T00:30:00.000Z'))

    expect(reloadContentNow).not.toHaveBeenCalled()
    expect(publishedStart()).toBe('2026-01-01T00:30:00.000Z')
  })

  it('ignores a message from another origin', () => {
    post(message(0), { origin: 'https://example.com' })

    expect(publishedStart()).toBeUndefined()
  })

  it('ignores a message that does not come from the dashboard', () => {
    post(message(0), { source: new MessageChannel().port1 })

    expect(publishedStart()).toBeUndefined()
  })

  it('ignores other messages', () => {
    post({ type: 'cmk:view:save-completed', range: message(0).range, tick: 0 })

    expect(publishedStart()).toBeUndefined()
  })
})
