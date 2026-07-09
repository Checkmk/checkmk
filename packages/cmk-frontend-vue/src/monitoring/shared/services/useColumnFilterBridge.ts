/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ColumnDef, type ColumnFiltersState } from '@tanstack/vue-table'
import { type ComputedRef, computed } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'
import { filterFields } from '@/monitoring/shared/components/filter/types'

import type { FilterStore } from './FilterStore'
import { getTopLevelConditions } from './filterNodeUtils'

function combine(
  conditions: ColumnFilterNode<FilterField>[]
): ColumnFilterNode<FilterField> | undefined {
  if (conditions.length === 0) {
    return undefined
  }
  if (conditions.length === 1) {
    return conditions[0]
  }
  return { type: 'and', children: conditions }
}

/**
 * Bridges a FilterStore (field-centric) with TanStack Table's column filter state
 * (column-ID-centric). Derives the table's displayed column filters from the store
 * and maps column filter change events back to store updates.
 *
 * Intended to be shared across monitoring apps that combine a FilterStore with a
 * MonitoringTable.
 */
export function useColumnFilterBridge<TData>(
  columns: ColumnDef<TData>[],
  filterStore: FilterStore
): {
  tableColumnFilters: ComputedRef<ColumnFiltersState>
  onColumnFiltersUpdate: (next: ColumnFiltersState) => void
} {
  const tableColumnFilters = computed<ColumnFiltersState>(() =>
    columns.flatMap((col) => {
      const filter = col.meta?.filter
      if (filter === undefined || !('accessorKey' in col)) {
        return []
      }
      const conditions = filterFields(filter)
        .map((field) => filterStore.getColumnFilter(field))
        .filter((condition): condition is ColumnFilterNode<FilterField> => condition !== undefined)
      const value = combine(conditions)
      return value !== undefined ? [{ id: col.accessorKey as string, value }] : []
    })
  )

  function onColumnFiltersUpdate(next: ColumnFiltersState): void {
    const map = new Map<FilterField, ColumnFilterNode<FilterField> | undefined>()
    for (const col of columns) {
      const filter = col.meta?.filter
      if (filter === undefined || !('accessorKey' in col)) {
        continue
      }
      const value = next.find((f) => f.id === col.accessorKey)?.value as
        | ColumnFilterNode<FilterField>
        | undefined
      const conditions = value !== undefined ? getTopLevelConditions(value) : []
      for (const field of filterFields(filter)) {
        map.set(field, combine(conditions.filter((condition) => condition.field === field)))
      }
    }
    filterStore.setColumnFilters(map)
  }

  return { tableColumnFilters, onColumnFiltersUpdate }
}
