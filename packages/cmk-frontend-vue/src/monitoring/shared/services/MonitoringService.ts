/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import { type ComputedRef, type Ref, computed, ref, shallowRef } from 'vue'

import type { KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'

import type { FilterNode } from '@/monitoring/shared/api/types'
import { POLL_INTERVAL_MS } from '@/monitoring/shared/constants'

export interface PagedResponse<T> {
  items: T[]
  meta: {
    total: number
  }
}

export abstract class MonitoringService<T> extends ServiceBase {
  readonly items: Ref<T[]> = shallowRef<T[]>([])
  readonly total: Ref<number> = ref(0)
  readonly loading: Ref<boolean> = ref(false)
  readonly sortState: Ref<SortingState> = ref<SortingState>([])
  readonly searchQuery: Ref<string> = ref('')
  readonly filterState: Ref<FilterNode | undefined> = ref(undefined)

  readonly pollIntervalSeconds: number
  readonly secondsRemaining: Ref<number>
  readonly manualPaused: Ref<boolean> = ref(false)
  private readonly autoPauseCount: Ref<number> = ref(0)
  readonly paused: ComputedRef<boolean> = computed(
    () => this.manualPaused.value || this.autoPauseCount.value > 0
  )

  private initialFetchTimer: ReturnType<typeof setTimeout> | null = null
  private tickTimer: ReturnType<typeof setInterval> | null = null

  constructor(
    serviceId: string,
    shortCutService: KeyShortcutService,
    pollIntervalMs: number = POLL_INTERVAL_MS
  ) {
    super(serviceId, shortCutService)
    this.pollIntervalSeconds = Math.max(1, Math.round(pollIntervalMs / 1000))
    this.secondsRemaining = ref(this.pollIntervalSeconds)
    this.initShortCuts()
    this.initialFetchTimer = setTimeout(() => {
      this.initialFetchTimer = null
      void this.fetch()
    }, 0)
    this.tickTimer = setInterval(() => {
      this.tick()
    }, 1000)
  }

  private tick(): void {
    if (this.paused.value) {
      return
    }
    if (this.secondsRemaining.value <= 1) {
      void this.fetch()
    } else {
      this.secondsRemaining.value -= 1
    }
  }

  togglePause(): void {
    this.manualPaused.value = !this.manualPaused.value
  }

  beginAutoPause(): void {
    this.autoPauseCount.value += 1
  }

  endAutoPause(): void {
    this.autoPauseCount.value = Math.max(0, this.autoPauseCount.value - 1)
  }

  protected abstract fetchBatch(): Promise<PagedResponse<T>>

  onFocusSearch(callback: () => void): void {
    this.pushCallBack('focus-search', callback)
  }

  private focusSearch(): void {
    this.dispatchCallback('focus-search')
  }

  private initShortCuts(): void {
    this.registerShortCut({ key: ['/'], preventDefault: true }, () => this.focusSearch())
    this.enableShortCuts()
  }

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
    const nodes = columnFilters.flatMap((f) => {
      const node = f.value as FilterNode | undefined
      return node ? [node] : []
    })
    if (nodes.length === 0) {
      return undefined
    }
    if (nodes.length === 1) {
      return nodes[0]!
    }
    return { type: 'and', children: nodes }
  }

  stopPolling(): void {
    if (this.initialFetchTimer !== null) {
      clearTimeout(this.initialFetchTimer)
      this.initialFetchTimer = null
    }
    if (this.tickTimer !== null) {
      clearInterval(this.tickTimer)
      this.tickTimer = null
    }
  }

  destruct(): void {
    this.stopPolling()
    this.disableShortCuts()
    this.removeCallbacks()
  }

  private async fetch(): Promise<void> {
    if (this.loading.value) {
      return
    }
    this.secondsRemaining.value = this.pollIntervalSeconds
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
