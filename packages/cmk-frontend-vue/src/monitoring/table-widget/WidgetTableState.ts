/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState, VisibilityState } from '@tanstack/vue-table'
import { type Ref, ref } from 'vue'

import type { MonitoringTableState } from '@/monitoring/shared/components/MonitoringTableContext'

export class WidgetTableState implements MonitoringTableState {
  readonly sortState: Ref<SortingState>
  readonly columnVisibility: Ref<VisibilityState> = ref({})
  private initialSort: SortingState

  constructor(sort: readonly string[]) {
    this.initialSort = WidgetTableState.decodeSort(sort)
    this.sortState = ref([...this.initialSort])
  }

  reset(sort: readonly string[]): void {
    this.initialSort = WidgetTableState.decodeSort(sort)
    this.restoreInitialSort()
  }

  updateSort(sortState: SortingState): void {
    if (sortState.length === 0) {
      this.restoreInitialSort()
      return
    }
    this.sortState.value = sortState
  }

  encodedSort(): string[] {
    return this.sortState.value.map((entry) => `${entry.id}:${entry.desc ? 'desc' : 'asc'}`)
  }

  private restoreInitialSort(): void {
    this.sortState.value = [...this.initialSort]
  }

  private static decodeSort(sort: readonly string[]): SortingState {
    return sort.flatMap((token) => WidgetTableState.decodeSortEntry(token))
  }

  private static decodeSortEntry(token: string): SortingState {
    const [id, direction] = token.split(':')
    if (!id || (direction !== 'asc' && direction !== 'desc')) {
      return []
    }
    return [{ id, desc: direction === 'desc' }]
  }
}
