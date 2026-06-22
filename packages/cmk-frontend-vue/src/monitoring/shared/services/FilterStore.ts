/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, ref, shallowRef } from 'vue'

import type { ConditionNode, FilterField, FilterNode } from '@/monitoring/shared/api/types'

import { filterNodesEqual, getTopLevelConditions, setCondition } from './filterNodeUtils'

export interface QuickFilterConfig {
  label: string
  /** Preset conditions applied when the quick filter is activated. Omit for an empty filter. */
  filter?: FilterNode
  /**
   * Search query applied when the quick filter is activated. Set to `''` to clear the search
   * box (e.g. the "All" quick filter). Omit to leave the current search query untouched.
   */
  searchQuery?: string
}

export interface QuickFilter {
  readonly label: string
  /** Derived: true when both the filter and search query match this quick filter's preset. */
  readonly isActive: ComputedRef<boolean>
  readonly filter: FilterNode | undefined
  readonly searchQuery: string | undefined
}

export class FilterStore {
  /** Single source of truth for all active filter conditions. */
  readonly filterNode: Ref<FilterNode | undefined>
  readonly quickFilters: readonly QuickFilter[]

  constructor(quickFilterConfigs: QuickFilterConfig[], searchQuery: Ref<string> = ref('')) {
    this.filterNode = shallowRef(undefined)
    const filterNode = this.filterNode
    this.quickFilters = quickFilterConfigs.map((c) => ({
      label: c.label,
      isActive: computed(
        () =>
          filterNodesEqual(filterNode.value, c.filter) &&
          (c.searchQuery === undefined || searchQuery.value === c.searchQuery)
      ),
      filter: c.filter,
      searchQuery: c.searchQuery
    }))
  }

  getColumnCondition(field: FilterField): ConditionNode | undefined {
    return this.filterNode.value !== undefined
      ? getTopLevelConditions(this.filterNode.value).find((c) => c.field === field)
      : undefined
  }

  /** Batch-update column conditions. Fields mapped to `undefined` are cleared. */
  setColumnConditions(map: Map<FilterField, ConditionNode | undefined>): void {
    let node = this.filterNode.value
    for (const [field, condition] of map) {
      node = setCondition(node, field, condition)
    }
    this.filterNode.value = node
  }

  /** Replace the entire filterNode with the quick filter's preset conditions. */
  activateQuickFilter(quickFilter: QuickFilter): void {
    this.filterNode.value = quickFilter.filter
  }

  /** Clear the entire filterNode. */
  deactivateQuickFilter(_quickFilter: QuickFilter): void {
    this.filterNode.value = undefined
  }

  /** Direct write for a future query-filter UI. */
  setQueryNode(node: FilterNode | undefined): void {
    this.filterNode.value = node
  }

  get activeFilterCount(): number {
    return this.filterNode.value !== undefined
      ? getTopLevelConditions(this.filterNode.value).length
      : 0
  }
}
