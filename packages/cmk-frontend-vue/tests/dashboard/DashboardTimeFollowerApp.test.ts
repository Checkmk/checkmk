/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { parseAbsoluteToLocal } from '@internationalized/date'
import { fireEvent, render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardTimeFollowerApp from '@/dashboard/DashboardTimeFollowerApp.vue'
import type { DashboardTimeRangeMessage } from '@/dashboard/lib/dashboardTimeRangeMessage'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'

const reloadContentNow = vi.fn()

function message(
  tick: number,
  start = '2026-01-01T00:00:00.000Z',
  live = false
): DashboardTimeRangeMessage {
  return {
    type: 'cmk:dashboard:time-range',
    range: { start, end: '2026-01-01T01:00:00.000Z' },
    tick,
    live
  }
}

function liveMessage(tick: number): DashboardTimeRangeMessage {
  return message(tick, '2026-01-01T00:00:00.000Z', true)
}

function columnLink({ includesTimeRange }: { includesTimeRange: boolean }): HTMLAnchorElement {
  const link = document.createElement('a')
  link.href = 'view.py?view_name=host&host=heute'
  if (includesTimeRange) {
    link.setAttribute('data-cmk_includes_time_range', '')
  }
  link.append(document.createElement('span'))
  document.body.append(link)
  return link
}

function linkVariables(link: HTMLAnchorElement): Record<string, string> {
  return Object.fromEntries(new URL(link.href).searchParams)
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
  vi.useRealTimers()
  document.querySelectorAll('a').forEach((link) => link.remove())
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

  it('ignores a message without the live state of the dashboard', () => {
    post({ type: 'cmk:dashboard:time-range', range: message(0).range, tick: 0 })

    expect(publishedStart()).toBeUndefined()
  })

  it('starts no reload of its own while the dashboard is live', () => {
    vi.useFakeTimers()
    post(liveMessage(4))

    vi.advanceTimersByTime(60 * 60 * 1000)
    document.dispatchEvent(new Event('visibilitychange'))

    expect(reloadContentNow).not.toHaveBeenCalled()
    expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  })
})

describe('DashboardTimeFollowerApp on the way back to the dashboard', () => {
  const pageUrl = window.location.href
  const dashboardUrl = 'https://example.com/check_mk/dashboard.py?name=main'

  afterEach(() => {
    window.history.replaceState({}, '', pageUrl)
  })

  function wayBack(): Record<string, string> {
    const iframeUrl = new URL(window.location.href)
    return Object.fromEntries(
      new URL(iframeUrl.searchParams.get('drill_down_source_url')!).searchParams
    )
  }

  it('carries the duration while the dashboard is live', () => {
    window.history.replaceState(
      {},
      '',
      `?drill_down_source_url=${encodeURIComponent(dashboardUrl)}`
    )

    post(liveMessage(0))

    expect(wayBack()).toEqual({ name: 'main', from: 'now-3600s', to: 'now' })
  })

  it('carries the two instants while the dashboard is paused', () => {
    window.history.replaceState(
      {},
      '',
      `?drill_down_source_url=${encodeURIComponent(dashboardUrl)}`
    )
    post(liveMessage(0))

    post(message(0))

    expect(wayBack()).toEqual({ name: 'main', from: '1767225600000', to: '1767229200000' })
  })

  it('leaves its address alone without a way back', () => {
    window.history.replaceState({}, '', '?view_name=host')
    const replaceState = vi.spyOn(window.history, 'replaceState')

    post(liveMessage(0))

    expect(replaceState).not.toHaveBeenCalled()
    replaceState.mockRestore()
  })
})

describe('DashboardTimeFollowerApp on a column link that includes the time range', () => {
  it('carries the duration while the dashboard is live', async () => {
    post(liveMessage(0))
    const link = columnLink({ includesTimeRange: true })

    await fireEvent.pointerOver(link)

    expect(linkVariables(link)).toEqual({
      view_name: 'host',
      host: 'heute',
      from: 'now-3600s',
      to: 'now'
    })
  })

  it('carries the two instants while the dashboard is paused', async () => {
    post(message(0))
    const link = columnLink({ includesTimeRange: true })

    await fireEvent.pointerOver(link)

    expect(linkVariables(link)).toMatchObject({ from: '1767225600000', to: '1767229200000' })
  })

  it('carries the range the dashboard told last', async () => {
    post(liveMessage(0))
    const link = columnLink({ includesTimeRange: true })
    await fireEvent.pointerOver(link)

    post(message(0))
    await fireEvent.pointerOver(link)

    expect(linkVariables(link)).toMatchObject({ from: '1767225600000', to: '1767229200000' })
  })

  it("carries the dashboard's range over a range a graph in the view picked", async () => {
    post(liveMessage(0))
    useGlobalTimeRange().setActiveTimeRange(
      {
        from: parseAbsoluteToLocal('2026-01-01T00:10:00.000Z'),
        to: parseAbsoluteToLocal('2026-01-01T00:20:00.000Z')
      },
      'external'
    )
    const link = columnLink({ includesTimeRange: true })

    await fireEvent.pointerOver(link)

    expect(linkVariables(link)).toMatchObject({ from: 'now-3600s', to: 'now' })
  })

  it('carries the range when a press reaches a part of the link', async () => {
    post(liveMessage(0))
    const link = columnLink({ includesTimeRange: true })

    await fireEvent.pointerDown(link.firstElementChild!)

    expect(linkVariables(link)).toMatchObject({ from: 'now-3600s', to: 'now' })
  })

  it('carries the range when the link gets the focus', async () => {
    post(liveMessage(0))
    const link = columnLink({ includesTimeRange: true })

    await fireEvent.focusIn(link)

    expect(linkVariables(link)).toMatchObject({ from: 'now-3600s', to: 'now' })
  })

  it('leaves a link alone that does not include the time range', async () => {
    post(liveMessage(0))
    const link = columnLink({ includesTimeRange: false })

    await fireEvent.pointerOver(link)

    expect(linkVariables(link)).toEqual({ view_name: 'host', host: 'heute' })
  })

  it('leaves the link as the server built it until the dashboard tells a range', async () => {
    const link = columnLink({ includesTimeRange: true })

    await fireEvent.pointerOver(link)

    expect(linkVariables(link)).toEqual({ view_name: 'host', host: 'heute' })
  })
})
