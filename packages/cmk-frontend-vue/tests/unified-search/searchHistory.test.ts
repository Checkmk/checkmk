/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { SearchHistorySearchProvider } from '@/unified-search/lib/providers/history'
import { HistoryEntry, SearchHistoryService } from '@/unified-search/lib/searchHistory'

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
