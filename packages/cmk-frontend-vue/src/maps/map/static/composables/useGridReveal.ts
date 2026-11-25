/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Which grid a viewer points into. Outside the editor a grid draws only its
 * objects, as NagVis does, so two grids side by side read as one; pointing at
 * an object shows the frame of its grid until the pointer has left the grid's
 * objects for a moment, so moving from one to the next keeps it.
 */
import { computed, ref } from 'vue'

import { gridIdOfMember } from '@/maps/api/wire'
import { useHoverGrace } from '@/maps/map/composables/useHoverGrace'
import type { MapElement } from '@/maps/types/api'

export function useGridReveal(source: {
  objects: () => readonly MapElement[]
  /** The objects drawn; one that is gone takes its grid's frame with it. */
  shown: () => readonly MapElement[]
}) {
  const memberId = ref<string | null>(null)
  const grace = useHoverGrace(() => {
    memberId.value = null
  })

  function enter(object: MapElement): void {
    grace.cancelClose()
    memberId.value = object.id
  }

  const grid = computed(() => {
    const id = memberId.value
    const gridId = id === null ? null : gridIdOfMember(id)
    if (gridId === null || !source.shown().some((o) => o.id === id)) {
      return null
    }
    return source.objects().find((o) => o.id === gridId) ?? null
  })

  return { grid, enter, leave: grace.scheduleClose }
}
