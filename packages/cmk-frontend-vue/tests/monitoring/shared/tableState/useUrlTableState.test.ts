/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import type { UrlSync } from '@/monitoring/shared/browserUrlSync'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import type { TableStateSchema } from '@/monitoring/shared/tableState/types'
import {
  readTableStateFromUrl,
  useUrlTableState
} from '@/monitoring/shared/tableState/useUrlTableState'

import { makeKeyShortcutService, makeResponse } from '../services/testHelpers'

interface TestItem {
  id: string
}

class TestService extends MonitoringService<TestItem> {
  constructor(options: MonitoringServiceOptions<TestItem> = {}) {
    super('url-table-state-test-service', makeKeyShortcutService(), options)
  }

  protected fetchBatch(): Promise<PagedResponse<TestItem>> {
    return Promise.resolve(makeResponse([], 0, 0))
  }
}

// No hideable columns: keeps `cols` at its default on every write, so these
// tests can focus on sort/limit without unrelated noise in the URL.
const schema: TableStateSchema = {
  hideable: [],
  sortable: new Set(['name']),
  defaultVisibility: {},
  offeredLimits: [1000, 5000]
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

describe('readTableStateFromUrl', () => {
  it('decodes and reconciles the given query string', () => {
    expect(readTableStateFromUrl('?limit=5000', schema).limit).toBe(5000)
  })
})

describe('useUrlTableState', () => {
  it('never seeds the service - reading the URL is the app job, done before this runs', () => {
    const service = new TestService({ limitTiers: [1000, 5000] })
    const { urlSync } = makeUrlSync('?limit=5000')

    useUrlTableState(service, schema, { urlSync })

    expect(service.requestedLimit.value).toBe(1000)

    service.stopPolling()
  })

  it('canonicalises once on setup, then once per applied mutation', async () => {
    const service = new TestService({ limitTiers: [1000, 5000] })
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlTableState(service, schema, { urlSync })
    expect(replaceUrl).toHaveBeenCalledTimes(1)

    service.setRequestedLimit(5000)
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(2)

    service.updateSort([{ id: 'name', desc: true }])
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(3)

    service.stopPolling()
  })

  it('keeps legacy-looking filter vars across several writes', async () => {
    const service = new TestService({ limitTiers: [1000, 5000] })
    const { urlSync, replaceUrl } = makeUrlSync('?host=v300&neg_host=&foo=bar')

    useUrlTableState(service, schema, { urlSync })
    service.setRequestedLimit(5000)
    await nextTick()
    service.updateSort([{ id: 'name', desc: true }])
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(3)
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
    const service = new TestService({ limitTiers: [1000, 5000] })
    const { urlSync } = makeUrlSync()

    useUrlTableState(service, schema, { urlSync })
    service.setRequestedLimit(5000)
    await nextTick()

    expect(replaceState).not.toHaveBeenCalled()

    replaceState.mockRestore()
    service.stopPolling()
  })
})
