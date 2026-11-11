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

/**
 * Bridges a FilterStore (keyed by the fields a column filters on) with TanStack
 * Table's column filter state (column-ID-centric). Derives the table's displayed column filters from the store
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
  const filteredColumns = columns.flatMap((col) =>
    col.meta?.filter !== undefined && 'accessorKey' in col
      ? [{ id: col.accessorKey as string, fields: filterFields(col.meta.filter) }]
      : []
  )

  const tableColumnFilters = computed<ColumnFiltersState>(() =>
    filteredColumns.flatMap(({ id, fields }) => {
      const value = filterStore.getColumnFilter(...fields)
      return value !== undefined ? [{ id, value }] : []
    })
  )

  function onColumnFiltersUpdate(next: ColumnFiltersState): void {
    filterStore.setColumnFilters(
      filteredColumns.map(
        ({ id, fields }) =>
          [
            fields,
            next.find((f) => f.id === id)?.value as ColumnFilterNode<FilterField> | undefined
          ] as const
      )
    )
  }

  return { tableColumnFilters, onColumnFiltersUpdate }
}
