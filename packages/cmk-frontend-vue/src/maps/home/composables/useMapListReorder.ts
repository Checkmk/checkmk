/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed } from 'vue'

import { useAuth, useMaps } from '@/maps/services/context'
import { useDragReorder } from '@/maps/shared/composables/useDragReorder'
import type { MapRead } from '@/maps/types/api'

/**
 * Dragging the cards into the order they should be listed in.
 *
 * Reorder operates on the FULL store list, never on a filtered subset —
 * ``sort_order`` is a per-owner concept, so the drag is only offered while the
 * displayed order matches the store's one to one (``orderIsPristine``).
 */
export function useMapListReorder(
  orderIsPristine: () => boolean
): { isEnabled: ComputedRef<boolean> } & ReturnType<typeof useDragReorder<MapRead>> {
  const auth = useAuth()
  const maps = useMaps()

  const isEnabled = computed(() => auth.isAdmin.value && orderIsPristine())

  function persist(): void {
    const order = maps.maps.value.map((map, index) => ({ name: map.name, sort_order: index }))
    // A failed write leaves the list showing an order the server does not have,
    // so re-read it rather than keeping the optimistic one.
    maps.reorderMaps(order).catch(() => maps.fetchMaps())
  }

  return {
    isEnabled,
    ...useDragReorder<MapRead>(
      () => maps.maps.value,
      (list) => {
        maps.maps.value.splice(0, maps.maps.value.length, ...list)
      },
      persist,
      () => isEnabled.value
    )
  }
}
