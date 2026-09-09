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
  type Header,
  type HeaderGroup,
  type Table
} from '@tanstack/vue-table'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type CSSProperties, computed, inject } from 'vue'

import type { FilterField } from '@/monitoring/shared/api/types'

import { COLUMN_LAYOUT_KEY, TABLE_BORDER_SPACING_PX } from './MonitoringTableContext'
import FilterDropdown from './filter/FilterDropdown.vue'
import type { ColumnFilterValue, SortDirection } from './filter/types'

const { _t } = usei18n()

const borderSpacing = TABLE_BORDER_SPACING_PX

// Named once: the hit area's tooltip and the checkbox's accessible name have to agree.
const selectAllLabel = computed(() => _t('Select all rows'))

defineProps<{
  headerGroups: HeaderGroup<T>[]
  disabled?: boolean
}>()

function filterValue(column: Column<T, unknown>): ColumnFilterValue<FilterField> | undefined {
  return column.getFilterValue() as ColumnFilterValue<FilterField> | undefined
}

function setFilterValue(
  column: Column<T, unknown>,
  node: ColumnFilterValue<FilterField> | undefined
): void {
  column.setFilterValue(node)
}

function setSort(column: Column<T, unknown>, direction: SortDirection): void {
  if (direction === false) {
    column.clearSorting()
    return
  }
  column.toggleSorting(direction === 'desc')
}

function columnLabel(column: Column<T, unknown>): string {
  return column.columnDef.header?.toString() ?? column.id
}

function filterButtonLabel(column: Column<T, unknown>, isActive: boolean): string {
  const columnTitle = (
    column.columnDef.meta?.headerTitle?.toString() ??
    column.columnDef.header?.toString() ??
    ''
  ).trim()
  return isActive
    ? _t('Filter %{column} (active)', { column: columnTitle })
    : _t('Filter %{column}', { column: columnTitle })
}

function helpLabel(column: Column<T, unknown>): string {
  return _t('Help for %{label}', { label: columnLabel(column) })
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

function toggleSelectAll(table: Table<T>): void {
  table.toggleAllRowsSelected(!table.getIsAllRowsSelected())
}

const columns = inject(COLUMN_LAYOUT_KEY, null)

function stickyStyle(columnId: string): CSSProperties {
  const info = columns?.value.get(columnId)
  const left = info?.pinnedLeft ?? null
  if (left !== null) {
    return { position: 'sticky', left: `${left}px`, zIndex: 3 }
  }
  const right = info?.pinnedRight ?? null
  if (right !== null) {
    return { position: 'sticky', right: `${right}px`, zIndex: 3 }
  }
  return {}
}

function isLastPinned(columnId: string): boolean {
  return columns?.value.get(columnId)?.isLastPinned ?? false
}

function isFirstPinnedRight(columnId: string): boolean {
  return columns?.value.get(columnId)?.isFirstPinnedRight ?? false
}

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

function hasFilterButton(header: Header<T, unknown>): boolean {
  return (
    !header.isPlaceholder &&
    header.column.getCanFilter() &&
    header.column.columnDef.meta?.filter !== undefined
  )
}

function reservesFilterSpace(header: Header<T, unknown>): boolean {
  return (
    !header.isPlaceholder && !header.column.columnDef.meta?.selectColumn && !hasFilterButton(header)
  )
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
            'monitoring-table-header__header-cell--last-pinned': isLastPinned(header.column.id),
            'monitoring-table-header__header-cell--first-pinned-right': isFirstPinnedRight(
              header.column.id
            )
          }
        ]"
        :style="[columnStyle(header.column.columnDef), stickyStyle(header.column.id)]"
        :aria-sort="ariaSortFor(header.column.getIsSorted())"
      >
        <div
          class="monitoring-table-header__cell-content"
          :class="{
            'monitoring-table-header__cell-content--reserve-filter': reservesFilterSpace(header)
          }"
        >
          <div
            v-if="!header.isPlaceholder && header.column.columnDef.meta?.selectColumn"
            class="monitoring-table-header__select"
            :style="contentStyle(header.column.columnDef)"
            :title="selectAllLabel"
            @click="toggleSelectAll(header.getContext().table)"
          >
            <CmkCheckbox
              :allow-indeterminate="true"
              :aria-label="selectAllLabel"
              :model-value="selectAllModel(header.getContext().table)"
              @update:model-value="setSelectAll(header.getContext().table, $event)"
              @click.stop
            />
          </div>
          <button
            v-else-if="!header.isPlaceholder && header.column.getCanSort()"
            type="button"
            class="monitoring-table-header__header-button"
            :style="contentStyle(header.column.columnDef)"
            :title="
              header.column.columnDef.meta?.headerTitle?.toString() ??
              header.column.columnDef.header?.toString()
            "
            :disabled="disabled"
            @click="header.column.getToggleSortingHandler()?.($event)"
          >
            <span class="monitoring-table-header__label">
              <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
            </span>

            <CmkMultitoneIcon
              v-if="header.column.getIsSorted() !== false"
              name="dashlet-resize"
              class="monitoring-table-header__sort-icon"
              :rotate="header.column.getIsSorted() === 'asc' ? 180 : 0"
              primary-color="font"
              aria-hidden="true"
              size="xsmall"
            />
          </button>
          <span
            v-else-if="!header.isPlaceholder && header.column.columnDef.meta?.headerHelp"
            class="monitoring-table-header__label-group monitoring-table-header__label-group--standalone"
            :style="labelStyle(header.column.columnDef)"
          >
            <span class="monitoring-table-header__label">
              <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
            </span>
            <CmkHelpText
              :help="header.column.columnDef.meta.headerHelp"
              :aria-label="helpLabel(header.column)"
            />
          </span>
          <span
            v-else-if="!header.isPlaceholder"
            class="monitoring-table-header__label monitoring-table-header__label--standalone"
            :style="labelStyle(header.column.columnDef)"
            :title="
              header.column.columnDef.meta?.headerTitle?.toString() ??
              header.column.columnDef.header?.toString()
            "
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
            anchor="th"
            :heading="_t('Filter')"
            :sortable="header.column.getCanSort()"
            :sort="header.column.getIsSorted()"
            :model-value="filterValue(header.column)"
            @update:sort="setSort(header.column, $event)"
            @update:model-value="setFilterValue(header.column, $event)"
          >
            <template #trigger="{ toggle, isOpen, isActive, panelId }">
              <button
                type="button"
                class="monitoring-table-header__filter-button"
                :class="{
                  'monitoring-table-header__filter-button--open': isOpen
                }"
                :title="filterButtonLabel(header.column, isActive)"
                :aria-label="filterButtonLabel(header.column, isActive)"
                :aria-expanded="isOpen"
                :aria-controls="panelId"
                @click="toggle"
              >
                <CmkMultitoneIcon
                  name="more-actions"
                  primary-color="font"
                  aria-hidden="true"
                  size="small"
                />
                <span
                  v-if="isActive"
                  class="monitoring-table-header__filter-dot"
                  aria-hidden="true"
                ></span>
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
  top: v-bind(borderSpacing);
  z-index: 2;
  vertical-align: middle;
  height: 24px;
  font-weight: var(--font-weight-bold);
  background: var(--ux-theme-1);
  box-shadow: 0 0 0 1px var(--ux-theme-4);
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

.monitoring-table-header__header-cell--first-pinned-right::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 2px;
  pointer-events: none;
  background: var(--default-border-color);
}

.monitoring-table-header__cell-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.monitoring-table-header__cell-content--reserve-filter {
  margin-right: var(--dimension-4);
}

.monitoring-table-header__select {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  height: 100%;
  cursor: pointer;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.monitoring-table-header__select :deep(.cmk-checkbox__container) {
  pointer-events: none;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.monitoring-table-header__select:hover :deep(.cmk-checkbox__button) {
  background-color: var(--input-hover-bg-color);
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
  padding-left: var(--dimension-4);
}

.monitoring-table-header__label-group {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  min-width: 0;
}

.monitoring-table-header__label-group--standalone {
  flex: 1 1 auto;
  padding-left: var(--dimension-4);
}

.monitoring-table-header__filter-button {
  position: relative;
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

.monitoring-table-header__filter-button--open {
  background-color: var(--ux-theme-3);
}

.monitoring-table-header__filter-dot {
  position: absolute;
  top: var(--dimension-3);
  right: 0;
  width: var(--dimension-3);
  height: var(--dimension-3);
  border-radius: 50%;
  background: var(--success);
}

.monitoring-table-header__sort-icon {
  flex-shrink: 0;
}
</style>
