/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UnifiedSearchResultItem } from 'cmk-shared-typing/typescript/unified_search'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import type { Ref } from 'vue'

import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

export class HistoryEntry {
  public hitCount = 1
  public date = Date.now()

  constructor(
    public query: UnifiedSearchQueryLike,
    public element: UnifiedSearchResultItem
  ) {}
}

export class SearchHistoryService {
  private entries: Ref<HistoryEntry[]>
  private queries: Ref<UnifiedSearchQueryLike[]>

  constructor(public searchId: string) {
    this.entries = usePersistentRef<HistoryEntry[]>(
      'search-history-'.concat(this.searchId),
      [],
      // Migration helper for all people running 2.5 daily builds, could be
      // removed just before release
      (entries) => (entries as HistoryEntry[]).filter((entry) => 'target' in entry.element),
      'local'
    )

    this.queries = usePersistentRef<UnifiedSearchQueryLike[]>(
      'search-queries-'.concat(this.searchId),
      [],
      (v) => v as UnifiedSearchQueryLike[],
      'local'
    )
  }
  public getEntries(
    provider: string | null = null,
    by: 'date' | 'hitCount' = 'date',
    limit?: number
  ): HistoryEntry[] {
    return this.entries.value
      .filter((e) => e.element.provider === provider || provider === null)
      .sort((a, b) => b[by] - a[by])
      .slice(0, limit)
  }

  public getQueries(limit?: number): UnifiedSearchQueryLike[] {
    return this.queries.value
      .filter((q) => q.input !== '')
      .filter((value, index, array) => {
        return (
          array.findIndex(
            (i) =>
              i.input === value.input && JSON.stringify(i.filters) === JSON.stringify(value.filters)
          ) === index
        )
      })
      .reverse()
      .slice(0, limit)
  }

  public add(historyEntry: HistoryEntry): void {
    this.addEntry(historyEntry)
    this.addQuery(historyEntry)
  }

  public addEntry(historyEntry: HistoryEntry): void {
    let found = false

    const [entries] = this.getCopy()

    entries.forEach((hist) => {
      if (historyEntry.element.title === hist.element.title) {
        hist.hitCount++
        hist.date = Date.now()
        found = true
      }
    })

    if (found === false) {
      entries.push(historyEntry)
    }
    this.entries.value = entries
  }

  public addQuery(historyEntry: HistoryEntry): void {
    const [, queries] = this.getCopy()

    queries.push(historyEntry.query as UnifiedSearchQueryLike)
    this.queries.value = queries
  }

  public resetEntries(): void {
    this.entries.value = []
  }

  public resetQueries(): void {
    this.queries.value = []
  }

  private getCopy(): [HistoryEntry[], UnifiedSearchQueryLike[]] {
    return [this.getEntriesCopy(), this.getQueriesCopy()]
  }

  private getEntriesCopy(): HistoryEntry[] {
    const entries: HistoryEntry[] = []
    return entries.concat(this.entries.value)
  }

  private getQueriesCopy(): UnifiedSearchQueryLike[] {
    const queries: UnifiedSearchQueryLike[] = []
    return queries.concat(this.queries.value)
  }
}
