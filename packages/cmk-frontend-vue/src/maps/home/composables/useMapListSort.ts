/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { hasDynamicContent, mapOwnerLabel, mapVisibilityLabel } from '@/maps/home/mapLabels'
import type { MapRead } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'

export type MapSortColumn = 'name' | 'type' | 'owner' | 'visibility' | 'connection' | 'objects'
export type SortDirection = 'asc' | 'desc'

/**
 * Which column the map table is sorted by.
 *
 * Unsorted is a state of its own: the list then keeps the order the home view
 * handed it (yours → others → built-in, each in its stored sort order), which is
 * what a drag-reorder persists.
 */
export function useMapListSort(
  maps: () => readonly MapRead[],
  currentUserId: () => string | undefined,
  _t: TranslateFn
): {
  column: Readonly<Ref<MapSortColumn | null>>
  direction: Readonly<Ref<SortDirection>>
  sortedMaps: ComputedRef<readonly MapRead[]>
  toggleColumn: (column: MapSortColumn) => void
  ariaSort: (column: MapSortColumn) => 'ascending' | 'descending' | 'none'
} {
  const column = ref<MapSortColumn | null>(null)
  const direction = ref<SortDirection>('asc')

  function sortKey(map: MapRead, by: MapSortColumn): string | number {
    switch (by) {
      case 'name':
        return (map.alias || map.name).toLowerCase()
      case 'type':
        return map.view.type
      case 'owner':
        return mapOwnerLabel(map, currentUserId(), _t).toLowerCase()
      case 'visibility':
        return mapVisibilityLabel(map, _t)
      case 'connection':
        return (map.connection_id || '').toLowerCase()
      case 'objects':
        // A computed map has no count to compare, so it sorts last.
        return hasDynamicContent(map) ? Number.MAX_SAFE_INTEGER : map.object_count
    }
  }

  const sortedMaps = computed<readonly MapRead[]>(() => {
    const by = column.value
    if (by === null) {
      return maps()
    }
    const factor = direction.value === 'asc' ? 1 : -1
    // Each key is derived once per map rather than once per comparison — the
    // owner key costs a translation lookup, and a comparison sort would ask for
    // it O(n log n) times.
    return maps()
      .map((map) => ({ map, key: sortKey(map, by) }))
      .sort((a, b) => {
        if (a.key < b.key) {
          return -factor
        }
        if (a.key > b.key) {
          return factor
        }
        return 0
      })
      .map((entry) => entry.map)
  })

  function toggleColumn(next: MapSortColumn): void {
    if (column.value === next) {
      direction.value = direction.value === 'asc' ? 'desc' : 'asc'
      return
    }
    column.value = next
    direction.value = 'asc'
  }

  function ariaSort(of: MapSortColumn): 'ascending' | 'descending' | 'none' {
    if (column.value !== of) {
      return 'none'
    }
    return direction.value === 'asc' ? 'ascending' : 'descending'
  }

  return { column, direction, sortedMaps, toggleColumn, ariaSort }
}
