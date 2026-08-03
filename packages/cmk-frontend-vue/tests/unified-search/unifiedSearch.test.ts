/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from 'cmk-ui-library/lib/api-client'

import { UnifiedSearchProvider } from '@/unified-search/lib/providers/unified'
import {
  SearchProvider,
  UnifiedSearch,
  UnifiedSearchAborted,
  UnifiedSearchError
} from '@/unified-search/lib/unified-search'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

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

  const result = search.search({ input: 'test', filters: [], provider: 'all', sort: 'ut' })

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

  const result = search.search({ input: 'test', filters: [], provider: 'all', sort: 'ut' })

  expect(result).toBeDefined()

  const uRes = (await result?.get(sp.id)?.result) as string

  expect(uRes).toBe('any type of response string')
})

const buildQuery = (query: Partial<UnifiedSearchQueryLike> = {}): UnifiedSearchQueryLike => ({
  input: 'myhost',
  provider: 'all',
  filters: [],
  sort: 'weighted_index',
  ...query
})

class TestSearchProvider extends SearchProvider {
  public searchCalls = 0

  constructor(
    id: string,
    private response: () => Promise<unknown> = () => Promise.resolve('result'),
    minInputLength = 2
  ) {
    super(id, undefined, 0, minInputLength)
  }

  public async search(): Promise<unknown> {
    this.searchCalls++
    return this.response()
  }
}

describe('UnifiedSearch provider registry', () => {
  const first = new TestSearchProvider('first')
  const second = new TestSearchProvider('second')
  const search = new UnifiedSearch('test-search', api, [first, second])

  test('lists the ids of all registered providers', () => {
    expect(search.getProviderIds()).toEqual(['first', 'second'])
  })

  test('returns a provider by id', () => {
    expect(search.get('second')).toBe(second)
  })

  test('returns null for an unknown provider id', () => {
    expect(search.get('unknown')).toBeNull()
  })

  test('returns every provider when no id is given', () => {
    expect(search.get()).toEqual([first, second])
  })

  test('has no result registered for a provider that did not run', () => {
    expect(search.search(buildQuery()).get('unknown')).toBeNull()
  })

  test('registers a result for every provider', () => {
    expect(search.search(buildQuery()).getAll()).toHaveLength(2)
  })
})

describe('UnifiedSearch.initSearch', () => {
  afterEach(() => {
    vitest.useRealTimers()
  })

  test('does not search before the debounce delay has elapsed', async () => {
    vitest.useFakeTimers()
    const provider = new TestSearchProvider('fake')
    const search = new UnifiedSearch('test-search', api, [provider])
    const onSearch = vitest.fn()
    search.onSearch(onSearch)

    search.onInput(buildQuery())
    await vitest.advanceTimersByTimeAsync(249)

    expect(onSearch).not.toHaveBeenCalled()
    expect(provider.searchCalls).toBe(0)
  })

  test('searches once the input has settled', async () => {
    vitest.useFakeTimers()
    const provider = new TestSearchProvider('fake')
    const search = new UnifiedSearch('test-search', api, [provider])
    const onSearch = vitest.fn()
    search.onSearch(onSearch)

    search.onInput(buildQuery())
    await vitest.advanceTimersByTimeAsync(250)

    expect(provider.searchCalls).toBe(1)
    expect(onSearch.mock.calls[0]?.[0]).toBeDefined()
  })

  test('reports keystrokes that were superseded without searching for them', async () => {
    vitest.useFakeTimers()
    const provider = new TestSearchProvider('fake')
    const search = new UnifiedSearch('test-search', api, [provider])
    const onSearch = vitest.fn()
    search.onSearch(onSearch)

    search.onInput(buildQuery({ input: 'my' }))
    await vitest.advanceTimersByTimeAsync(100)
    search.onInput(buildQuery({ input: 'myhost' }))
    await vitest.advanceTimersByTimeAsync(250)

    expect(provider.searchCalls).toBe(1)
    expect(onSearch).toHaveBeenCalledTimes(2)
    expect(onSearch.mock.calls[0]).toEqual([])
    expect(onSearch.mock.calls[1]?.[0]).toBeDefined()
  })
})

describe('UnifiedSearch.search', () => {
  test('aborts a running search when a new one is started', async () => {
    const provider = new TestSearchProvider('fake', () => new Promise(() => {}))
    const search = new UnifiedSearch('test-search', api, [provider])

    const superseded = search.search(buildQuery())
    search.search(buildQuery())

    expect(await superseded.get('fake')?.result).toBeInstanceOf(UnifiedSearchAborted)
  })

  test('skips a provider whose minimum input length is not reached', async () => {
    const provider = new TestSearchProvider('fake')
    const search = new UnifiedSearch('test-search', api, [provider])

    const result = search.search(buildQuery({ input: 'a' }))

    expect(await result.get('fake')?.result).toBeNull()
    expect(provider.searchCalls).toBe(0)
  })

  test('turns a failing provider into an error result instead of rejecting', async () => {
    const provider = new TestSearchProvider('fake', () =>
      Promise.reject(new Error('livestatus is not running'))
    )
    const search = new UnifiedSearch('test-search', api, [provider])

    const result = await search.search(buildQuery()).get('fake')?.result

    expect(result).toBeInstanceOf(UnifiedSearchError)
    expect((result as UnifiedSearchError).provider).toBe('fake')
    expect((result as UnifiedSearchError).message).toBe('livestatus is not running')
  })

  test('falls back to a generic message when the provider gives no reason', async () => {
    const provider = new TestSearchProvider('fake', () => Promise.reject(new Error('')))
    const search = new UnifiedSearch('test-search', api, [provider])

    const result = await search.search(buildQuery()).get('fake')?.result

    expect((result as UnifiedSearchError).message).toBe(
      'Unknown error. Are all Checkmk services running?'
    )
  })

  test('marks the provider as active while its search is running', () => {
    const provider = new TestSearchProvider('fake', () => new Promise(() => {}))
    const search = new UnifiedSearch('test-search', api, [provider])

    search.search(buildQuery())

    expect(provider.searchActive.value).toBe(true)
  })

  test('marks the provider as inactive once the search finished', async () => {
    const provider = new TestSearchProvider('fake')
    const search = new UnifiedSearch('test-search', api, [provider])

    await search.search(buildQuery()).get('fake')?.result

    await vitest.waitFor(() => {
      expect(provider.searchActive.value).toBe(false)
    })
  })

  test('keeps the original query when a provider manipulates it', () => {
    const provider = new TestSearchProvider('fake')
    provider.manipulateSearchQuery = (query: UnifiedSearchQueryLike) => ({
      manipulatedQuery: { ...query, provider: 'monitoring' },
      isManipulated: true
    })
    const search = new UnifiedSearch('test-search', api, [provider])

    const registered = search.search(buildQuery()).get('fake')

    expect(registered?.isManipulated).toBe(true)
    expect(registered?.query.provider).toBe('monitoring')
    expect(registered?.originalQuery?.provider).toBe('all')
  })

  test('reports no original query when the provider left it untouched', () => {
    const provider = new TestSearchProvider('fake')
    const search = new UnifiedSearch('test-search', api, [provider])

    const registered = search.search(buildQuery()).get('fake')

    expect(registered?.isManipulated).toBe(false)
    expect(registered?.originalQuery).toBeUndefined()
  })
})
