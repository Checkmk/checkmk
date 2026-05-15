<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import {
  type ColumnDef,
  type ColumnFiltersState,
  FlexRender,
  type SortingState,
  type Updater,
  getCoreRowModel,
  useVueTable
} from '@tanstack/vue-table'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-vue-next'

const props = defineProps<{
  rows: T[]
  loading: boolean
  columns: ColumnDef<T>[]
  sortState: SortingState
  filterState: ColumnFiltersState
  getRowKey?: (row: T, index: number) => string | number
}>()

const emit = defineEmits<{
  (event: 'update:sortState', value: SortingState): void
  (event: 'update:filterState', value: ColumnFiltersState): void
}>()

type SortDirection = false | 'asc' | 'desc'

function ariaSortFor(direction: SortDirection): 'ascending' | 'descending' | 'none' {
  if (direction === 'asc') {
    return 'ascending'
  }
  if (direction === 'desc') {
    return 'descending'
  }
  return 'none'
}

function resolveUpdater<S>(updater: Updater<S>, current: S): S {
  return typeof updater === 'function' ? (updater as (old: S) => S)(current) : updater
}

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
      return props.sortState
    },
    get columnFilters() {
      return props.filterState
    }
  },
  manualSorting: true,
  manualFiltering: true,
  onSortingChange: (updater) => {
    emit('update:sortState', resolveUpdater(updater, props.sortState))
  },
  onColumnFiltersChange: (updater) => {
    emit('update:filterState', resolveUpdater(updater, props.filterState))
  },
  getCoreRowModel: getCoreRowModel()
})
</script>

<template>
  <div class="monitoring-table" :aria-busy="loading">
    <table class="monitoring-table__table">
      <thead>
        <tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
          <th
            v-for="header in headerGroup.headers"
            :key="header.id"
            :colspan="header.colSpan"
            :class="[
              'monitoring-table__header-cell',
              {
                'monitoring-table__header-cell--sortable': header.column.getCanSort()
              }
            ]"
            :aria-sort="ariaSortFor(header.column.getIsSorted())"
          >
            <button
              v-if="!header.isPlaceholder && header.column.getCanSort()"
              type="button"
              class="monitoring-table__header-button"
              @click="header.column.getToggleSortingHandler()?.($event)"
            >
              <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
              <ChevronUp
                v-if="header.column.getIsSorted() === 'asc'"
                class="monitoring-table__sort-icon"
                :size="14"
                aria-hidden="true"
              />
              <ChevronDown
                v-else-if="header.column.getIsSorted() === 'desc'"
                class="monitoring-table__sort-icon"
                :size="14"
                aria-hidden="true"
              />
              <ChevronsUpDown
                v-else
                class="monitoring-table__sort-icon monitoring-table__sort-icon--inactive"
                :size="14"
                aria-hidden="true"
              />
            </button>
            <FlexRender
              v-else-if="!header.isPlaceholder"
              :render="header.column.columnDef.header"
              :props="header.getContext()"
            />
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="getRowKey ? getRowKey(row, index) : index"
          class="monitoring-table__row"
        >
          <slot name="row" :row="row" :index="index" />
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.monitoring-table {
  width: 100%;
}

.monitoring-table__table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.monitoring-table__header-cell,
.monitoring-table__row :deep(td) {
  height: 24px;
  padding: 0 var(--dimension-4);
  text-align: left;
  vertical-align: middle;
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.monitoring-table__header-cell {
  font-weight: var(--font-weight-bold);
  background: var(--ux-theme-2);
  white-space: nowrap;
}

.monitoring-table__header-button {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  background: transparent;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.monitoring-table__header-button:focus-visible {
  outline: 1px solid var(--success);
  outline-offset: 2px;
}

.monitoring-table__sort-icon {
  flex-shrink: 0;
}

.monitoring-table__sort-icon--inactive {
  opacity: 0.4;
}

.monitoring-table__row:nth-child(even) {
  background: var(--ux-theme-3);
}

.monitoring-table__row:nth-child(odd) {
  background: var(--ux-theme-4);
}
</style>
