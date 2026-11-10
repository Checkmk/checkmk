/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import { type Ref, computed, ref, watch } from 'vue'

import { loadMenu } from '../api/burgerMenu'
import type { ValueRange } from '../components/TimeSeriesGraph/types'
import type { ConsolidationFn } from '../components/consolidation'
import type { BurgerMenuCallable, BurgerMenuGroup, RequestedTimeRange } from '../types'

/**
 * The graph burger (action) menu, shared by every graph surface that offers one.
 * The menu is (re)loaded whenever the add type changes and cleared when disabled; the add-to
 * target can be null at first render (e.g. for custom graphs), which hides the menu.
 */
export function useBurgerMenu(
  getAddTo: () => AddTo | null | undefined,
  getEnabled: () => boolean,
  getDisplayedRange: () => RequestedTimeRange,
  getConsolidationFn: () => ConsolidationFn,
  getValueRange: () => ValueRange | null
): {
  showBurgerMenu: Ref<boolean>
  burgerMenuGroups: Ref<BurgerMenuGroup[]>
  triggerBurgerMenuAction: (onClick: BurgerMenuCallable) => Promise<void>
} {
  const addTo = computed(() => getAddTo() ?? null)
  const enabled = computed(() => getEnabled())
  const showBurgerMenu = computed(() => addTo.value !== null && enabled.value)
  const burgerMenuGroups = ref<BurgerMenuGroup[]>([])

  watch(
    [enabled, () => addTo.value?.type ?? null, () => addTo.value?.internal ?? null],
    ([isEnabled, addType]) => {
      if (!isEnabled || addType === null) {
        burgerMenuGroups.value = []
        return
      }
      loadMenu(addType)
        .then((groups) => {
          burgerMenuGroups.value = groups
        })
        .catch((err: unknown) => {
          // Reported rather than raised: a failed load leaves the menu empty instead of tearing
          // the surface down, and the next refetch of the target retries loading the menu.
          console.error(`Failed to load the burger menu for add type "${addType}":`, err)
        })
    },
    { immediate: true }
  )

  const triggerBurgerMenuAction = async (onClick: BurgerMenuCallable): Promise<void> => {
    const target = addTo.value
    if (target === null) {
      throw new Error('A burger menu action needs the add-to target the menu was assembled for')
    }
    const range = getDisplayedRange()
    await onClick({
      specification: target.specification,
      internal: target.internal,
      timeStart: range.start,
      timeEnd: range.end,
      consolidationFunction: getConsolidationFn(),
      valueRange: getValueRange() ?? undefined
    })
  }

  return { showBurgerMenu, burgerMenuGroups, triggerBurgerMenuAction }
}
