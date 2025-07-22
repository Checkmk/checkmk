/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { SearchProvider, type SearchProviderResult } from '../unified-search'
import type { HistoryEntry, SearchHistoryService } from '../searchHistory'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils'

export type SearchHistorySearchResult = SearchProviderResult<{
  entries: HistoryEntry[]
  queries: UnifiedSearchQueryLike[]
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

  public override shouldExecuteSearch(query: UnifiedSearchQueryLike): boolean {
    if (query.input.indexOf('/') === 0) {
      return false
    }

    return super.shouldExecuteSearch(query)
  }

  public async search(
    query: UnifiedSearchQueryLike
  ): Promise<{ entries: HistoryEntry[]; queries: UnifiedSearchQueryLike[] }> {
    return new Promise((resolve) => {
      resolve({
        entries: this.searchHistory
          .getEntries()
          .filter((hist) => {
            return (
              (hist.query as UnifiedSearchQueryLike).input.indexOf(query.input) >= 0 ||
              hist.element.topic.indexOf(query.input) >= 0 ||
              hist.element.title.indexOf(query.input) >= 0 ||
              hist.element.url.indexOf(query.input) >= 0
            )
          })
          .sort((a, b) => b.date - a.date),
        queries: this.searchHistory.getQueries().filter((hist) => {
          return hist.input.indexOf(query.input) >= 0
        })
      })
    })
  }
}
