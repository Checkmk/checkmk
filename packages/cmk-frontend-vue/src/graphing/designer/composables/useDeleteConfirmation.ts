/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed, ref } from 'vue'

import type { FormulaItem, ItemId } from '../types'
import type { GraphItemsStore } from './useGraphItems'

export interface DeleteTarget {
  id: ItemId
  /** The resolved title, or the id while the row has none. */
  name: string
}

export interface PendingDelete {
  targets: readonly DeleteTarget[]
  /** The formulas that (transitively) reference the targets and are deleted along with them. */
  dependents: readonly FormulaItem[]
  /** Whether the targets are every row of the graph, and more than one. */
  all: boolean
}

export interface DeleteConfirmation {
  /** The delete awaiting confirmation; null otherwise. */
  pending: ComputedRef<PendingDelete | null>
  /** Stores `ids` and the formulas that reference them as `pending`. */
  request: (ids: readonly ItemId[]) => void
  /** Deletes the pending rows together with their dependents. */
  confirm: () => void
  cancel: () => void
}

/**
 * The delete flow shared by the metrics table and the calculation slideout.
 * @param onRemoved Called with the removed ids after every removal.
 */
export function useDeleteConfirmation(
  store: GraphItemsStore,
  getResolvedTitles: () => ReadonlyMap<ItemId, string>,
  onRemoved: (ids: readonly ItemId[]) => void = () => {}
): DeleteConfirmation {
  const pending = ref<PendingDelete | null>(null)

  function request(ids: readonly ItemId[]): void {
    const idSet = new Set(ids)
    const dependentById = new Map(
      ids.flatMap((id) =>
        store.dependentsOf(id).map((dependent) => [dependent.id, dependent] as const)
      )
    )
    const resolvedTitles = getResolvedTitles()
    pending.value = {
      targets: ids.map((id) => ({ id, name: resolvedTitles.get(id) ?? id })),
      dependents: [...dependentById.values()].filter((dependent) => !idSet.has(dependent.id)),
      all: ids.length > 1 && ids.length === store.items.value.length
    }
  }

  function confirm(): void {
    if (pending.value !== null) {
      const ids = [
        ...pending.value.targets.map((target) => target.id),
        ...pending.value.dependents.map((dependent) => dependent.id)
      ]
      store.removeMany(ids)
      onRemoved(ids)
      pending.value = null
    }
  }

  function cancel(): void {
    pending.value = null
  }

  return { pending: computed(() => pending.value), request, confirm, cancel }
}
