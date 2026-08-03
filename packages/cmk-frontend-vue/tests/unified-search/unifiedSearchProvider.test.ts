/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from 'cmk-ui-library/lib/api-client'

import { UnifiedSearchProvider } from '@/unified-search/lib/providers/unified'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

const buildQuery = (query: Partial<UnifiedSearchQueryLike> = {}): UnifiedSearchQueryLike => ({
  input: 'test',
  provider: 'all',
  filters: [],
  sort: 'weighted_index',
  ...query
})

const buildProvider = (): UnifiedSearchProvider =>
  new UnifiedSearchProvider(['monitoring', 'customize', 'setup'])

describe('UnifiedSearchProvider.shouldExecuteSearch', () => {
  test('rejects a query starting with a slash, which selects a search operator', () => {
    expect(buildProvider().shouldExecuteSearch(buildQuery({ input: '/host' }))).toBe(false)
  })

  test('rejects a query shorter than the minimum input length', () => {
    expect(buildProvider().shouldExecuteSearch(buildQuery({ input: 'a' }))).toBe(false)
  })

  test('accepts a query of exactly the minimum input length', () => {
    expect(buildProvider().shouldExecuteSearch(buildQuery({ input: 'ab' }))).toBe(true)
  })

  test('rejects an empty query', () => {
    expect(buildProvider().shouldExecuteSearch(buildQuery({ input: '' }))).toBe(false)
  })

  test('measures the encoded query, so a single escaped character passes as long enough', () => {
    expect(buildProvider().shouldExecuteSearch(buildQuery({ input: 'ä' }))).toBe(true)
  })
})

describe('UnifiedSearchProvider.manipulateSearchQuery', () => {
  test('switches to monitoring when an inline filter is unavailable for other providers', () => {
    const { manipulatedQuery, isManipulated } = buildProvider().manipulateSearchQuery(
      buildQuery({ input: 'h:myhost' })
    )

    expect(isManipulated).toBe(true)
    expect(manipulatedQuery.provider).toBe('monitoring')
  })

  test('switches to monitoring for a service state filter', () => {
    const { manipulatedQuery, isManipulated } = buildProvider().manipulateSearchQuery(
      buildQuery({ input: 'st:crit' })
    )

    expect(isManipulated).toBe(true)
    expect(manipulatedQuery.provider).toBe('monitoring')
  })

  test('keeps the query untouched when no inline filter is used', () => {
    const query = buildQuery({ input: 'myhost' })
    const { manipulatedQuery, isManipulated } = buildProvider().manipulateSearchQuery(query)

    expect(isManipulated).toBe(false)
    expect(manipulatedQuery).toEqual(query)
  })

  test('never overrides a provider the user selected explicitly', () => {
    const query = buildQuery({ input: 'h:myhost', provider: 'setup' })
    const { manipulatedQuery, isManipulated } = buildProvider().manipulateSearchQuery(query)

    expect(isManipulated).toBe(false)
    expect(manipulatedQuery.provider).toBe('setup')
  })

  test('does not mutate the query that is bound to the input field', () => {
    const query = buildQuery({ input: 'h:myhost' })
    buildProvider().manipulateSearchQuery(query)

    expect(query.provider).toBe('all')
  })

  test('does not confuse a longer filter prefix with a shorter one', () => {
    const { isManipulated } = buildProvider().manipulateSearchQuery(
      buildQuery({ input: 'hg:mygroup' })
    )

    expect(isManipulated).toBe(true)
  })

  test('matches a filter prefix anywhere in the query, so a pasted url selects monitoring', () => {
    const { manipulatedQuery, isManipulated } = buildProvider().manipulateSearchQuery(
      buildQuery({ input: 'https://myhost' })
    )

    expect(isManipulated).toBe(true)
    expect(manipulatedQuery.provider).toBe('monitoring')
  })
})

describe('UnifiedSearchProvider.search', () => {
  const api = new Api()
  const apiGet = vitest.fn()

  const requestedUrl = async (query: Partial<UnifiedSearchQueryLike>): Promise<string> => {
    const provider = buildProvider()
    provider.injectApi(api)
    await provider.search(buildQuery(query), new AbortController().signal)
    return apiGet.mock.calls[0]?.[0] as string
  }

  beforeAll(() => {
    api.get = apiGet
  })

  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue(null)
  })

  test('omits the provider parameter when searching across all providers', async () => {
    expect(await requestedUrl({ input: 'myhost' })).toBe(
      'ajax_unified_search.py?q=myhost&sort=weighted_index&collapse=1'
    )
  })

  test('passes an explicitly selected provider to the backend', async () => {
    expect(await requestedUrl({ input: 'myhost', provider: 'setup' })).toBe(
      'ajax_unified_search.py?q=myhost&provider=setup&sort=weighted_index&collapse=1'
    )
  })

  test('passes the requested sort type to the backend', async () => {
    expect(await requestedUrl({ input: 'myhost', sort: 'alphabetic' })).toContain(
      '&sort=alphabetic'
    )
  })

  test('strips the leading slash of a search operator query', async () => {
    expect(await requestedUrl({ input: '/myhost' })).toContain('?q=myhost&')
  })

  test('encodes characters that would otherwise be read as query parameters', async () => {
    expect(await requestedUrl({ input: 'foo & bar' })).toContain('?q=foo%20%26%20bar&')
  })

  test('forwards the abort signal so a superseded search can be cancelled', async () => {
    const abortController = new AbortController()
    const provider = buildProvider()
    provider.injectApi(api)

    await provider.search(buildQuery(), abortController.signal)

    expect(apiGet.mock.calls[0]?.[1]).toMatchObject({
      exceptOnNonZeroResultCode: true,
      signal: abortController.signal
    })
  })

  test('fails loudly when no api has been injected', async () => {
    await expect(
      buildProvider().search(buildQuery(), new AbortController().signal)
    ).rejects.toThrow('api not set')
  })
})
