<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import {
  type ColumnDef,
  type Row,
  type RowSelectionState,
  getCoreRowModel,
  useVueTable
} from '@tanstack/vue-table'
import useDragging from 'cmk-ui-library/lib/useDragging'
import { type ComponentPublicInstance, computed, provide, ref } from 'vue'

import {
  COLUMN_LAYOUT_KEY,
  type ColumnLayoutInfo,
  ROW_DRAG_KEY,
  TABLE_BORDER_SPACING_PX,
  resolveUpdater
} from './MonitoringTableContext'
import MonitoringTableHeader from './MonitoringTableHeader.vue'

const borderSpacing = TABLE_BORDER_SPACING_PX

const props = defineProps<{
  /**
   * Replace immutably (assign a new array) when rows are edited, added,
   * removed, or reordered — TanStack memoizes its row model on the array
   * identity, so in-place mutation leaves `tableRow` slot props stale.
   */
  rows: T[]
  columns: ColumnDef<T>[]
  getRowKey: (row: T, index: number) => string | number
  rowHeight?: string
  /**
   * Expanded state per row key. Each expanded row renders the `#expansion` slot beneath it;
   * the slot must supply its own `<tr>` element(s).
   */
  expandedRows?: Record<string, boolean>
  getRowVariant?: (row: T, index: number) => 'error' | null
}>()

const emit = defineEmits<{
  (event: 'reorder', fromIndex: number, toIndex: number): void
}>()

const rowSelection = defineModel<RowSelectionState>('rowSelection', { default: () => ({}) })

const table = useVueTable({
  get data() {
    return props.rows
  },
  get columns() {
    return props.columns
  },
  state: {
    get rowSelection() {
      return rowSelection.value
    }
  },
  enableRowSelection: true,
  enableSorting: false,
  enableColumnFilters: false,
  getRowId: (row: T, index: number) => String(props.getRowKey(row, index)),
  onRowSelectionChange: (updater) => {
    rowSelection.value = resolveUpdater(updater, rowSelection.value)
  },
  getCoreRowModel: getCoreRowModel()
})

const leafColumns = computed(() => table.getAllLeafColumns())

const columnInfos = computed<Map<string, ColumnLayoutInfo>>(() => {
  const infos = new Map<string, ColumnLayoutInfo>()
  for (const column of leafColumns.value) {
    infos.set(column.id, {
      width: null,
      pinnedLeft: null,
      pinnedRight: null,
      isLastPinned: false,
      isFirstPinnedRight: false,
      justify: column.columnDef.meta?.justify ?? 'left'
    })
  }
  return infos
})
provide(COLUMN_LAYOUT_KEY, columnInfos)

const effectiveRowHeight = computed(() => props.rowHeight ?? 'auto')

function tableRowAt(index: number): Row<T> {
  return table.getRowModel().rows[index]!
}

// Each data row and its expansion live in their own <tbody> group
const ROW_GROUP_SELECTOR = 'tbody.monitoring-editable-table__row-group'
const tableRef = ref<HTMLTableElement | null>(null)
const { dragStart, dragEnd, dragging } = useDragging(tableRef, {
  itemSelector: ROW_GROUP_SELECTOR
})
const draggedRowIndex = ref<number | null>(null)
const isDraggingRow = computed(() => draggedRowIndex.value !== null)

provide(ROW_DRAG_KEY, {
  dragStart: (event: DragEvent) => {
    draggedRowIndex.value = dragStart(event)
  },
  drag: (event: DragEvent) => {
    const result = dragging(event)
    if (result !== null) {
      emit('reorder', result.draggedIndex, result.targetIndex)
      draggedRowIndex.value = result.targetIndex
    }
  },
  dragEnd: (event: DragEvent) => {
    draggedRowIndex.value = null
    dragEnd(event)
  }
})

function isRowExpanded(row: T, index: number): boolean {
  return props.expandedRows?.[String(props.getRowKey(row, index))] === true
}

const rowGroups = new Map<string, HTMLElement>()

function registerRowGroup(key: string, element: Element | ComponentPublicInstance | null): void {
  if (element instanceof HTMLElement) {
    rowGroups.set(key, element)
  } else {
    rowGroups.delete(key)
  }
}

defineExpose({
  /** Scroll the row with this key into view, together with its expansion. */
  scrollToRow: (key: string | number): void => {
    rowGroups.get(String(key))?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
})
</script>

<template>
  <div class="monitoring-editable-table">
    <table ref="tableRef" class="monitoring-editable-table__table">
      <colgroup>
        <col
          v-for="column in leafColumns"
          :key="column.id"
          :style="column.columnDef.meta?.stretch ? { width: '100%' } : {}"
        />
      </colgroup>
      <MonitoringTableHeader :header-groups="table.getHeaderGroups()" />
      <tbody v-if="rows.length === 0">
        <tr class="monitoring-editable-table__empty-row">
          <td :colspan="leafColumns.length">
            <slot name="empty-state" />
          </td>
        </tr>
      </tbody>
      <tbody
        v-for="(row, index) in rows"
        :key="getRowKey(row, index)"
        :ref="(element) => registerRowGroup(String(getRowKey(row, index)), element)"
        class="monitoring-editable-table__row-group"
        :class="{ 'monitoring-editable-table__row-group--dragging': draggedRowIndex === index }"
      >
        <tr
          class="monitoring-editable-table__row"
          :class="{
            'monitoring-editable-table__row--alt': index % 2 === 1,
            'monitoring-editable-table__row--no-hover': isDraggingRow,
            'monitoring-editable-table__row--error': getRowVariant?.(row, index) === 'error'
          }"
        >
          <slot name="row" :row="row" :table-row="tableRowAt(index)" :index="index" />
        </tr>
        <template v-if="isRowExpanded(row, index)">
          <slot name="expansion" :row="row" :table-row="tableRowAt(index)" :index="index" />
        </template>
      </tbody>
      <tfoot v-if="$slots.footer">
        <tr class="monitoring-editable-table__footer-row">
          <slot name="footer" />
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<style scoped>
.monitoring-editable-table {
  width: 100%;

  --monitoring-editable-table-row-error-bg: var(--color-dark-red-20);
}

body[data-theme='modern-dark'] .monitoring-editable-table {
  --monitoring-editable-table-row-error-bg: var(--color-dark-red-100);
}

.monitoring-editable-table__table {
  width: 100%;
  table-layout: auto;
  border-collapse: separate;
  border-spacing: v-bind(borderSpacing);
  background: var(--ux-theme-4);
}

.monitoring-editable-table__row {
  height: v-bind(effectiveRowHeight);
  background: var(--ux-theme-4);
}

.monitoring-editable-table__row--alt {
  background: var(--ux-theme-3);
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.monitoring-editable-table__row:not(
    .monitoring-editable-table__row--no-hover,
    .monitoring-editable-table__row--error
  ):hover,
.monitoring-editable-table__row:not(
    .monitoring-editable-table__row--no-hover,
    .monitoring-editable-table__row--error
  ):hover
  :deep(td) {
  background-color: var(--color-light-blue-0);
}

body[data-theme='modern-dark']
  .monitoring-editable-table__row:not(
    .monitoring-editable-table__row--no-hover,
    .monitoring-editable-table__row--error
  ):hover,
body[data-theme='modern-dark']
  .monitoring-editable-table__row:not(
    .monitoring-editable-table__row--no-hover,
    .monitoring-editable-table__row--error
  ):hover
  :deep(td) {
  background-color: var(--color-dark-blue-90);
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.monitoring-editable-table__row--error,
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-editable-table__row--error :deep(td) {
  background-color: var(--monitoring-editable-table-row-error-bg);
}

.monitoring-editable-table__row-group--dragging {
  box-shadow: 0 2px 10px 0 rgb(0 0 0 / 40%);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-editable-table__row-group--dragging :deep(td) {
  background-color: var(--color-light-blue-0);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
body[data-theme='modern-dark'] .monitoring-editable-table__row-group--dragging :deep(td) {
  background-color: var(--color-dark-blue-90);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-editable-table__footer-row :deep(td) {
  position: sticky;
  bottom: v-bind(borderSpacing);
  z-index: 2;
  background: var(--ux-theme-2);
  box-shadow: 0 0 0 1px var(--ux-theme-4);
}
</style>
