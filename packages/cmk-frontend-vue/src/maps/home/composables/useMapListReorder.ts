/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed } from 'vue'

import { byStoredOrder } from '@/maps/home/composables/useMapListFilter'
import { useAuth, useMaps } from '@/maps/services/context'
import { useDragReorder } from '@/maps/shared/composables/useDragReorder'
import type { MapRead } from '@/maps/types/api'
import { mapOwnerKind } from '@/maps/utils/mapVisibility'

export interface MapListReorder {
  isDraggable: (map: MapRead) => boolean
  isDragging: (map: MapRead) => boolean
  onDragStart: (event: DragEvent, map: MapRead) => void
  onDragOver: (event: DragEvent, map: MapRead) => void
  onDrop: (event: DragEvent) => void
  onDragEnd: (event: DragEvent) => void
}

/**
 * Dragging your own cards into the order they should be listed in.
 *
 * ``sort_order`` is per owner, and only your own maps are yours to write, so a
 * drag orders those among themselves; the maps of other users and the built-in
 * ones keep their place. It is offered only while no search hides some of them.
 */
export function useMapListReorder(orderIsPristine: () => boolean): MapListReorder {
  const auth = useAuth()
  const maps = useMaps()

  const ownMaps: ComputedRef<MapRead[]> = computed(() => {
    if (!orderIsPristine()) {
      return []
    }
    const userId = auth.user.value?.user_id
    return maps.maps.value
      .filter((map) => map.can_edit === true && mapOwnerKind(map, userId) === 'you')
      .sort(byStoredOrder)
  })

  function stamp(list: readonly MapRead[]): void {
    list.forEach((map, index) => {
      map.sort_order = index
    })
  }

  function persist(): void {
    const order = ownMaps.value.map((map, index) => ({ name: map.name, sort_order: index }))
    // A failed write leaves the list showing an order the server does not have,
    // so re-read it rather than keeping the optimistic one.
    maps.reorderMaps(order).catch(() => maps.fetchMaps())
  }

  const drag = useDragReorder<MapRead>(() => ownMaps.value, stamp, persist)

  function indexOf(map: MapRead): number {
    return ownMaps.value.findIndex((own) => own.name === map.name)
  }

  return {
    isDraggable: (map) => indexOf(map) !== -1,
    isDragging: (map) => drag.dragIndex.value !== null && drag.dragIndex.value === indexOf(map),
    onDragStart: (event, map) => {
      const index = indexOf(map)
      if (index !== -1) {
        drag.onDragStart(event, index)
      }
    },
    onDragOver: (event, map) => {
      const index = indexOf(map)
      if (index !== -1) {
        drag.onDragOver(event, index)
      }
    },
    onDrop: drag.onDrop,
    onDragEnd: drag.onDragEnd
  }
}
