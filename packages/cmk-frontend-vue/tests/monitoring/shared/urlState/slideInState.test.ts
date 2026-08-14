/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import {
  type SlideInUrlDescriptor,
  exactPattern,
  readSlideInFromHash,
  slideInWriter
} from '@/monitoring/shared/urlState/slideInState'

import { makeKeyShortcutService, makeResponse } from '../services/testHelpers'

interface TestRow {
  site: string
  name: string
}

class TestService extends MonitoringService<TestRow> {
  constructor(
    private readonly rows: TestRow[],
    options: MonitoringServiceOptions<TestRow> = {}
  ) {
    super('slide-in-url-state-test-service', makeKeyShortcutService(), options)
  }

  protected fetchBatch(): Promise<PagedResponse<TestRow>> {
    return Promise.resolve(makeResponse(this.rows, this.rows.length, this.rows.length))
  }
}

const WEB01: TestRow = { site: 'heute', name: 'web01' }

function makeDescriptor(
  load: (identity: TestRow) => Promise<TestRow | null> = () => Promise.resolve(null)
): SlideInUrlDescriptor<TestRow, TestRow> {
  return {
    keys: ['host', 'site'],
    defaultTabId: 'overview',
    encode: (row) => ({ host: row.name, site: row.site }),
    decode: (params) => {
      const name = params['host']
      const site = params['site']
      return name === undefined || site === undefined ? null : { name, site }
    },
    matches: (row, identity) => row.name === identity.name && row.site === identity.site,
    load
  }
}

const descriptor = makeDescriptor()

function makeHarness(
  rows: TestRow[],
  hash: string,
  load?: (identity: TestRow) => Promise<TestRow | null>
) {
  const current: Ref<TestRow | null> = ref(null)
  const tabId = ref<string | undefined>(undefined)
  const service = new TestService(rows)
  const writer = slideInWriter({
    descriptor: load === undefined ? descriptor : makeDescriptor(load),
    service,
    current,
    tabId,
    initial: readSlideInFromHash(load === undefined ? descriptor : makeDescriptor(load), hash),
    open: (row) => {
      current.value = row
    },
    close: () => {
      current.value = null
    }
  })
  return { current, tabId, service, writer }
}

describe('readSlideInFromHash', () => {
  it('reads the panel and tab a fragment names', () => {
    expect(readSlideInFromHash(descriptor, '#host=web01&site=heute&tab=metrics')).toEqual({
      identity: WEB01,
      tabId: 'metrics',
      params: { host: 'web01', site: 'heute', tab: 'metrics' }
    })
  })

  it('is null for a fragment naming no panel', () => {
    expect(readSlideInFromHash(descriptor, '#tab=metrics')).toBeNull()
    expect(readSlideInFromHash(descriptor, '')).toBeNull()
  })
})

describe('slideInWriter', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    return () => vi.useRealTimers()
  })

  it('opens the panel on the row the fragment names, once the listing has it', async () => {
    const { current, tabId, service, writer } = makeHarness(
      [WEB01],
      '#host=web01&site=heute&tab=metrics'
    )

    expect(current.value).toBeNull()
    // Until the row is there, the fragment is echoed back rather than cleared.
    expect(writer.params.value).toEqual({ host: 'web01', site: 'heute', tab: 'metrics' })

    await vi.advanceTimersByTimeAsync(0)

    expect(current.value).toEqual(WEB01)
    expect(tabId.value).toBe('metrics')

    service.stopPolling()
  })

  it('scrolls the listing to the row it opened from it', async () => {
    const { service, current } = makeHarness([WEB01], '#host=web01&site=heute')

    await vi.advanceTimersByTimeAsync(0)

    expect(current.value).toEqual(WEB01)
    expect(service.rowToReveal.value).toEqual(WEB01)

    service.stopPolling()
  })

  it('opens a row the listing does not show, by fetching it', async () => {
    const load = vi.fn().mockResolvedValue(WEB01)
    const { current, tabId, service } = makeHarness([], '#host=web01&site=heute&tab=metrics', load)

    await vi.advanceTimersByTimeAsync(0)

    expect(load).toHaveBeenCalledWith(WEB01)
    expect(current.value).toEqual(WEB01)
    expect(tabId.value).toBe('metrics')
    // Nothing to scroll to: the row is not in the listing.
    expect(service.rowToReveal.value).toBeNull()

    service.stopPolling()
  })

  it('does not fetch when the listing already carries the row', async () => {
    const load = vi.fn().mockResolvedValue(WEB01)
    const { current, service } = makeHarness([WEB01], '#host=web01&site=heute', load)

    await vi.advanceTimersByTimeAsync(0)

    expect(load).not.toHaveBeenCalled()
    expect(current.value).toEqual(WEB01)

    service.stopPolling()
  })

  it('leaves the panel closed and the link intact for a row that is gone', async () => {
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const { current, writer, service } = makeHarness([], '#host=web01&site=heute', () =>
      Promise.resolve(null)
    )

    await vi.advanceTimersByTimeAsync(0)

    expect(current.value).toBeNull()
    expect(consoleWarn).toHaveBeenCalledWith(expect.stringContaining('slide-in:'))
    // The link stays intact: the user may still navigate back out of it.
    expect(writer.params.value).toEqual({ host: 'web01', site: 'heute' })

    consoleWarn.mockRestore()
    service.stopPolling()
  })

  it('honours a fragment once, so a row matching again later does not pop open', async () => {
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const rows: TestRow[] = []
    const { current, service } = makeHarness(rows, '#host=web01&site=heute', () =>
      Promise.resolve(null)
    )

    await vi.advanceTimersByTimeAsync(0)
    expect(current.value).toBeNull()

    // The row starts matching the filter again a poll later.
    rows.push(WEB01)
    service.refresh(0)
    await vi.advanceTimersByTimeAsync(50)

    expect(service.items.value).toEqual([WEB01])
    expect(current.value).toBeNull()

    consoleWarn.mockRestore()
    service.stopPolling()
  })

  it('names the open panel in the fragment, omitting a tab that says nothing', async () => {
    const { current, tabId, service, writer } = makeHarness([WEB01], '')

    current.value = WEB01
    await nextTick()
    expect(writer.params.value).toEqual({ host: 'web01', site: 'heute', tab: null })

    tabId.value = 'overview'
    await nextTick()
    expect(writer.params.value['tab']).toBeNull()

    tabId.value = 'metrics'
    await nextTick()
    expect(writer.params.value['tab']).toBe('metrics')

    service.stopPolling()
  })

  it('clears its params when the panel closes, so the fragment goes away', async () => {
    const { current, service, writer } = makeHarness([WEB01], '')

    current.value = WEB01
    await nextTick()
    current.value = null
    await nextTick()

    expect(writer.params.value).toEqual({ host: null, site: null, tab: null })

    service.stopPolling()
  })

  it('closes the panel when a navigation lands on a fragment naming none', async () => {
    const { current, service, writer } = makeHarness([WEB01], '#host=web01&site=heute')

    await vi.advanceTimersByTimeAsync(0)
    expect(current.value).toEqual(WEB01)

    writer.apply?.({})

    expect(current.value).toBeNull()

    service.stopPolling()
  })

  it('reopens the panel when a navigation lands back on its fragment', async () => {
    const { current, tabId, service, writer } = makeHarness([WEB01], '')

    await vi.advanceTimersByTimeAsync(0)

    writer.apply?.({ host: 'web01', site: 'heute', tab: 'metrics' })

    expect(current.value).toEqual(WEB01)
    expect(tabId.value).toBe('metrics')

    service.stopPolling()
  })
})

describe('exactPattern', () => {
  it('anchors the value so a longer name cannot match', () => {
    expect(exactPattern('web01')).toBe('^web01$')
  })

  it('escapes metacharacters, so a name out of a URL carries no pattern of its own', () => {
    expect(exactPattern('web.01')).toBe('^web\\.01$')
    expect(exactPattern('CPU load (avg)')).toBe('^CPU load \\(avg\\)$')
    expect(exactPattern('.*')).toBe('^\\.\\*$')
  })
})
