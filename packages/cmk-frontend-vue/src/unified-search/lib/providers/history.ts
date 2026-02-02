/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

import type { HistoryEntry, SearchHistoryService } from '../searchHistory'
import { SearchProvider, type SearchProviderResult } from '../unified-search'

export interface SearchHistoryResult {
  entries: HistoryEntry[]
  queries: UnifiedSearchQueryLike[]
}

export type HistorySearchProviderResult = SearchProviderResult<SearchHistoryResult>

export class SearchHistorySearchProvider extends SearchProvider {
  constructor(
    private searchHistory: SearchHistoryService,
    public override title?: string,
    public override sort: number = 0,
    public override minInputLength: number = 0
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
    query: UnifiedSearchQueryLike,
    _abortSignal: AbortSignal
  ): Promise<SearchHistoryResult> {
    return new Promise((resolve) => {
      resolve({
        entries: this.searchHistory
          .getEntries()
          .filter((hist) => {
            return query.provider === 'all' || query.provider === hist.element.provider
          })
          .filter((hist) => {
            return (
              query.input.length === 0 ||
              (hist.query as UnifiedSearchQueryLike).input.indexOf(query.input) >= 0 ||
              hist.element.topic.indexOf(query.input) >= 0 ||
              hist.element.title.indexOf(query.input) >= 0 ||
              hist.element.target.url.indexOf(query.input) >= 0
            )
          })
          .sort((a, b) => b.date - a.date),
        queries: this.searchHistory
          .getQueries()
          .filter((hist) => {
            return query.provider === 'all' || query.provider === hist.provider
          })
          .filter((hist) => {
            return hist.input.indexOf(query.input) >= 0
          })
      })
    })
  }
}
