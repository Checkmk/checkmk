<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import { type ColumnDef, FlexRender, type HeaderGroup } from '@tanstack/vue-table'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-vue-next'
import { type CSSProperties, inject } from 'vue'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import { COLUMN_LAYOUT_KEY } from './MonitoringTableContext'

defineProps<{
  headerGroups: HeaderGroup<T>[]
}>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

function stickyStyle(columnId: string): CSSProperties {
  const left = columns?.value.get(columnId)?.pinnedLeft ?? null
  return left !== null ? { position: 'sticky', left: `${left}px`, zIndex: 3 } : {}
}

function isLastPinned(columnId: string): boolean {
  return columns?.value.get(columnId)?.isLastPinned ?? false
}

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
  if (columnDef.meta?.justify !== undefined) {
    style.textAlign = columnDef.meta.justify
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
            'monitoring-table-header__header-cell--sortable': header.column.getCanSort(),
            'monitoring-table-header__header-cell--last-pinned': isLastPinned(header.column.id)
          }
        ]"
        :style="[columnStyle(header.column.columnDef), stickyStyle(header.column.id)]"
        :aria-sort="ariaSortFor(header.column.getIsSorted())"
      >
        <div class="monitoring-table-header__cell-content">
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
          <button
            v-if="!header.isPlaceholder && header.column.getCanFilter()"
            type="button"
            class="monitoring-table-header__filter-button"
            :class="{
              'monitoring-table-header__filter-button--active': header.column.getIsFiltered()
            }"
            :title="`Filter ${header.column.columnDef.header?.toString() ?? ''}`.trim()"
          >
            <CmkMultitoneIcon name="filter" primary-color="font" />
          </button>
        </div>
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
  position: sticky;
  top: 0;
  z-index: 2;
}

.monitoring-table-header__header-cell--last-pinned::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 8px;
  transform: translateX(100%);
  pointer-events: none;
  background: linear-gradient(to right, rgb(0 0 0 / 30%), rgb(0 0 0 / 0%));
}

.monitoring-table-header__cell-content {
  display: flex;
  align-items: center;
  height: 100%;
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

.monitoring-table-header__filter-button {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  height: 100%;
  padding: var(--dimension-2);
  background: transparent;
  border: none;
  margin: 0;
  color: inherit;
  cursor: pointer;
  border-radius: 0;
  opacity: 0.5;

  &:hover {
    background-color: var(--ux-theme-3);
    opacity: 1;
  }

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }
}

.monitoring-table-header__filter-button--active {
  opacity: 1;
}

.monitoring-table-header__sort-icon {
  flex-shrink: 0;
}

.monitoring-table-header__sort-icon--inactive {
  opacity: 0.4;
}
</style>
