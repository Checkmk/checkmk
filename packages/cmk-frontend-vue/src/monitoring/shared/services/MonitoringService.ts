/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import {
  type ComputedRef,
  type Ref,
  type WatchStopHandle,
  computed,
  ref,
  shallowRef,
  watch
} from 'vue'

import type { KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'

import type { FilterNode } from '@/monitoring/shared/api/types'
import { POLL_INTERVAL_MS } from '@/monitoring/shared/constants'

import { FilterStore, type QuickFilter, type QuickFilterConfig } from './FilterStore'
import { useColumnFilterBridge } from './useColumnFilterBridge'

export interface PagedResponse<T> {
  items: T[]
  meta: {
    total: number
  }
}

/**
 * The kind of fetch that produces visible rows:
 * - `'foreground'`: initial load or a user action (search/filter/sort) that
 *   replaces the visible rows and should show the loading skeleton.
 * - `'background'`: a refresh-timer poll that silently refreshes the rows.
 */
export type FetchKind = 'foreground' | 'background'

/** The current fetch state: a {@link FetchKind} in flight, or `'idle'`. */
export type FetchState = 'idle' | FetchKind

export interface MonitoringServiceOptions<T> {
  pollIntervalMs?: number | undefined
  /** Column definitions including optional column filters */
  columns?: ColumnDef<T>[]
  /** Quick-filter presets */
  quickFilters?: QuickFilterConfig[]
}

export abstract class MonitoringService<T> extends ServiceBase {
  readonly items: Ref<T[]> = shallowRef<T[]>([])
  readonly total: Ref<number> = ref(0)
  /** The kind of fetch currently in flight, or `'idle'`. */
  readonly fetchState: Ref<FetchState> = ref('idle')
  readonly hasLoaded: Ref<boolean> = ref(false)
  readonly sortState: Ref<SortingState> = ref<SortingState>([])
  readonly searchQuery: Ref<string> = ref('')
  readonly filterState: Ref<FilterNode | undefined> = ref(undefined)

  /** Owns all filter state: quick-filters and active conditions. */
  readonly filters: FilterStore
  /** Column filter state derived from {@link filters}, for binding to the table. */
  readonly tableColumnFilters: ComputedRef<ColumnFiltersState>
  /** Apply a table column-filter change back into {@link filters}. */
  readonly onColumnFiltersUpdate: (next: ColumnFiltersState) => void

  readonly pollIntervalSeconds: number
  readonly secondsRemaining: Ref<number>
  readonly manualPaused: Ref<boolean> = ref(false)
  private readonly autoPauseCount: Ref<number> = ref(0)
  readonly paused: ComputedRef<boolean> = computed(
    () => this.manualPaused.value || this.autoPauseCount.value > 0
  )

  private initialFetchTimer: ReturnType<typeof setTimeout> | null = null
  private tickTimer: ReturnType<typeof setInterval> | null = null
  private stopFilterWatch: WatchStopHandle | null = null

  constructor(
    serviceId: string,
    shortCutService: KeyShortcutService,
    options: MonitoringServiceOptions<T> = {}
  ) {
    super(serviceId, shortCutService)
    const { pollIntervalMs = POLL_INTERVAL_MS, quickFilters = [], columns = [] } = options

    this.filters = new FilterStore(quickFilters, this.searchQuery)
    const bridge = useColumnFilterBridge(columns, this.filters)
    this.tableColumnFilters = bridge.tableColumnFilters
    this.onColumnFiltersUpdate = bridge.onColumnFiltersUpdate
    this.stopFilterWatch = watch(this.filters.filterNode, (node) => {
      this.updateFilters(node)
    })

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
      void this.fetch('background')
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

  updateFilters(node: FilterNode | undefined): void {
    this.filterState.value = node
    void this.fetch()
  }

  /**
   * Activate a quick-filter: apply its preset filter and, if it declares one,
   * its search query.
   */
  activateQuickFilter(quickFilter: QuickFilter): void {
    if (quickFilter.searchQuery !== undefined) {
      this.searchQuery.value = quickFilter.searchQuery
    }
    this.filters.activateQuickFilter(quickFilter)
    // Refresh explicitly: a quick filter may only change the search query, leaving the
    // filter node unchanged so the filterNode watcher would not fire.
    this.updateFilters(quickFilter.filter)
  }

  deactivateQuickFilter(quickFilter: QuickFilter): void {
    this.filters.deactivateQuickFilter(quickFilter)
  }

  clearAllFilters(): void {
    this.filters.clearAllFilters()
  }

  stopPolling(): void {
    if (this.stopFilterWatch !== null) {
      this.stopFilterWatch()
      this.stopFilterWatch = null
    }
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

  private async fetch(kind: FetchKind = 'foreground'): Promise<void> {
    if (this.fetchState.value !== 'idle') {
      return
    }
    this.secondsRemaining.value = this.pollIntervalSeconds
    this.fetchState.value = kind
    try {
      const response = await this.fetchBatch()
      this.items.value = response.items
      this.total.value = response.meta.total
    } catch (error: unknown) {
      console.error('MonitoringService: fetchBatch failed', error)
    } finally {
      this.fetchState.value = 'idle'
      this.hasLoaded.value = true
    }
  }
}
