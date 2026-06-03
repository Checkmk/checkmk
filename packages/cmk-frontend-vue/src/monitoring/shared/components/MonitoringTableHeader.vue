<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import { type ColumnDef, FlexRender, type HeaderGroup } from '@tanstack/vue-table'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-vue-next'
import type { CSSProperties } from 'vue'

defineProps<{
  headerGroups: HeaderGroup<T>[]
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

function columnStyle(columnDef: ColumnDef<T>): CSSProperties {
  const style: CSSProperties = {}
  if (columnDef.size !== undefined) {
    style.width = `${columnDef.size}px`
  }
  if (columnDef.minSize !== undefined) {
    style.minWidth = `${columnDef.minSize}px`
  }
  if (columnDef.maxSize !== undefined) {
    style.maxWidth = `${columnDef.maxSize}px`
  }
  return style
}
</script>

<template>
  <thead>
    <tr v-for="headerGroup in headerGroups" :key="headerGroup.id">
      <th
        v-for="header in headerGroup.headers"
        :key="header.id"
        :colspan="header.colSpan"
        :class="[
          'monitoring-table-header__header-cell',
          {
            'monitoring-table-header__header-cell--sortable': header.column.getCanSort()
          }
        ]"
        :style="columnStyle(header.column.columnDef)"
        :aria-sort="ariaSortFor(header.column.getIsSorted())"
      >
        <button
          v-if="!header.isPlaceholder && header.column.getCanSort()"
          type="button"
          class="monitoring-table-header__header-button"
          :title="header.column.columnDef.header?.toString()"
          @click="header.column.getToggleSortingHandler()?.($event)"
        >
          <ChevronUp
            v-if="header.column.getIsSorted() === 'asc'"
            class="monitoring-table-header__sort-icon"
            :size="14"
            aria-hidden="true"
          />
          <ChevronDown
            v-else-if="header.column.getIsSorted() === 'desc'"
            class="monitoring-table-header__sort-icon"
            :size="14"
            aria-hidden="true"
          />
          <ChevronsUpDown
            v-else
            class="monitoring-table-header__sort-icon monitoring-table-header__sort-icon--inactive"
            :size="14"
            aria-hidden="true"
          />
          <span class="monitoring-table-header__label">
            <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
          </span>
        </button>
        <span
          v-else-if="!header.isPlaceholder"
          class="monitoring-table-header__label"
          :title="header.column.columnDef.header?.toString()"
        >
          <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
        </span>
      </th>
    </tr>
  </thead>
</template>

<style scoped>
.monitoring-table-header__header-cell {
  vertical-align: middle;
  height: 24px;
  font-weight: var(--font-weight-bold);
  background: var(--ux-theme-2);
  white-space: nowrap;
  text-align: left;
}

.monitoring-table-header__header-button {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  max-width: 100%;
  height: 100%;
  background: transparent;
  border: none;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
  border-radius: 0;
  padding: var(--dimension-2) var(--dimension-4);

  &:hover {
    background-color: var(--ux-theme-3);
  }
}

.monitoring-table-header__label {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.monitoring-table-header__header-button:focus-visible {
  outline: 1px solid var(--success);
  outline-offset: 2px;
}

.monitoring-table-header__sort-icon {
  flex-shrink: 0;
}

.monitoring-table-header__sort-icon--inactive {
  opacity: 0.4;
}
</style>
