/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, shallowRef } from 'vue'

import type { ConditionNode, FilterField, FilterNode } from '@/monitoring/shared/api/types'

import { getTopLevelConditions, setCondition } from './filterNodeUtils'

export interface QuickFilterConfig {
  label: string
  filter: FilterNode
}

export interface QuickFilter {
  readonly label: string
  /** Derived: true when filterNode is the same reference as this chip's filter. */
  readonly isActive: ComputedRef<boolean>
  readonly filter: FilterNode
}

export class FilterStore {
  /** Single source of truth for all active filter conditions. */
  readonly filterNode: Ref<FilterNode | undefined>
  readonly chips: readonly QuickFilter[]

  constructor(chipConfigs: QuickFilterConfig[]) {
    this.filterNode = shallowRef(undefined)
    const filterNode = this.filterNode
    this.chips = chipConfigs.map((c) => ({
      label: c.label,
      isActive: computed(() => filterNode.value === c.filter),
      filter: c.filter
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

  /** Replace the entire filterNode with the chip's preset conditions. */
  activateChip(chip: QuickFilter): void {
    this.filterNode.value = chip.filter
  }

  /** Clear the entire filterNode. */
  deactivateChip(_chip: QuickFilter): void {
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
