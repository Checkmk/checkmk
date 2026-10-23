/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * One tab stop for all the objects on a map, and the arrow keys to move between
 * them -- the roving tabindex the folder tree's list uses for its rows.
 *
 * A map can carry hundreds of objects; each its own tab stop puts all of them
 * between the operator and the controls after the map. The order is worst state
 * first, so the keyboard reaches the problems before anything else.
 *
 * The keys are taken at the map's own element, from whichever object they come
 * from, which is why an object only has to carry ``data-object-id``.
 */
import { computed, nextTick, ref } from 'vue'

import type { MapElement, ObjectState } from '@/maps/types/api'
import { stateRank } from '@/maps/utils/stateColors'

export interface RovingFocus {
  isTabStop: (id: string) => boolean
  onKeydown: (event: KeyboardEvent) => void
  /** Keeps the tab stop on the object last focused, by keyboard or pointer. */
  onFocusin: (event: FocusEvent) => void
}

function objectIdOf(target: EventTarget | null): string | null {
  const element =
    target instanceof HTMLElement ? target.closest<HTMLElement>('[data-object-id]') : null
  return element?.dataset['objectId'] ?? null
}

const collator = new Intl.Collator()

export function useRovingFocus(source: {
  objects: () => MapElement[]
  states: () => Record<string, ObjectState>
  nameOf: (object: MapElement) => string
  root: () => HTMLElement | null
  /** Bring the object into view when it takes the focus; the browser does not scroll to it. */
  reveal?: (object: MapElement) => void
}): RovingFocus {
  const activeId = ref<string | null>(null)

  function compare(states: Record<string, ObjectState>, a: MapElement, b: MapElement): number {
    return (
      stateRank(states[b.id]?.state) - stateRank(states[a.id]?.state) ||
      collator.compare(source.nameOf(a), source.nameOf(b))
    )
  }

  // One pass rather than a sort: every object reads this on every render, and
  // the states change every few seconds.
  const tabStop = computed(() => {
    const objects = source.objects()
    if (activeId.value !== null && objects.some((object) => object.id === activeId.value)) {
      return activeId.value
    }
    const states = source.states()
    let first: MapElement | undefined
    for (const object of objects) {
      if (first === undefined || compare(states, object, first) < 0) {
        first = object
      }
    }
    return first?.id ?? null
  })

  async function focus(object: MapElement): Promise<void> {
    activeId.value = object.id
    source.reveal?.(object)
    await nextTick()
    source
      .root()
      ?.querySelector<HTMLElement>(`[data-object-id="${CSS.escape(object.id)}"]`)
      ?.focus({ preventScroll: source.reveal !== undefined })
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.altKey || event.ctrlKey || event.metaKey) {
      return
    }
    const id = objectIdOf(event.target)
    if (id === null) {
      return
    }
    const states = source.states()
    const order = [...source.objects()].sort((a, b) => compare(states, a, b))
    const index = order.findIndex((object) => object.id === id)
    if (index < 0) {
      return
    }
    let target: number
    switch (event.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        target = Math.min(index + 1, order.length - 1)
        break
      case 'ArrowLeft':
      case 'ArrowUp':
        target = Math.max(index - 1, 0)
        break
      case 'Home':
        target = 0
        break
      case 'End':
        target = order.length - 1
        break
      default:
        return
    }
    event.preventDefault()
    const next = order[target]
    if (next !== undefined) {
      void focus(next)
    }
  }

  function onFocusin(event: FocusEvent): void {
    const id = objectIdOf(event.target)
    if (id === null) {
      return
    }
    activeId.value = id
    // Tabbing in lands on the worst state, wherever it is on the map.
    const object = source.objects().find((candidate) => candidate.id === id)
    if (object) {
      source.reveal?.(object)
    }
  }

  return { isTabStop: (id) => tabStop.value === id, onKeydown, onFocusin }
}
