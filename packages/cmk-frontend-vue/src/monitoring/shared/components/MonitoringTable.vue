<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type Updater,
  getCoreRowModel,
  useVueTable
} from '@tanstack/vue-table'

import MonitoringTableHeader from './MonitoringTableHeader.vue'

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
      <MonitoringTableHeader :header-groups="table.getHeaderGroups()" />
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
  table-layout: fixed;
  border-collapse: collapse;
  border-spacing: 0;
}

.monitoring-table__row:nth-child(even) {
  background: var(--ux-theme-3);
}

.monitoring-table__row:nth-child(odd) {
  background: var(--ux-theme-4);
}
</style>
