/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'
import usePersistentRef from '../usePersistentRef'
import type { UnifiedSearchResultElement } from './providers/unified-search-result'

export class HistoryEntry {
  public hitCount = 1
  public date = Date.now()

  constructor(
    public query: string,
    public provider: string,
    public element: UnifiedSearchResultElement,
    public topic: string
  ) {}
}

export class SearchHistoryService {
  private entries: Ref<HistoryEntry[]>

  constructor(public searchId: string) {
    this.entries = usePersistentRef<HistoryEntry[]>(
      'search-history-'.concat(this.searchId),
      [],
      'local'
    )
  }
  public get(
    provider: string | null = null,
    by: 'date' | 'hitCount' = 'date',
    limit?: number
  ): HistoryEntry[] {
    return this.entries.value
      .filter((e) => e.provider === provider || provider === null)
      .sort((a, b) => b[by] - a[by])
      .slice(0, limit ? limit - 1 : limit)
  }

  public add(historyEntry: HistoryEntry): void {
    let found = false

    const entries = this.getEntriesCopy()

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

  public remove(historyEntry: HistoryEntry): void {
    let idx = -1

    const entries = this.getEntriesCopy()
    entries.forEach((hist, i) => {
      if (historyEntry.element.title === hist.element.title) {
        idx = i
      }
    })

    if (idx >= 0) {
      delete entries[idx]
    }

    this.entries.value = entries
  }

  private getEntriesCopy(): HistoryEntry[] {
    const entries: HistoryEntry[] = []
    return entries.concat(this.entries.value)
  }
}
