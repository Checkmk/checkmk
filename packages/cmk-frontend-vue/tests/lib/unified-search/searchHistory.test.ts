/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { SearchHistorySearchProvider } from '@/lib/unified-search/providers/history'
import { HistoryEntry, SearchHistoryService } from '@/lib/unified-search/searchHistory'

beforeEach(() => {
  localStorage.clear()
})

test('Add hist entry on search history service', async () => {
  const searchHistory = new SearchHistoryService('test-search')

  const histE = new HistoryEntry('test', {
    title: 'testTitle',
    url: 'www.google.com',
    context: 'test-context',
    provider: 'monitoring',
    topic: 'testTopic'
  })
  searchHistory.add(histE)
  expect(searchHistory.getEntries()[0]).toMatchObject(histE)
})

test('Add hist entry twice on search history service', async () => {
  const searchHistory = new SearchHistoryService('test-search')

  const histE = new HistoryEntry('test', {
    title: 'testTitle',
    url: 'www.google.com',
    context: 'test-context',
    provider: 'monitoring',
    topic: 'testTopic'
  })
  searchHistory.add(histE)
  searchHistory.add(histE)
  expect(searchHistory.getEntries()[0]?.hitCount).toBe(2)
})

test('Test SearchHistorySearchProvider', async () => {
  const searchHistory = new SearchHistoryService('test-search')
  const histSearch = new SearchHistorySearchProvider(searchHistory)

  const histE1 = new HistoryEntry('test', {
    title: 'testTitle',
    url: 'www.google.com',
    context: 'test-context',
    provider: 'monitoring',
    topic: 'testTopic'
  })

  const histE2 = new HistoryEntry('abc', {
    title: 'abcTitle',
    url: 'www.abc.com',
    context: 'abc-context',
    provider: 'setup',
    topic: 'testTopic'
  })
  searchHistory.add(histE1)
  searchHistory.add(histE2)

  const { entries, queries } = await histSearch.search('abc')

  expect(entries).toMatchObject([histE2])
  expect(queries).toMatchObject([histE2.query])
})
