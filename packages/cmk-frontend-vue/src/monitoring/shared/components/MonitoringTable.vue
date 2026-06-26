<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import {
  type ColumnDef,
  type ColumnFiltersState,
  type ColumnPinningState,
  type Row,
  type RowSelectionState,
  type Updater,
  getCoreRowModel,
  useVueTable
} from '@tanstack/vue-table'
import { useVirtualizer } from '@tanstack/vue-virtual'
import {
  type ComponentPublicInstance,
  computed,
  inject,
  onBeforeUnmount,
  provide,
  ref,
  watch
} from 'vue'

import TableSkeleton from '@/loading-transition/TableSkeleton.vue'
import type { FetchState } from '@/monitoring/shared/services/MonitoringService'

import {
  COLUMN_LAYOUT_KEY,
  type ColumnJustify,
  type ColumnLayoutInfo,
  MONITORING_SERVICE,
  TABLE_BORDER_SPACING,
  TABLE_BORDER_SPACING_PX
} from './MonitoringTableContext'
import MonitoringTableHeader from './MonitoringTableHeader.vue'

const DEFAULT_COLUMN_MIN_SIZE = 20
const DEFAULT_COLUMN_MAX_SIZE = Number.POSITIVE_INFINITY
const borderSpacing = TABLE_BORDER_SPACING_PX

const props = defineProps<{
  rows: T[]
  /**
   * The kind of fetch in flight: `'foreground'` (initial load or
   * search/filter/sort) shows the skeleton; `'background'` (refresh-timer poll)
   * refreshes silently; `'idle'` when nothing is in flight.
   */
  fetchState: FetchState
  hasLoaded?: boolean
  columns: ColumnDef<T>[]
  filterState: ColumnFiltersState
  getRowKey?: (row: T, index: number) => string | number
  columnPinning?: ColumnPinningState
}>()

const emit = defineEmits<{
  (event: 'update:filterState', value: ColumnFiltersState): void
}>()

const monitoringService = inject(MONITORING_SERVICE)
const showSkeleton = computed(() => !props.hasLoaded || props.fetchState === 'foreground')
const showEmptyState = computed(() => props.hasLoaded && props.rows.length === 0)

function resolveUpdater<S>(updater: Updater<S>, current: S): S {
  return typeof updater === 'function' ? (updater as (old: S) => S)(current) : updater
}

const rowSelection = ref<RowSelectionState>({})

const table = useVueTable({
  // Server-side sort/filter — we bypass getRowModel() and slot rows directly.
  get data() {
    return props.rows
  },
  get columns() {
    return props.columns
  },
  state: {
    get sorting() {
      return monitoringService?.sortState.value ?? []
    },
    get columnFilters() {
      return props.filterState
    },
    get columnPinning() {
      return props.columnPinning ?? {}
    },
    get rowSelection() {
      return rowSelection.value
    }
  },
  enableColumnPinning: true,
  enableRowSelection: true,
  manualSorting: true,
  manualFiltering: true,
  // Filter values are opaque ColumnFilterNode objects resolved server-side, so
  // the fn is never run. It is set explicitly only to stop TanStack from
  // auto-detecting a per-column fn: a numeric column would otherwise get
  // `inNumberRange`, whose autoRemove discards our node objects (no [0]/[1]),
  // silently dropping numeric filters the moment they are applied.
  defaultColumn: {
    filterFn: () => true
  },
  // Key selection by the stable row key so it survives server-side reordering.
  ...(props.getRowKey
    ? { getRowId: (row: T, index: number) => String(props.getRowKey!(row, index)) }
    : {}),
  onSortingChange: (updater) => {
    monitoringService?.updateSort(resolveUpdater(updater, monitoringService.sortState.value))
  },
  onColumnFiltersChange: (updater) => {
    emit('update:filterState', resolveUpdater(updater, props.filterState))
  },
  onRowSelectionChange: (updater) => {
    rowSelection.value = resolveUpdater(updater, rowSelection.value)
  },
  getCoreRowModel: getCoreRowModel()
})

// --- Column pinning ------------------------------------------------------
const pinningEnabled = computed(() => (props.columnPinning?.left?.length ?? 0) > 0)

const wrapperRef = ref<HTMLElement | null>(null)
const containerWidth = ref<number | null>(null)
const headerHeight = ref(0)
let observer: ResizeObserver | null = null

watch(wrapperRef, (el) => {
  observer?.disconnect()
  observer = null
  if (el && typeof ResizeObserver !== 'undefined') {
    const thead = el.querySelector('thead')
    const measure = (width: number): void => {
      containerWidth.value = width
      if (thead) {
        headerHeight.value = thead.getBoundingClientRect().height
      }
    }
    observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) {
        measure(entry.contentRect.width)
      }
    })
    measure(el.getBoundingClientRect().width)
    observer.observe(el)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})

interface ColumnMetric {
  id: string
  min: number
  max: number
  isLeftPinned: boolean
  justify: ColumnJustify
}

const columnMetrics = computed<ColumnMetric[]>(() =>
  table.getAllLeafColumns().map((column) => ({
    id: column.id,
    min: column.columnDef.minSize ?? DEFAULT_COLUMN_MIN_SIZE,
    max: column.columnDef.maxSize ?? DEFAULT_COLUMN_MAX_SIZE,
    isLeftPinned: column.getIsPinned() === 'left',
    justify: column.columnDef.meta?.justify ?? 'left'
  }))
)

const totalMinWidth = computed(() =>
  columnMetrics.value.reduce((sum, metric) => sum + metric.min, 0)
)

const borderSpacingTotal = computed(() => (columnMetrics.value.length + 1) * TABLE_BORDER_SPACING)

function distributeWidths(available: number, metrics: ColumnMetric[]): number[] {
  const columns = metrics.map((metric) => ({ width: metric.min, max: metric.max }))
  const totalMin = metrics.reduce((sum, metric) => sum + metric.min, 0)
  if (!Number.isFinite(available) || available <= totalMin) {
    return columns.map((column) => column.width)
  }
  const totalMax = metrics.reduce((sum, metric) => sum + metric.max, 0)
  const target = Math.min(available, totalMax)
  let remaining = target - totalMin
  let growable = columns.filter((column) => column.width < column.max)
  while (remaining > 0.5 && growable.length > 0) {
    const share = remaining / growable.length
    let cappedAny = false
    for (const column of growable) {
      const grow = Math.min(share, column.max - column.width)
      column.width += grow
      remaining -= grow
      if (column.width >= column.max) {
        cappedAny = true
      }
    }
    growable = growable.filter((column) => column.width < column.max)
    if (!cappedAny) {
      break
    }
  }

  const rounded = columns.map((column) => ({
    value: Math.floor(column.width),
    max: column.max,
    frac: column.width - Math.floor(column.width)
  }))
  let leftover = Math.floor(target) - rounded.reduce((sum, column) => sum + column.value, 0)
  for (const column of [...rounded].sort((a, b) => b.frac - a.frac)) {
    if (leftover <= 0) {
      break
    }
    if (column.value < column.max) {
      column.value += 1
      leftover -= 1
    }
  }
  return rounded.map((column) => column.value)
}

const pinningActive = computed(
  () =>
    pinningEnabled.value &&
    containerWidth.value !== null &&
    containerWidth.value - borderSpacingTotal.value < totalMinWidth.value
)

interface ColumnLayout {
  id: string
  index: number
  width: number
  isPinned: boolean
  left: number
  justify: ColumnJustify
}

const columnLayout = computed<ColumnLayout[]>(() => {
  const metrics = columnMetrics.value
  // Unmeasured (null) → treat as unconstrained so columns size to their min.
  const available =
    containerWidth.value === null
      ? Number.POSITIVE_INFINITY
      : containerWidth.value - borderSpacingTotal.value
  const widths = distributeWidths(available, metrics)
  let pinnedOffset = TABLE_BORDER_SPACING
  return metrics.map((metric, index) => {
    const width = widths[index] ?? metric.min
    const isPinned = pinningActive.value && metric.isLeftPinned
    const entry: ColumnLayout = {
      id: metric.id,
      index,
      width,
      isPinned,
      left: pinnedOffset,
      justify: metric.justify
    }
    if (isPinned) {
      pinnedOffset += width + TABLE_BORDER_SPACING
    }
    return entry
  })
})

const lastPinnedIndex = computed(() =>
  columnLayout.value.reduce((last, entry) => (entry.isPinned ? entry.index : last), -1)
)

const totalWidth = computed(() => columnLayout.value.reduce((sum, entry) => sum + entry.width, 0))

const tableWidth = computed(() => (pinningEnabled.value ? `${totalWidth.value}px` : '100%'))

const columnInfos = computed<Map<string, ColumnLayoutInfo>>(() => {
  const infos = new Map<string, ColumnLayoutInfo>()
  for (const entry of columnLayout.value) {
    infos.set(entry.id, {
      width: containerWidth.value === null ? null : entry.width,
      pinnedLeft: entry.isPinned ? entry.left : null,
      isLastPinned: entry.index === lastPinnedIndex.value,
      justify: entry.justify
    })
  }
  return infos
})
provide(COLUMN_LAYOUT_KEY, columnInfos)

const leafColumnCount = computed(() => columnMetrics.value.length)

function rowKeyOf(index: number): string | number {
  return props.getRowKey ? props.getRowKey(props.rows[index]!, index) : index
}

const rowVirtualizer = useVirtualizer(
  computed(() => ({
    count: props.rows.length,
    getScrollElement: () => wrapperRef.value,
    estimateSize: () => 33,
    overscan: 12,
    scrollMargin: headerHeight.value,
    getItemKey: rowKeyOf
  }))
)

const virtualRows = computed(() => rowVirtualizer.value.getVirtualItems())
const totalSize = computed(() => rowVirtualizer.value.getTotalSize())

const paddingTop = computed(() => {
  const first = virtualRows.value[0]
  return first ? Math.max(0, first.start - headerHeight.value) : 0
})
const paddingBottom = computed(() => {
  const last = virtualRows.value[virtualRows.value.length - 1]
  return last ? Math.max(0, totalSize.value - last.end + headerHeight.value) : 0
})

function measureRowElement(el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLElement) {
    rowVirtualizer.value.measureElement(el)
  }
}

function rowAt(index: number): T {
  return props.rows[index]!
}

// getCoreRowModel keeps rows in data order (manual sort/filter), so the row
// model index lines up with the virtualized data index.
function tableRowAt(index: number): Row<T> {
  return table.getRowModel().rows[index]!
}
</script>

<template>
  <div ref="wrapperRef" class="monitoring-table" :aria-busy="fetchState !== 'idle'">
    <TableSkeleton v-if="showSkeleton"></TableSkeleton>
    <table v-else class="monitoring-table__table">
      <colgroup v-if="pinningEnabled">
        <col v-for="entry in columnLayout" :key="entry.id" :style="{ width: `${entry.width}px` }" />
      </colgroup>
      <MonitoringTableHeader :header-groups="table.getHeaderGroups()" :disabled="showEmptyState" />
      <tbody>
        <tr v-if="showEmptyState" class="monitoring-table__row">
          <td :colspan="columnLayout.length" class="monitoring-table__empty-cell">
            <slot name="empty-state" />
          </td>
        </tr>
        <template v-else>
          <tr v-if="paddingTop > 0" class="monitoring-table__spacer" aria-hidden="true">
            <td :colspan="leafColumnCount" :style="{ height: `${paddingTop}px` }"></td>
          </tr>
          <tr
            v-for="virtualRow in virtualRows"
            :key="rowKeyOf(virtualRow.index)"
            :ref="measureRowElement"
            :data-index="virtualRow.index"
            class="monitoring-table__row"
            :class="{ 'monitoring-table__row--alt': virtualRow.index % 2 === 1 }"
          >
            <slot
              name="row"
              :row="rowAt(virtualRow.index)"
              :table-row="tableRowAt(virtualRow.index)"
              :index="virtualRow.index"
            />
          </tr>
          <tr v-if="paddingBottom > 0" class="monitoring-table__spacer" aria-hidden="true">
            <td :colspan="leafColumnCount" :style="{ height: `${paddingBottom}px` }"></td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.monitoring-table {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.monitoring-table__table {
  width: v-bind(tableWidth);
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: v-bind(borderSpacing);
  background: var(--ux-theme-4);
}

.monitoring-table__row {
  background: var(--ux-theme-4);
}

.monitoring-table__row--alt {
  background: var(--ux-theme-3);
}

.monitoring-table__row:hover,
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-table__row:hover :deep(td) {
  background-color: var(--color-dark-blue-90);
}

body[data-theme='facelift'] .monitoring-table__row:hover,
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
body[data-theme='facelift'] .monitoring-table__row:hover :deep(td) {
  background-color: var(--color-light-blue-0);
}

.monitoring-table__spacer {
  background: transparent;
}

.monitoring-table__spacer td {
  padding: 0;
  border: 0;
}
</style>
