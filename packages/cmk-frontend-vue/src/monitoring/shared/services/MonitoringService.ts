/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState
} from '@tanstack/vue-table'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { ServiceBase } from 'cmk-ui-library/lib/service/base'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import {
  type ComputedRef,
  type Ref,
  type WatchStopHandle,
  computed,
  ref,
  shallowRef,
  watch
} from 'vue'

import type { FilterNode } from '@/monitoring/shared/api/types'
import { DEFAULT_BATCH_SIZE, POLL_INTERVAL_MS } from '@/monitoring/shared/constants'

import { FilterStore, type QuickFilter, type QuickFilterConfig } from './FilterStore'
import { useColumnFilterBridge } from './useColumnFilterBridge'

export interface PagedResponse<T> {
  items: T[]
  meta: {
    limit: number | null
    matched: number
    total: number
    /** Offset the returned items start at. Absent for listings that do not page. */
    offset?: number
    /** Highest offset the backend serves. Absent for listings that do not page. */
    maxOffset?: number
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
  limitTiers?: number[]
  mayRemoveLimit?: boolean
  /**
   * Browser-storage key the user's column selection is kept under, built with
   * {@link buildColumnStorageKey}. Omit to keep the selection in memory only.
   */
  columnStorageKey?: string
}

export interface ColumnStorageScope {
  /** The view the columns belong to, e.g. `'all-hosts'`. */
  view: string
  /** Site serving the view. */
  site: string
  /** Logged-in user. */
  userId: string
  /** Edition serving the view, e.g. `'community'`. */
  edition: string
}

/**
 * Key a view's column selection is stored under.
 */
export function buildColumnStorageKey({ view, site, userId, edition }: ColumnStorageScope): string {
  return `monitoring-${view}-columns-${site}-${userId}-${edition}`
}

export type RequestedLimit = number | null

export interface ToggleableColumn {
  id: string
  label: TranslatedString
}

export function columnId<T>(column: ColumnDef<T>): string | undefined {
  if (column.id !== undefined) {
    return column.id
  }
  if ('accessorKey' in column && column.accessorKey !== undefined) {
    return String(column.accessorKey)
  }
  return undefined
}

function columnLabel<T>(column: ColumnDef<T>, id: string): string {
  if (typeof column.header === 'string' && column.header !== '') {
    return column.header
  }
  return column.meta?.headerTitle?.toString() ?? id
}

function isToggleable<T>(column: ColumnDef<T>): boolean {
  return !column.meta?.selectColumn && column.enableHiding !== false
}

function buildToggleableColumns<T>(columns: ColumnDef<T>[]): ToggleableColumn[] {
  const result: ToggleableColumn[] = []
  for (const column of columns) {
    if (!isToggleable(column)) {
      continue
    }
    const id = columnId(column)
    if (id === undefined) {
      continue
    }
    result.push({ id, label: untranslated(columnLabel(column, id)) })
  }
  return result
}

function computeDefaultVisibility<T>(columns: ColumnDef<T>[]): VisibilityState {
  const visibility: VisibilityState = {}
  for (const column of columns) {
    if (column.meta?.hidden) {
      const id = columnId(column)
      if (id !== undefined) {
        visibility[id] = false
      }
    }
  }
  return visibility
}

/**
 * Rebuild a visibility state from what browser storage holds, keeping only
 * decisions that still mean something: an id that is no longer offered has been
 * renamed, removed or turned into a fixed column since it was stored, so its
 * stale entry must not decide anything. Columns the stored state says nothing
 * about fall back to their default.
 */
function sanitizeVisibility(
  stored: unknown,
  toggleable: ToggleableColumn[],
  defaults: VisibilityState
): VisibilityState {
  const visibility: VisibilityState = { ...defaults }
  if (stored === null || typeof stored !== 'object') {
    return visibility
  }
  const entries = stored as Record<string, unknown>
  for (const column of toggleable) {
    const value = entries[column.id]
    if (typeof value === 'boolean') {
      visibility[column.id] = value
    }
  }
  return visibility
}

export abstract class MonitoringService<T> extends ServiceBase {
  readonly items: Ref<T[]> = shallowRef<T[]>([])
  readonly matched: Ref<number> = ref(0)
  readonly total: Ref<number> = ref(0)

  readonly offeredLimits: RequestedLimit[]
  readonly requestedLimit: Ref<RequestedLimit>
  /**
   * Offset of the visible page into the matched rows. Stays 0 for listings that
   * are bounded by a limit instead of paged.
   */
  readonly offset: Ref<number> = ref(0)
  /** Highest offset the backend serves, or `null` while it has not said. */
  readonly maxOffset: Ref<number | null> = ref(null)
  /** The kind of fetch currently in flight, or `'idle'`. */
  readonly fetchState: Ref<FetchState> = ref('idle')
  readonly hasLoaded: Ref<boolean> = ref(false)
  readonly sortState: Ref<SortingState> = ref<SortingState>([])
  readonly searchQuery: Ref<string> = ref('')
  /** The `searchQuery` updates on every key stroke, but we will also want information on the
   *  committed (or sent) query, which only changes on submit. */
  readonly committedSearchQuery: Ref<string> = ref('')
  readonly filterState: Ref<FilterNode | undefined> = ref(undefined)

  readonly toggleableColumns: ToggleableColumn[]
  readonly columnVisibility: Ref<VisibilityState>
  readonly defaultColumnVisibility: VisibilityState

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

  /** 1-based position of the first visible row, or 0 when nothing matched. */
  readonly pageFirst: ComputedRef<number> = computed(() =>
    this.items.value.length === 0 ? 0 : this.offset.value + 1
  )
  /** 1-based position of the last visible row, or 0 when nothing matched. */
  readonly pageLast: ComputedRef<number> = computed(
    () => this.offset.value + this.items.value.length
  )
  readonly hasPreviousPage: ComputedRef<boolean> = computed(() => this.offset.value > 0)
  readonly hasNextPage: ComputedRef<boolean> = computed(() => {
    const next = this.offset.value + this.pageSize
    return (
      next < this.matched.value && (this.maxOffset.value === null || next <= this.maxOffset.value)
    )
  })

  /**
   * Rows per page. An unbounded listing has no page size of its own, so it
   * steps by however many rows came back - which keeps `nextPage()` honest even
   * though such a listing never offers paging in practice.
   */
  private get pageSize(): number {
    return this.requestedLimit.value ?? this.items.value.length
  }

  private initialFetchTimer: ReturnType<typeof setTimeout> | null = null
  private refreshTimer: ReturnType<typeof setTimeout> | null = null
  private tickTimer: ReturnType<typeof setInterval> | null = null
  private stopFilterWatch: WatchStopHandle | null = null
  private currentAbort: AbortController | null = null

  constructor(
    serviceId: string,
    shortCutService: KeyShortcutService,
    options: MonitoringServiceOptions<T> = {}
  ) {
    super(serviceId, shortCutService)
    const {
      pollIntervalMs = POLL_INTERVAL_MS,
      quickFilters = [],
      columns = [],
      limitTiers = [],
      mayRemoveLimit = false,
      columnStorageKey
    } = options

    this.toggleableColumns = buildToggleableColumns(columns)
    this.defaultColumnVisibility = computeDefaultVisibility(columns)
    const defaultVisibility = { ...this.defaultColumnVisibility }
    // usePersistentRef writes every later change back, so the selection outlives
    // the tab it was made in.
    this.columnVisibility =
      columnStorageKey === undefined
        ? ref(defaultVisibility)
        : usePersistentRef(columnStorageKey, defaultVisibility, (stored) =>
            sanitizeVisibility(stored, this.toggleableColumns, defaultVisibility)
          )

    const numericTiers: RequestedLimit[] = limitTiers.length
      ? [...limitTiers]
      : [DEFAULT_BATCH_SIZE]
    this.offeredLimits = mayRemoveLimit ? [...numericTiers, null] : numericTiers
    this.requestedLimit = ref(this.offeredLimits[0] ?? DEFAULT_BATCH_SIZE)

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

  protected abstract fetchBatch(signal: AbortSignal): Promise<PagedResponse<T>>

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
    this.offset.value = 0
    void this.fetch()
  }

  updateSearch(searchQuery: string): void {
    this.searchQuery.value = searchQuery
    this.offset.value = 0
    void this.fetch()
  }

  updateColumnVisibility(visibility: VisibilityState): void {
    // A view may narrow its request to the columns on show, in which case a
    // column that was hidden has no data behind it yet and revealing one has to
    // fetch. Hiding needs nothing: that data is already here, merely unused.
    const revealed = this.toggleableColumns.some(
      ({ id }) => this.columnVisibility.value[id] === false && visibility[id] !== false
    )
    this.columnVisibility.value = visibility
    if (revealed) {
      void this.fetch()
    }
  }

  resetColumnVisibility(): void {
    this.updateColumnVisibility({ ...this.defaultColumnVisibility })
  }

  updateFilters(node: FilterNode | undefined): void {
    this.filterState.value = node
    this.offset.value = 0
    void this.fetch()
  }

  /**
   * Jump to an offset into the matched rows. Narrowing or resizing invalidates
   * the current page, so search, sort, filter and limit changes reset it to 0.
   */
  setOffset(value: number): void {
    const next = Math.max(0, value)
    if (next === this.offset.value) {
      return
    }
    this.offset.value = next
    void this.fetch()
  }

  nextPage(): void {
    if (this.hasNextPage.value) {
      this.setOffset(this.offset.value + this.pageSize)
    }
  }

  previousPage(): void {
    if (this.hasPreviousPage.value) {
      this.setOffset(this.offset.value - this.pageSize)
    }
  }

  // Selecting "no limit" pauses the auto-refresh so an unbounded result set isn't re-fetched on
  // every tick; switching back to a bounded limit resumes it.
  setRequestedLimit(value: RequestedLimit): void {
    if (value === this.requestedLimit.value) {
      return
    }
    const wasUnlimited = this.requestedLimit.value === null
    this.requestedLimit.value = value
    this.offset.value = 0
    if (value === null) {
      this.manualPaused.value = true
    } else if (wasUnlimited) {
      this.manualPaused.value = false
    }
    void this.fetch()
  }

  refresh(delayMs = 0): void {
    if (this.refreshTimer !== null) {
      clearTimeout(this.refreshTimer)
      this.refreshTimer = null
    }
    if (delayMs <= 0) {
      void this.fetch('background')
      return
    }
    this.refreshTimer = setTimeout(() => {
      this.refreshTimer = null
      void this.fetch('background')
    }, delayMs)
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
    if (this.refreshTimer !== null) {
      clearTimeout(this.refreshTimer)
      this.refreshTimer = null
    }
    if (this.tickTimer !== null) {
      clearInterval(this.tickTimer)
      this.tickTimer = null
    }
    if (this.currentAbort !== null) {
      this.currentAbort.abort()
      this.currentAbort = null
    }
  }

  destruct(): void {
    this.stopPolling()
    this.disableShortCuts()
    this.removeCallbacks()
  }

  /**
   * Protected rather than private: a subclass with query dimensions of its own
   * (the flow explorer's visual-filter context, for one) needs to trigger the
   * same foreground refetch that a search or sort change does.
   */
  protected async fetch(kind: FetchKind = 'foreground'): Promise<void> {
    if (kind === 'background' && this.fetchState.value !== 'idle') {
      return
    }
    this.currentAbort?.abort()
    const abort = new AbortController()
    this.currentAbort = abort

    this.secondsRemaining.value = this.pollIntervalSeconds
    this.fetchState.value = kind
    const searchQueryForFetch = this.searchQuery.value
    try {
      const response = await this.fetchBatch(abort.signal)
      if (this.currentAbort !== abort) {
        return
      }
      this.items.value = response.items
      this.matched.value = response.meta.matched
      this.total.value = response.meta.total
      // A paging backend reports which page it actually served; trust it over the
      // requested offset, which it may have clamped.
      if (response.meta.offset !== undefined) {
        this.offset.value = response.meta.offset
      }
      if (response.meta.maxOffset !== undefined) {
        this.maxOffset.value = response.meta.maxOffset
      }
      this.committedSearchQuery.value = searchQueryForFetch
    } catch (error: unknown) {
      if (this.currentAbort !== abort) {
        return
      }
      console.error('MonitoringService: fetchBatch failed', error)
    } finally {
      if (this.currentAbort === abort) {
        this.currentAbort = null
        this.fetchState.value = 'idle'
        this.hasLoaded.value = true
      }
    }
  }
}
