/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import type { UrlSync } from '@/monitoring/shared/browserUrlSync'
import {
  readFilterUrlState,
  useUrlFilterState
} from '@/monitoring/shared/filterState/useUrlFilterState'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

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
      replaceUrl
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

describe('useUrlFilterState', () => {
  it('never seeds the service - reading the URL is the app job, done before this runs', () => {
    const service = new TestService()
    const { urlSync } = makeUrlSync('?q=preexisting')

    useUrlFilterState(service, { urlSync })

    expect(service.searchQuery.value).toBe('')

    service.stopPolling()
  })

  it('canonicalises once on setup, then once per applied mutation', async () => {
    const service = new TestService()
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlFilterState(service, { urlSync })
    expect(replaceUrl).toHaveBeenCalledTimes(1)

    service.updateSearch('web01')
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(2)

    service.updateFilters({ type: 'condition', field: 'name', op: 'contains', value: 'web' })
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(3)

    service.stopPolling()
  })

  it('keeps legacy-looking filter vars across several writes', async () => {
    const service = new TestService()
    const { urlSync, replaceUrl } = makeUrlSync('?host=v300&neg_host=&foo=bar')

    useUrlFilterState(service, { urlSync })
    service.updateSearch('web01')
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(2)
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

    useUrlFilterState(service, { urlSync })
    service.updateSearch('web01')
    await nextTick()

    expect(replaceState).not.toHaveBeenCalled()

    replaceState.mockRestore()
    service.stopPolling()
  })
})
