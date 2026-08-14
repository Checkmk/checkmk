/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import type { UrlSync } from '@/monitoring/shared/browserUrlSync'
import { filterStateWriter, readFilterUrlState } from '@/monitoring/shared/filterState/urlState'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import { useUrlSync } from '@/monitoring/shared/urlState/useUrlSync'

import { makeKeyShortcutService, makeResponse } from '../services/testHelpers'

interface TestItem {
  id: string
}

class TestService extends MonitoringService<TestItem> {
  constructor(options: MonitoringServiceOptions<TestItem> = {}) {
    super('filter-url-state-test-service', makeKeyShortcutService(), options)
  }

  protected fetchBatch(): Promise<PagedResponse<TestItem>> {
    return Promise.resolve(makeResponse([], 0, 0))
  }
}

function makeUrlSync(search = ''): { urlSync: UrlSync; replaceUrl: ReturnType<typeof vi.fn> } {
  const replaceUrl = vi.fn()
  return {
    urlSync: {
      getCurrentUrl: () => ({ pathname: '/monitor_all_hosts.py', search, hash: '' }),
      replaceUrl,
      pushUrl: replaceUrl,
      onNavigate: () => () => {}
    },
    replaceUrl
  }
}

describe('readFilterUrlState', () => {
  it('decodes and reconciles the given query string', () => {
    expect(readFilterUrlState('?q=preexisting', { filterableFields: new Set() }).search).toBe(
      'preexisting'
    )
  })
})

describe('filterStateWriter', () => {
  it('never seeds the service - reading the URL is the app job, done before this runs', () => {
    const service = new TestService()
    const { urlSync } = makeUrlSync('?q=preexisting')

    useUrlSync([filterStateWriter(service)], { urlSync })

    expect(service.searchQuery.value).toBe('')

    service.stopPolling()
  })

  it('writes once per applied mutation, and not at all for a URL that already matches', async () => {
    const service = new TestService()
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([filterStateWriter(service)], { urlSync })
    expect(replaceUrl).not.toHaveBeenCalled()

    service.updateSearch('web01')
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(1)

    service.updateFilters({ type: 'condition', field: 'name', op: 'contains', value: 'web' })
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('drops a stale search the URL was seeded with but the state does not carry', () => {
    const service = new TestService()
    const { urlSync, replaceUrl } = makeUrlSync('?q=preexisting')

    useUrlSync([filterStateWriter(service)], { urlSync })

    expect(replaceUrl).toHaveBeenCalledTimes(1)
    expect(replaceUrl.mock.calls[0]![0]).not.toContain('q=')

    service.stopPolling()
  })

  it('keeps legacy-looking filter vars across several writes', async () => {
    const service = new TestService()
    const { urlSync, replaceUrl } = makeUrlSync('?host=v300&neg_host=&foo=bar')

    useUrlSync([filterStateWriter(service)], { urlSync })
    service.updateSearch('web01')
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(1)
    for (const call of replaceUrl.mock.calls) {
      const url = call[0] as string
      expect(url).toContain('host=v300')
      expect(url).toContain('neg_host=')
      expect(url).toContain('foo=bar')
    }

    service.stopPolling()
  })

  it('writes only through the injected sync, never touching the real browser', async () => {
    const replaceState = vi.spyOn(window.history, 'replaceState')
    const service = new TestService()
    const { urlSync } = makeUrlSync()

    useUrlSync([filterStateWriter(service)], { urlSync })
    service.updateSearch('web01')
    await nextTick()

    expect(replaceState).not.toHaveBeenCalled()

    replaceState.mockRestore()
    service.stopPolling()
  })
})
