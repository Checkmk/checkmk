/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ColumnDef, type ColumnFiltersState } from '@tanstack/vue-table'
import { type ComputedRef, computed } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import type { FilterStore } from './FilterStore'

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
      const field = col.meta?.filter?.field
      if (field === undefined || !('accessorKey' in col)) {
        return []
      }
      const condition = filterStore.getColumnFilter(field)
      return condition !== undefined ? [{ id: col.accessorKey as string, value: condition }] : []
    })
  )

  function onColumnFiltersUpdate(next: ColumnFiltersState): void {
    const map = new Map<FilterField, ColumnFilterNode<FilterField> | undefined>()
    for (const col of columns) {
      const field = col.meta?.filter?.field
      if (field === undefined || !('accessorKey' in col)) {
        continue
      }
      const id = col.accessorKey as string
      const entry = next.find((f) => f.id === id)
      map.set(field, entry?.value as ColumnFilterNode<FilterField> | undefined)
    }
    filterStore.setColumnFilters(map)
  }

  return { tableColumnFilters, onColumnFiltersUpdate }
}
