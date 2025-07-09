/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { SearchProvider, type SearchProviderResult } from '../unified-search'
import type { HistoryEntry, SearchHistoryService } from '../searchHistory'

export type SearchHistorySearchResult = SearchProviderResult<{
  entries: HistoryEntry[]
  queries: string[]
}>

export class SearchHistorySearchProvider extends SearchProvider {
  constructor(
    private searchHistory: SearchHistoryService,
    public override title?: string,
    public override sort: number = 0,
    public override minInputlength: number = 0
  ) {
    super('search-history')
  }

  public async search(input: string): Promise<{ entries: HistoryEntry[]; queries: string[] }> {
    return new Promise((resolve) => {
      resolve({
        entries: this.searchHistory
          .getEntries()
          .filter((hist) => {
            return (
              hist.query.indexOf(input) >= 0 ||
              hist.element.topic.indexOf(input) >= 0 ||
              hist.element.title.indexOf(input) >= 0 ||
              hist.element.url.indexOf(input) >= 0
            )
          })
          .sort((a, b) => b.date - a.date),
        queries: this.searchHistory.getQueries().filter((hist) => {
          return hist.indexOf(input) >= 0
        })
      })
    })
  }
}
