/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { SearchProvider, type SearchProviderResult } from '../unified-search'
import type { HistoryEntry, SearchHistoryService } from '../searchHistory'

export type SearchHistorySearchResult = SearchProviderResult<HistoryEntry[]>

export class SearchHistorySearchProvider extends SearchProvider {
  constructor(private searchHistory: SearchHistoryService) {
    super('search-history')
  }

  public async search(input: string): Promise<HistoryEntry[]> {
    return new Promise((resolve) => {
      resolve(
        this.searchHistory
          .get()
          .filter((hist) => {
            return (
              hist.query.indexOf(input) >= 0 ||
              hist.topic.indexOf(input) >= 0 ||
              hist.element.title.indexOf(input) >= 0 ||
              hist.element.url.indexOf(input) >= 0
            )
          })
          .sort((a, b) => b.date - a.date)
      )
    })
  }
}
