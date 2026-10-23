/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { MarqueeRect } from '@/maps/map/composables/useMarquee'
import type { PresentationElement } from '@/maps/types/api'

import { type ElementById, elementBounds } from '../connectors'

interface SelectionOptions {
  elements: Ref<PresentationElement[]>
  byId: ElementById
  /** The group an element belongs to, if any -- selection is per group. */
  topLevelId: (id: string) => string
  isGrouped: (id: string) => boolean
  isLocked: (el: PresentationElement) => boolean
}

/**
 * What the editor currently has hold of: the selected elements and the inline
 * text edit, which is mutually exclusive with a selection change (picking
 * anything else commits the text being typed).
 *
 * Selection is always of top-level elements: clicking a group member selects
 * its group. ``moving`` widens that back out to what physically moves when the
 * selection is dragged, which is the group's members as well.
 */
export function useCanvasSelection(options: SelectionOptions) {
  const { elements, byId, topLevelId, isGrouped, isLocked } = options

  const selectedIds = ref<string[]>([])
  const editingTextId = ref<string | null>(null)

  const selectedElements = computed(() =>
    selectedIds.value.map(byId).filter((el): el is PresentationElement => !!el)
  )
  const hasLocked = computed(() => selectedElements.value.some(isLocked))
  // A marquee rewrites the selection on every frame and the templates ask
  // "is this one selected?" once per element, so that question gets a Set.
  const selectedIdSet = computed(() => new Set(selectedIds.value))

  function select(id: string): void {
    editingTextId.value = null
    selectedIds.value = [id]
  }

  function toggle(id: string): void {
    editingTextId.value = null
    selectedIds.value = selectedIds.value.includes(id)
      ? selectedIds.value.filter((i) => i !== id)
      : [...selectedIds.value, id]
  }

  function setSelection(ids: string[]): void {
    editingTextId.value = null
    selectedIds.value = ids
  }

  function clear(): void {
    editingTextId.value = null
    selectedIds.value = []
  }

  /**
   * Clicking an element: shift extends the selection, a plain click on an
   * already-selected element keeps the selection (so a multi-selection can be
   * dragged as a whole).
   */
  function pick(el: PresentationElement, extend: boolean): void {
    const id = topLevelId(el.id)
    if (extend) {
      toggle(id)
    } else if (!selectedIds.value.includes(id)) {
      select(id)
    } else {
      editingTextId.value = null
    }
  }

  /**
   * The given elements plus everything nested inside them. Groups nest, so this
   * descends: stopping at the first level would move an inner group's box and
   * leave its members behind.
   */
  function withDescendants(ids: string[]): string[] {
    const out = new Set<string>()
    const walk = (id: string): void => {
      if (out.has(id)) {
        return
      }
      out.add(id)
      const el = byId(id)
      if (el?.kind === 'group') {
        el.children.forEach(walk)
      }
    }
    ids.forEach(walk)
    return [...out]
  }

  /** The elements a drag of the current selection actually moves. */
  function moving(): string[] {
    return withDescendants(selectedIds.value)
  }

  /** Everything the rubber band touches, added to the selection when additive. */
  function applyMarquee(rect: MarqueeRect, additive: boolean): void {
    const hits = elements.value
      .filter((el) => !isGrouped(el.id))
      .filter((el) => {
        // Not el.x/y/w/h: a connector's own box is vestigial, so the band has
        // to test the box its endpoints span.
        const b = elementBounds(el, byId)
        return (
          b.x < rect.left + rect.width &&
          b.x + b.w > rect.left &&
          b.y < rect.top + rect.height &&
          b.y + b.h > rect.top
        )
      })
      .map((el) => el.id)
    selectedIds.value = additive ? [...new Set([...selectedIds.value, ...hits])] : hits
  }

  return {
    selectedIds,
    selectedIdSet,
    selectedElements,
    editingTextId,
    hasLocked,
    select,
    toggle,
    setSelection,
    clear,
    pick,
    withDescendants,
    moving,
    applyMarquee
  }
}

export type CanvasSelection = ReturnType<typeof useCanvasSelection>
