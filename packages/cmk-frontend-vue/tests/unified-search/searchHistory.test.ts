/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UnifiedSearchResultItem } from 'cmk-shared-typing/typescript/unified_search'
import { nextTick } from 'vue'

import { SearchHistorySearchProvider } from '@/unified-search/lib/providers/history'
import { HistoryEntry, SearchHistoryService } from '@/unified-search/lib/searchHistory'
import type { FilterOption } from '@/unified-search/providers/search-utils.types'

interface EntryOptions {
  filters?: FilterOption[]
  input?: string
  provider?: UnifiedSearchResultItem['provider']
  topic?: string
  url?: string
}

const buildEntry = (title: string, options: EntryOptions = {}): HistoryEntry =>
  new HistoryEntry(
    {
      input: options.input ?? title,
      filters: options.filters ?? [],
      sort: 'none',
      provider: 'all'
    },
    {
      title,
      target: { url: options.url ?? 'www.google.com' },
      context: 'test-context',
      provider: options.provider ?? 'monitoring',
      topic: options.topic ?? 'testTopic',
      icon: { type: 'default_icon', id: 'main-search' }
    }
  )

const titlesOf = (entries: HistoryEntry[]): string[] => entries.map((entry) => entry.element.title)

beforeEach(() => {
  localStorage.clear()
})

test('Add hist entry on search history service', async () => {
  const searchHistory = new SearchHistoryService('test-search')

  const histE = new HistoryEntry(
    { input: 'test', filters: [], sort: 'none', provider: 'all' },
    {
      title: 'testTitle',
      target: { url: 'www.google.com' },
      context: 'test-context',
      provider: 'monitoring',
      topic: 'testTopic',
      icon: { type: 'default_icon', id: 'main-search' }
    }
  )
  searchHistory.add(histE)
  expect(searchHistory.getEntries()[0]).toMatchObject(histE)
})

test('Add hist entry twice on search history service', async () => {
  const searchHistory = new SearchHistoryService('test-search')

  const histE = new HistoryEntry(
    { input: 'test', filters: [], sort: 'none', provider: 'all' },
    {
      title: 'testTitle',
      target: { url: 'www.google.com' },
      context: 'test-context',
      provider: 'monitoring',
      topic: 'testTopic',
      icon: { type: 'default_icon', id: 'main-search' }
    }
  )
  searchHistory.add(histE)
  searchHistory.add(histE)
  expect(searchHistory.getEntries()[0]?.hitCount).toBe(2)
})

describe('SearchHistoryService.getEntries', () => {
  test('returns the entries of the requested provider only', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('monitored', { provider: 'monitoring' }))
    searchHistory.add(buildEntry('configured', { provider: 'setup' }))

    expect(titlesOf(searchHistory.getEntries('setup'))).toEqual(['configured'])
  })

  test('returns entries of every provider when none is requested', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('monitored', { provider: 'monitoring' }))
    searchHistory.add(buildEntry('configured', { provider: 'setup' }))

    expect(searchHistory.getEntries()).toHaveLength(2)
  })

  test('orders entries by date, most recently visited first', () => {
    const searchHistory = new SearchHistoryService('test-search')
    const older = buildEntry('older')
    older.date = 1000
    const newer = buildEntry('newer')
    newer.date = 2000
    searchHistory.add(older)
    searchHistory.add(newer)

    expect(titlesOf(searchHistory.getEntries())).toEqual(['newer', 'older'])
  })

  test('orders entries by hit count when requested', () => {
    const searchHistory = new SearchHistoryService('test-search')
    const rare = buildEntry('rare')
    rare.hitCount = 1
    const frequent = buildEntry('frequent')
    frequent.hitCount = 7
    searchHistory.add(rare)
    searchHistory.add(frequent)

    expect(titlesOf(searchHistory.getEntries(null, 'hitCount'))).toEqual(['frequent', 'rare'])
  })

  test('returns as many entries as the given limit allows', () => {
    const searchHistory = new SearchHistoryService('test-search')
    for (const title of ['one', 'two', 'three', 'four', 'five', 'six']) {
      searchHistory.add(buildEntry(title))
    }

    expect(searchHistory.getEntries(null, 'date', 5)).toHaveLength(5)
  })
})

describe('SearchHistoryService.getQueries', () => {
  test('ignores queries with an empty input', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('empty', { input: '' }))
    searchHistory.add(buildEntry('filled', { input: 'myhost' }))

    expect(searchHistory.getQueries().map((query) => query.input)).toEqual(['myhost'])
  })

  test('deduplicates queries with the same input and filters', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('first', { input: 'myhost' }))
    searchHistory.add(buildEntry('second', { input: 'myhost' }))

    expect(searchHistory.getQueries()).toHaveLength(1)
  })

  test('keeps queries apart that search the same term with different filters', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(
      buildEntry('byHost', {
        input: 'myhost',
        filters: [{ type: 'inline', value: 'h:', title: 'Host' }]
      })
    )
    searchHistory.add(
      buildEntry('byService', {
        input: 'myhost',
        filters: [{ type: 'inline', value: 's:', title: 'Service' }]
      })
    )

    expect(searchHistory.getQueries()).toHaveLength(2)
  })

  test('returns the most recent query first', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('first', { input: 'alpha' }))
    searchHistory.add(buildEntry('second', { input: 'beta' }))

    expect(searchHistory.getQueries().map((query) => query.input)).toEqual(['beta', 'alpha'])
  })

  test('keeps a repeated query at the position of its first occurrence', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('first', { input: 'alpha' }))
    searchHistory.add(buildEntry('second', { input: 'beta' }))
    searchHistory.add(buildEntry('third', { input: 'alpha' }))

    expect(searchHistory.getQueries().map((query) => query.input)).toEqual(['beta', 'alpha'])
  })

  test('returns as many queries as the given limit allows', () => {
    const searchHistory = new SearchHistoryService('test-search')
    for (const input of ['one', 'two', 'three', 'four', 'five', 'six']) {
      searchHistory.add(buildEntry(input, { input }))
    }

    expect(searchHistory.getQueries(5)).toHaveLength(5)
  })
})

describe('SearchHistoryService reset', () => {
  test('resetEntries clears the visited entries but keeps the queries', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('visited', { input: 'myhost' }))

    searchHistory.resetEntries()

    expect(searchHistory.getEntries()).toHaveLength(0)
    expect(searchHistory.getQueries()).toHaveLength(1)
  })

  test('resetQueries clears the queries but keeps the visited entries', () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('visited', { input: 'myhost' }))

    searchHistory.resetQueries()

    expect(searchHistory.getQueries()).toHaveLength(0)
    expect(searchHistory.getEntries()).toHaveLength(1)
  })
})

describe('SearchHistoryService persistence', () => {
  test('restores the entries written by a previous search', async () => {
    new SearchHistoryService('test-search').add(buildEntry('persisted'))
    await nextTick()

    expect(titlesOf(new SearchHistoryService('test-search').getEntries())).toEqual(['persisted'])
  })

  test('keeps the history of different search instances apart', async () => {
    new SearchHistoryService('test-search').add(buildEntry('persisted'))
    await nextTick()

    expect(new SearchHistoryService('other-search').getEntries()).toHaveLength(0)
  })

  test('drops persisted entries that were written before results had a target', () => {
    localStorage.setItem(
      'search-history-test-search',
      JSON.stringify([
        { query: { input: 'legacy' }, element: { title: 'legacy', url: 'www.legacy.com' } },
        {
          query: { input: 'current' },
          element: { title: 'current', target: { url: 'www.current.com' } }
        }
      ])
    )

    expect(titlesOf(new SearchHistoryService('test-search').getEntries())).toEqual(['current'])
  })
})

test('Test SearchHistorySearchProvider', async () => {
  const searchHistory = new SearchHistoryService('test-search')
  const histSearch = new SearchHistorySearchProvider(searchHistory)

  const histE1 = new HistoryEntry(
    { input: 'test', filters: [], sort: 'none', provider: 'all' },
    {
      title: 'testTitle',
      target: { url: 'www.google.com' },
      context: 'test-context',
      provider: 'monitoring',
      topic: 'testTopic',
      icon: { type: 'default_icon', id: 'main-search' }
    }
  )

  const histE2 = new HistoryEntry(
    { input: 'abc', filters: [], sort: 'none', provider: 'all' },
    {
      title: 'abcTitle',
      target: { url: 'www.abc.com' },
      context: 'abc-context',
      provider: 'setup',
      topic: 'testTopic',
      icon: { type: 'default_icon', id: 'main-search' }
    }
  )
  searchHistory.add(histE1)
  searchHistory.add(histE2)

  const { entries, queries } = await histSearch.search(
    {
      input: 'abc',
      filters: [],
      sort: 'none',
      provider: 'all'
    },
    new AbortController().signal
  )

  expect(entries).toMatchObject([histE2])
  expect(queries).toMatchObject([histE2.query])
})

describe('SearchHistorySearchProvider', () => {
  test('is skipped for a query that selects a search operator', () => {
    const provider = new SearchHistorySearchProvider(new SearchHistoryService('test-search'))

    expect(
      provider.shouldExecuteSearch({ input: '/host', filters: [], sort: 'none', provider: 'all' })
    ).toBe(false)
  })

  test('already searches for a single character', () => {
    const provider = new SearchHistorySearchProvider(new SearchHistoryService('test-search'))

    expect(
      provider.shouldExecuteSearch({ input: 'a', filters: [], sort: 'none', provider: 'all' })
    ).toBe(true)
  })

  test('returns only entries of the requested provider', async () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('monitored', { input: 'host', provider: 'monitoring' }))
    searchHistory.add(buildEntry('configured', { input: 'host', provider: 'setup' }))

    const { entries } = await new SearchHistorySearchProvider(searchHistory).search(
      { input: 'host', filters: [], sort: 'none', provider: 'setup' },
      new AbortController().signal
    )

    expect(titlesOf(entries)).toEqual(['configured'])
  })

  test('matches an entry by its topic', async () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('byTopic', { input: 'unrelated', topic: 'Hosts' }))

    const { entries } = await new SearchHistorySearchProvider(searchHistory).search(
      { input: 'Hosts', filters: [], sort: 'none', provider: 'all' },
      new AbortController().signal
    )

    expect(titlesOf(entries)).toEqual(['byTopic'])
  })

  test('matches an entry by its url', async () => {
    const searchHistory = new SearchHistoryService('test-search')
    searchHistory.add(buildEntry('byUrl', { input: 'unrelated', url: 'wato.py?mode=hosts' }))

    const { entries } = await new SearchHistorySearchProvider(searchHistory).search(
      { input: 'wato.py', filters: [], sort: 'none', provider: 'all' },
      new AbortController().signal
    )

    expect(titlesOf(entries)).toEqual(['byUrl'])
  })
})
