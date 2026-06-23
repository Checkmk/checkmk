<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import {
  type Column,
  type ColumnDef,
  FlexRender,
  type HeaderGroup,
  type Table
} from '@tanstack/vue-table'
import { type CSSProperties, inject } from 'vue'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import { COLUMN_LAYOUT_KEY } from './MonitoringTableContext'
import FilterDropdown from './filter/FilterDropdown.vue'

defineProps<{
  headerGroups: HeaderGroup<T>[]
  disabled?: boolean
}>()

function filterValue(column: Column<T, unknown>): ColumnFilterNode<FilterField> | undefined {
  return column.getFilterValue() as ColumnFilterNode<FilterField> | undefined
}

function setFilterValue(
  column: Column<T, unknown>,
  node: ColumnFilterNode<FilterField> | undefined
): void {
  column.setFilterValue(node)
}

function columnLabel(column: Column<T, unknown>): string {
  return column.columnDef.header?.toString() ?? column.id
}

function selectAllModel(table: Table<T>): boolean | 'indeterminate' {
  if (table.getIsAllRowsSelected()) {
    return true
  }
  return table.getIsSomeRowsSelected() ? 'indeterminate' : false
}

function setSelectAll(table: Table<T>, value: boolean | 'indeterminate'): void {
  table.toggleAllRowsSelected(value === true)
}

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

function contentStyle(columnDef: ColumnDef<T>): CSSProperties {
  const justify = columnDef.meta?.justify
  if (justify === 'right') {
    return { justifyContent: 'flex-end' }
  }
  if (justify === 'center') {
    return { justifyContent: 'center' }
  }
  return {}
}

function labelStyle(columnDef: ColumnDef<T>): CSSProperties {
  const justify = columnDef.meta?.justify
  return justify !== undefined ? { textAlign: justify } : {}
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
            'monitoring-table-header__header-cell--last-pinned': isLastPinned(header.column.id)
          }
        ]"
        :style="[columnStyle(header.column.columnDef), stickyStyle(header.column.id)]"
        :aria-sort="ariaSortFor(header.column.getIsSorted())"
      >
        <div class="monitoring-table-header__cell-content">
          <div
            v-if="!header.isPlaceholder && header.column.columnDef.meta?.selectColumn"
            class="monitoring-table-header__select"
            :style="contentStyle(header.column.columnDef)"
          >
            <CmkCheckbox
              :allow-indeterminate="true"
              :model-value="selectAllModel(header.getContext().table)"
              @update:model-value="setSelectAll(header.getContext().table, $event)"
            />
          </div>
          <button
            v-else-if="!header.isPlaceholder && header.column.getCanSort()"
            type="button"
            class="monitoring-table-header__header-button"
            :style="contentStyle(header.column.columnDef)"
            :title="header.column.columnDef.header?.toString()"
            :disabled="disabled"
            @click="header.column.getToggleSortingHandler()?.($event)"
          >
            <div class="monitoring-table-header__sort-icon-wrapper">
              <CmkMultitoneIcon
                name="chevron-up"
                class="monitoring-table-header__sort-icon"
                :class="{
                  'monitoring-table-header__sort-icon--active':
                    header.column.getIsSorted() === 'asc'
                }"
                primary-color="font"
                aria-hidden="true"
                size="xsmall"
              />
              <CmkMultitoneIcon
                name="chevron-down"
                class="monitoring-table-header__sort-icon"
                :class="{
                  'monitoring-table-header__sort-icon--active':
                    header.column.getIsSorted() === 'desc'
                }"
                primary-color="font"
                aria-hidden="true"
                size="xsmall"
              />
            </div>

            <span class="monitoring-table-header__label">
              <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
            </span>
          </button>
          <span
            v-else-if="!header.isPlaceholder"
            class="monitoring-table-header__label monitoring-table-header__label--standalone"
            :style="labelStyle(header.column.columnDef)"
            :title="header.column.columnDef.header?.toString()"
          >
            <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
          </span>
          <FilterDropdown
            v-if="
              !header.isPlaceholder &&
              header.column.getCanFilter() &&
              header.column.columnDef.meta?.filter
            "
            :definition="header.column.columnDef.meta.filter"
            :label="columnLabel(header.column)"
            :model-value="filterValue(header.column)"
            @update:model-value="setFilterValue(header.column, $event)"
          >
            <template #trigger="{ toggle, isOpen, isActive }">
              <button
                type="button"
                class="monitoring-table-header__filter-button"
                :class="{
                  'monitoring-table-header__filter-button--active': isActive || isOpen
                }"
                :title="`Filter ${header.column.columnDef.header?.toString() ?? ''}`.trim()"
                aria-haspopup="true"
                :aria-expanded="isOpen"
                @click="toggle"
              >
                <CmkMultitoneIcon
                  name="filter"
                  :primary-color="isActive ? { custom: 'var(--success)' } : 'font'"
                />
              </button>
            </template>
          </FilterDropdown>
        </div>
      </th>
    </tr>
  </thead>
</template>

<style scoped>
.monitoring-table-header__header-cell {
  position: sticky;
  top: 0;
  z-index: 2;
  vertical-align: middle;
  height: 24px;
  font-weight: var(--font-weight-bold);
  background: var(--ux-theme-1);
  white-space: nowrap;
  text-align: left;
}

.monitoring-table-header__header-cell--last-pinned::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 2px;
  pointer-events: none;
  background: var(--default-border-color);
}

.monitoring-table-header__cell-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.monitoring-table-header__select {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
}

.monitoring-table-header__header-button {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  max-width: 100%;
  height: 100%;
  flex: 1 1 auto;
  min-width: 0;
  background: transparent;
  border: none;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
  border-radius: 0;
  padding: var(--dimension-2) var(--dimension-4);

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }

  &:disabled {
    color: inherit;
    cursor: default;
    background: transparent;
    filter: none;
  }

  &:not(:disabled):hover {
    background-color: var(--ux-theme-3);
  }
}

.monitoring-table-header__label {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.monitoring-table-header__label--standalone {
  flex: 1 1 auto;
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

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }

  &:disabled {
    color: inherit;
    cursor: default;
    background: transparent;
    filter: none;
  }

  &:not(:disabled):hover {
    background-color: var(--ux-theme-3);
    opacity: 1;
  }
}

.monitoring-table-header__filter-button--active {
  opacity: 1;
}

.monitoring-table-header__sort-icon-wrapper {
  flex-shrink: 0;
  margin-right: var(--dimension-2);
}

.monitoring-table-header__sort-icon {
  opacity: 0.4;

  &:first-child {
    margin-top: calc(-1 * var(--dimension-2));
  }

  &:last-child {
    margin-top: calc(-1 * var(--dimension-3));
  }

  &.monitoring-table-header__sort-icon--active {
    opacity: 1;
  }
}
</style>
