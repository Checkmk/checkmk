/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import { type Ref, ref, shallowRef } from 'vue'

import type { FilterNode, HostState } from '@/monitoring/shared/api/types'
import { POLL_INTERVAL_MS } from '@/monitoring/shared/constants'

export interface PagedResponse<T> {
  items: T[]
  meta: {
    total: number
  }
}

export abstract class MonitoringService<T> {
  readonly items: Ref<T[]> = shallowRef<T[]>([])
  readonly total: Ref<number> = ref(0)
  readonly loading: Ref<boolean> = ref(false)
  readonly sortState: Ref<SortingState> = ref<SortingState>([])
  readonly searchQuery: Ref<string> = ref('')
  readonly filterState: Ref<FilterNode | undefined> = ref(undefined)

  private initialFetchTimer: ReturnType<typeof setTimeout> | null = null
  private pollTimer: ReturnType<typeof setInterval> | null = null

  constructor(pollIntervalMs: number = POLL_INTERVAL_MS) {
    this.initialFetchTimer = setTimeout(() => {
      this.initialFetchTimer = null
      void this.fetch()
    }, 0)
    this.pollTimer = setInterval(() => {
      void this.fetch()
    }, pollIntervalMs)
  }

  protected abstract fetchBatch(): Promise<PagedResponse<T>>

  updateSort(sortState: SortingState): void {
    this.sortState.value = sortState
    void this.fetch()
  }

  updateSearch(searchQuery: string): void {
    this.searchQuery.value = searchQuery
    void this.fetch()
  }

  updateFilters(columnFilters: ColumnFiltersState): void {
    this.filterState.value = this.buildFilter(columnFilters)
    void this.fetch()
  }

  private buildFilter(columnFilters: ColumnFiltersState): FilterNode | undefined {
    const conditions = columnFilters
      .map((filter) => this.columnFilterToNode(filter))
      .filter((node): node is FilterNode => node !== undefined)
    if (conditions.length === 0) {
      return undefined
    }
    if (conditions.length === 1) {
      return conditions[0]
    }
    return { type: 'and', children: conditions }
  }

  private columnFilterToNode(filter: { id: string; value: unknown }): FilterNode | undefined {
    switch (filter.id) {
      case 'state':
        return this.stateCondition(filter.value)
      default:
        return undefined
    }
  }

  private stateCondition(value: unknown): FilterNode | undefined {
    if (!Array.isArray(value) || value.length === 0) {
      return undefined
    }
    return { type: 'condition', field: 'state', op: 'one_of', value: value as HostState[] }
  }

  stopPolling(): void {
    if (this.initialFetchTimer !== null) {
      clearTimeout(this.initialFetchTimer)
      this.initialFetchTimer = null
    }
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  }

  private async fetch(): Promise<void> {
    if (this.loading.value) {
      return
    }
    this.loading.value = true
    try {
      const response = await this.fetchBatch()
      this.items.value = response.items
      this.total.value = response.meta.total
    } catch (error: unknown) {
      console.error('MonitoringService: fetchBatch failed', error)
    } finally {
      this.loading.value = false
    }
  }
}
