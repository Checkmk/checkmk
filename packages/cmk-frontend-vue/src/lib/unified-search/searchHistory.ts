/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'

import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

import usePersistentRef from '../usePersistentRef'
import type { UnifiedSearchResultElement } from './providers/unified'

export class HistoryEntry {
  public hitCount = 1
  public date = Date.now()

  constructor(
    public query: UnifiedSearchQueryLike,
    public element: UnifiedSearchResultElement
  ) {}
}

export class SearchHistoryService {
  private entries: Ref<HistoryEntry[]>
  private queries: Ref<UnifiedSearchQueryLike[]>

  constructor(public searchId: string) {
    this.entries = usePersistentRef<HistoryEntry[]>(
      'search-history-'.concat(this.searchId),
      [],
      'local'
    )

    this.queries = usePersistentRef<UnifiedSearchQueryLike[]>(
      'search-queries-'.concat(this.searchId),
      [],
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
            (i) => i.input === value.input && i.filters.toString() === value.filters.toString()
          ) === index
        )
      })
      .reverse()
      .slice(0, limit ? limit - 1 : limit)
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

  public remove(historyEntry: HistoryEntry): void {
    let idx = -1

    const [entries, queries] = this.getCopy()
    entries.forEach((hist, i) => {
      if (historyEntry.element.title === hist.element.title) {
        idx = i
      }
    })

    if (idx >= 0) {
      delete entries[idx]
    }

    idx = queries.indexOf(historyEntry.query as UnifiedSearchQueryLike)
    if (idx !== -1) {
      queries.splice(idx, 1)
    }

    this.queries.value = queries
    this.entries.value = entries
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
