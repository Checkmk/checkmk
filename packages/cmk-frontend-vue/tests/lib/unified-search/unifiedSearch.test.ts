/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { Api } from '@/lib/api-client'
import { CustomizeSearchProvider } from '@/lib/unified-search/providers/customize'
import { MonitoringSearchProvider } from '@/lib/unified-search/providers/monitoring'
import { SetupSearchProvider } from '@/lib/unified-search/providers/setup'
import { UnifiedSearch } from '@/lib/unified-search/unified-search'

const api = new Api()
const mockLegacyGetResponse = vitest.fn()

beforeAll(() => {
  api.get = mockLegacyGetResponse
})

beforeEach(() => {
  mockLegacyGetResponse.mockReturnValue(
    new Promise((resolve) => {
      resolve(null)
    })
  )
})

test('Unified search instance with setup & monitoring search provider, returns proper unified search result', async () => {
  const monSP = new MonitoringSearchProvider()
  const setupSP = new SetupSearchProvider()
  const custSP = new CustomizeSearchProvider()
  const search = new UnifiedSearch('test-search', api, [monSP, setupSP])

  const result = search.search('test')

  expect(result).toBeDefined()
  expect(result?.get(monSP.id)).toBeDefined()
  expect(result?.get(setupSP.id)).toBeDefined()
  expect(result?.get(custSP.id)).toBeNull()
})

test('Unified search instance with setup & monitoring search provider, returns proper unified search result', async () => {
  mockLegacyGetResponse.mockReturnValue(
    new Promise((resolve) => {
      setTimeout(() => {
        resolve('any type of response string')
      }, 100)
    })
  )

  const monSP = new MonitoringSearchProvider()
  const setupSP = new SetupSearchProvider()
  const search = new UnifiedSearch('test-search', api, [monSP, setupSP])

  const result = search.search('test')

  expect(result).toBeDefined()

  const monRes = (await result?.get(monSP.id)?.result) as string
  const setupRes = (await result?.get(setupSP.id)?.result) as string

  expect(monRes).toBe('any type of response string')
  expect(monRes).not.toBe('any other type of response string')
  expect(setupRes).toBe('any type of response string')
})
