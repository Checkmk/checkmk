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
import type { FilterUrlState } from '@/monitoring/shared/filterState/types'
import {
  columnIdsFromVisibility,
  visibilityFromColumnIds
} from '@/monitoring/shared/tableState/reconcile'
import {
  type ToggleableColumn,
  buildOfferedLimits,
  buildToggleableColumns,
  computeDefaultVisibility
} from '@/monitoring/shared/tableState/schema'
import type { TableState, TableStateSchema } from '@/monitoring/shared/tableState/types'
import type { RequestedLimit } from '@/monitoring/shared/types'

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
   * The table's URL vocabulary, built by `buildTableStateSchema` from the same
   * `columns`/`limitTiers`/`mayRemoveLimit` also wired to `useUrlTableState`. When
   * given, it is the single source for the ids behind `toggleableColumns`,
   * `defaultColumnVisibility` and `offeredLimits` - `columns`/`limitTiers`/
   * `mayRemoveLimit` are then only consulted for labels and the column-filter
   * bridge. Omit for a listing with no URL persistence, which keeps deriving all
   * three straight from `columns`/`limitTiers`/`mayRemoveLimit`.
   */
  tableStateSchema?: TableStateSchema
  /**
   * Browser-storage key the user's column selection is kept under, built with
   * {@link buildColumnStorageKey}. Omit to keep the selection in memory only.
   */
  columnStorageKey?: string
  /**
   * A validated, already-reconciled table state to seed columns, sort and
   * limit from - typically decoded from the URL. Seeding columns this way
   * never writes to local storage; seeding the limit applies the same
   * unlimited-pauses-refresh coupling `setRequestedLimit` does.
   */
  initialState?: Partial<TableState>
  /**
   * A validated, already-reconciled filter/search state to seed from -
   * typically decoded from the URL. Kept separate from {@link initialState}:
   * this narrows the result set, table state never does.
   */
  initialFilterState?: Partial<FilterUrlState>
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
  /**
   * `searchQuery` updates on every key stroke; this only changes when a search is actually
   * submitted (Enter, a quick filter, or a reset). `fetchBatch` reads this, not `searchQuery`,
   * so a background poll firing mid-keystroke can never narrow the listing to unsubmitted text.
   */
  readonly appliedSearchQuery: Ref<string> = ref('')
  /** The applied query the most recently completed fetch actually used. */
  readonly committedSearchQuery: Ref<string> = ref('')
  readonly filterState: Ref<FilterNode | undefined> = ref(undefined)
  /** The table's row-narrowing state - filter plus applied search - for a URL sync to watch. */
  readonly filterUrlState: ComputedRef<FilterUrlState>

  readonly toggleableColumns: ToggleableColumn[]
  private readonly hideableColumnIds: string[]
  readonly columnVisibility: Ref<VisibilityState>
  readonly defaultColumnVisibility: VisibilityState
  /** The table's non-filter display state, for a URL sync to watch. */
  readonly tableState: ComputedRef<TableState>

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
      tableStateSchema,
      columnStorageKey,
      initialState,
      initialFilterState
    } = options

    if (tableStateSchema === undefined) {
      this.toggleableColumns = buildToggleableColumns(columns)
      this.hideableColumnIds = this.toggleableColumns.map(({ id }) => id)
      this.defaultColumnVisibility = computeDefaultVisibility(columns)
    } else {
      // `columns` still describes every column, so this only borrows its labels - not
      // its notion of what's hideable or hidden by default, which the schema now owns.
      // `untranslated(id)` is unreachable as long as `columns` is the same array
      // `tableStateSchema` was built from; it exists so a schema/columns mismatch
      // degrades to a raw id instead of crashing.
      const labelById = new Map(buildToggleableColumns(columns).map(({ id, label }) => [id, label]))
      this.hideableColumnIds = tableStateSchema.hideable
      this.toggleableColumns = this.hideableColumnIds.map((id) => ({
        id,
        label: labelById.get(id) ?? untranslated(id)
      }))
      this.defaultColumnVisibility = tableStateSchema.defaultVisibility
    }
    const defaultVisibility = { ...this.defaultColumnVisibility }
    const urlVisibility =
      initialState?.cols === undefined
        ? undefined
        : visibilityFromColumnIds(initialState.cols, this.hideableColumnIds)
    // usePersistentRef writes every later change back, so the selection outlives
    // the tab it was made in. Seeding through `parse` lets a URL's columns win
    // without persisting them - the user's own next change still writes through.
    this.columnVisibility =
      columnStorageKey === undefined
        ? ref(urlVisibility ?? defaultVisibility)
        : usePersistentRef(columnStorageKey, defaultVisibility, (stored) =>
            urlVisibility === undefined
              ? sanitizeVisibility(stored, this.toggleableColumns, defaultVisibility)
              : urlVisibility
          )

    this.offeredLimits =
      tableStateSchema?.offeredLimits ?? buildOfferedLimits(limitTiers, mayRemoveLimit)
    this.requestedLimit = ref(this.offeredLimits[0] ?? DEFAULT_BATCH_SIZE)
    if (initialState?.limit !== undefined) {
      this.applyLimit(initialState.limit)
    }

    if (initialState?.sort !== undefined) {
      this.sortState.value = initialState.sort
    }

    this.tableState = computed(() => ({
      cols: columnIdsFromVisibility(this.columnVisibility.value, this.hideableColumnIds),
      sort: this.sortState.value,
      limit: this.requestedLimit.value
    }))

    if (initialFilterState?.search !== undefined) {
      this.searchQuery.value = initialFilterState.search
      this.appliedSearchQuery.value = initialFilterState.search
    }

    this.filters = new FilterStore(quickFilters, this.searchQuery)
    // Seed before the filterNode watch below exists, so this never fires a spurious
    // updateFilters() fetch - the scheduled initial fetch already carries this filter.
    if (initialFilterState?.filter !== undefined) {
      this.filters.setQueryNode(initialFilterState.filter)
      this.filterState.value = initialFilterState.filter
    }
    this.filterUrlState = computed(() => ({
      filter: this.filterState.value,
      search: this.appliedSearchQuery.value
    }))

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
    this.appliedSearchQuery.value = searchQuery
    this.offset.value = 0
    void this.fetch()
  }

  /**
   * Hiding a shown column whose funnel filters the listing would leave that filter narrowing the
   * rows with nothing on screen pointing at it, so such a column is kept shown. A column that is
   * already hidden stays hidden, or a filter set elsewhere could never be got rid of.
   */
  withFilteredColumnsShown(visibility: VisibilityState): VisibilityState {
    const filtered = new Set(this.tableColumnFilters.value.map((filter) => filter.id))
    const guarded = { ...visibility }
    for (const { id } of this.toggleableColumns) {
      if (filtered.has(id) && this.columnVisibility.value[id] !== false) {
        guarded[id] = true
      }
    }
    return guarded
  }

  updateColumnVisibility(visibility: VisibilityState): void {
    const guarded = this.withFilteredColumnsShown(visibility)
    // A view may narrow its request to the columns on show, in which case a
    // column that was hidden has no data behind it yet and revealing one has to
    // fetch. Hiding needs nothing: that data is already here, merely unused.
    const revealed = this.toggleableColumns.some(
      ({ id }) => this.columnVisibility.value[id] === false && guarded[id] !== false
    )
    this.columnVisibility.value = guarded
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

  /**
   * Set {@link requestedLimit}, applying the "unlimited pauses auto-refresh,
   * a bounded value resumes it" coupling. Does not reset {@link offset} or
   * trigger a fetch - callers representing a user action do that themselves.
   */
  private applyLimit(value: RequestedLimit): void {
    const wasUnlimited = this.requestedLimit.value === null
    this.requestedLimit.value = value
    if (value === null) {
      this.manualPaused.value = true
    } else if (wasUnlimited) {
      this.manualPaused.value = false
    }
  }

  setRequestedLimit(value: RequestedLimit): void {
    if (value === this.requestedLimit.value) {
      return
    }
    this.applyLimit(value)
    this.offset.value = 0
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
      this.appliedSearchQuery.value = quickFilter.searchQuery
    }
    this.filters.activateQuickFilter(quickFilter)
    // Refresh explicitly: a quick filter may only change the search query, leaving the
    // filter node unchanged so the filterNode watcher would not fire.
    this.updateFilters(quickFilter.filter)
  }

  deactivateQuickFilter(quickFilter: QuickFilter): void {
    this.filters.deactivateQuickFilter(quickFilter)
  }

  /**
   * Clears the search box and what the next fetch will send with it. Does not
   * fetch: the caller owns when that happens, because a view resetting its
   * filters alongside this one only wants a single request.
   */
  clearSearch(): void {
    this.searchQuery.value = ''
    this.appliedSearchQuery.value = ''
  }

  clearAllFilters(): void {
    this.clearSearch()
    this.filters.clearAllFilters()
    this.updateFilters(undefined)
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
    const searchQueryForFetch = this.appliedSearchQuery.value
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
