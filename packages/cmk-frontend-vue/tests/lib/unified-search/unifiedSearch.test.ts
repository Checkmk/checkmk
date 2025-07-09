/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { Api } from '@/lib/api-client'
import { UnifiedSearchProvider } from '@/lib/unified-search/providers/unified'
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
  const sp = new UnifiedSearchProvider(['monitoring', 'setup'])
  const search = new UnifiedSearch('test-search', api, [sp])

  const result = search.search('test')

  expect(result).toBeDefined()
  expect(result?.get(sp.id)).toBeDefined()
})

test('Unified search instance with setup & monitoring search provider, returns proper unified search result', async () => {
  mockLegacyGetResponse.mockReturnValue(
    new Promise((resolve) => {
      setTimeout(() => {
        resolve('any type of response string')
      }, 100)
    })
  )

  const sp = new UnifiedSearchProvider(['monitoring', 'setup'])
  const search = new UnifiedSearch('test-search', api, [sp])

  const result = search.search('test')

  expect(result).toBeDefined()

  const uRes = (await result?.get(sp.id)?.result) as string

  expect(uRes).toBe('any type of response string')
})
