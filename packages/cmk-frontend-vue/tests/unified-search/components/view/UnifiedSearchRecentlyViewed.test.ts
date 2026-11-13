/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import UnifiedSearchRecentlyViewed from '@/unified-search/components/view/UnifiedSearchRecentlyViewed.vue'
import { HistoryEntry } from '@/unified-search/lib/searchHistory'
import { initSearchUtils, searchUtilsProvider } from '@/unified-search/providers/search-utils'

function entry(title: string, topic: string, url: string): HistoryEntry {
  return new HistoryEntry(
    { input: title, filters: [], sort: 'none', provider: 'all' },
    { title, topic, target: { url }, provider: 'monitoring' }
  )
}

test('keeps apart the entries of one host found by name and by alias', async () => {
  // Both results of the host open the same page, so they share the URL.
  const hostUrl = 'monitor_host_services.py?host=myhost&site=mysite'
  const byName = entry('myhost', 'Host name', hostUrl)
  const other = entry('otherhost', 'Host name', 'monitor_host_services.py?host=otherhost')
  const { rerender } = render(UnifiedSearchRecentlyViewed, {
    props: { historyEntries: [byName, other], focus: -1 },
    global: { provide: { [searchUtilsProvider]: initSearchUtils('test') } }
  })

  await rerender({
    historyEntries: [other, entry('My alias', 'Host alias', hostUrl), byName],
    focus: -1
  })

  expect(screen.getAllByRole('link').map((link) => link.textContent)).toEqual([
    expect.stringContaining('otherhost'),
    expect.stringContaining('My alias'),
    expect.stringContaining('myhost')
  ])
})
