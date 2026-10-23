/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import type { PresentationElement, PresentationView } from '@/maps/types/api'

import { type AlignMode, alignedPosition, distributedPositions } from '../alignment'
import { type ElementSelection, collectWithChildren, instantiate } from '../clipboard'
import { type ElementById, undockFrom } from '../connectors'
import { type InsertKind, createElement, newElementId } from '../elements'
import type { Box, SlidePoint } from '../geometry'
import type { PresentationTemplate } from '../templates'
import type { CanvasSelection } from './useCanvasSelection'

interface EditingOptions {
  view: Ref<PresentationView>
  elements: Ref<PresentationElement[]>
  byId: ElementById
  isLocked: (el: PresentationElement) => boolean
  nextZ: Ref<number>
  selection: CanvasSelection
  selectionBox: Ref<Box | null>
  /** The undo stack's revision -- see ``nudge``. */
  historyVersion: Ref<number>
  /** Records an undo step, runs the change, and schedules the save. */
  mutate: (change: () => void) => void
  setElements: (next: PresentationElement[]) => void
  snapshot: () => void
  scheduleSave: () => void
}

/** New elements land near the middle, fanned out so a run of them is visible. */
const INSERT_FAN = 16
const INSERT_FAN_PERIOD = 6

/** Held arrow-key repeats within this many ms coalesce into one undo step. */
const NUDGE_COALESCE_MS = 600

/**
 * Everything the editor does to the slide's elements. Each operation goes
 * through the document's ``mutate`` pipeline, so history and persistence stay
 * uniform no matter which panel, shortcut or toolbar triggered it.
 */
export function useSlideEditing(options: EditingOptions) {
  const {
    view,
    elements,
    byId,
    isLocked,
    nextZ,
    selection,
    selectionBox,
    historyVersion,
    mutate,
    setElements,
    snapshot,
    scheduleSave
  } = options

  function add(el: PresentationElement): void {
    mutate(() => setElements([...elements.value, el]))
  }

  function insert(kind: InsertKind): void {
    const fan = (elements.value.length % INSERT_FAN_PERIOD) * INSERT_FAN
    const el = createElement(
      kind,
      Math.round(view.value.width / 2 - 100 + fan),
      Math.round(view.value.height / 2 - 70 + fan)
    )
    el.z = nextZ.value
    add(el)
    selection.setSelection([el.id])
    if (kind === 'text') {
      selection.editingTextId.value = el.id
    }
  }

  function remove(): void {
    if (!selection.selectedIds.value.length) {
      return
    }
    const doomed = new Set(selection.moving())
    mutate(() => {
      const survivors = elements.value.filter((el) => !doomed.has(el.id))
      undockFrom(survivors, doomed, byId)
      setElements(survivors)
    })
    selection.clear()
  }

  /** Clone a set of elements onto the slide and leave the clones selected. */
  function cloneOnto(source: ElementSelection): void {
    const { copies, newTops } = instantiate(source, nextZ.value)
    mutate(() => setElements([...elements.value, ...copies]))
    selection.setSelection(newTops)
  }

  function duplicate(): void {
    if (selection.selectedIds.value.length) {
      cloneOnto(collectWithChildren(selection.selectedIds.value, byId))
    }
  }

  let clipboard: ElementSelection = { els: [], tops: [] }
  function copy(): void {
    clipboard = collectWithChildren(selection.selectedIds.value, byId)
  }
  function paste(): void {
    if (clipboard.els.length) {
      cloneOnto(clipboard)
    }
  }

  /**
   * Arrow-key nudge, a design-tool staple. Held repeats coalesce into one undo
   * step (like a drag), and an all-locked selection is a no-op so it cannot
   * spam empty history entries.
   *
   * A repeat only joins the step it started, so anything that moved the undo
   * stack in between (an undo, or an edit from elsewhere) ends the run: joining
   * a step that is no longer on top would change the slide without a history
   * entry of its own and leave a redo pointing at an unrelated state.
   */
  let lastNudgeAt = 0
  let nudgeVersion = -1
  function nudge(dx: number, dy: number): void {
    const movable = selection
      .moving()
      .map(byId)
      .filter((el): el is PresentationElement => !!el && !isLocked(el))
    if (!movable.length) {
      return
    }
    const now = Date.now()
    if (now - lastNudgeAt > NUDGE_COALESCE_MS || historyVersion.value !== nudgeVersion) {
      snapshot()
    }
    lastNudgeAt = now
    nudgeVersion = historyVersion.value
    for (const el of movable) {
      el.x += dx
      el.y += dy
    }
    scheduleSave()
  }

  /**
   * An inspector patch applies to the whole selection: a single element gets
   * its own fields, a multi-selection shares the patched subset (opacity, say).
   */
  function patchSelection(patch: Record<string, unknown>): void {
    const els = selection.selectedElements.value
    if (els.length) {
      mutate(() => els.forEach((el) => Object.assign(el, patch)))
    }
  }

  function patchElement(el: PresentationElement, patch: Record<string, unknown>): void {
    mutate(() => Object.assign(el, patch))
  }

  /**
   * Blur always reports the text so editing reliably ends, but only an actual
   * change records a history step -- a no-op blur must not spam undo or saves.
   */
  function setText(id: string, text: string): void {
    const el = byId(id)
    if (el?.kind === 'text' && text !== el.text) {
      mutate(() => {
        el.text = text
      })
    }
    selection.editingTextId.value = null
  }

  function toggleLock(id: string): void {
    const el = byId(id)
    if (el) {
      patchElement(el, { locked: !el.locked })
    }
  }
  function toggleHidden(id: string): void {
    const el = byId(id)
    if (el) {
      patchElement(el, { hidden: !el.hidden })
    }
  }

  function group(): void {
    const box = selectionBox.value
    if (selection.selectedIds.value.length < 2 || !box) {
      return
    }
    const grouped: PresentationElement = {
      id: newElementId('group'),
      kind: 'group',
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
      rotation: 0,
      z: nextZ.value,
      opacity: 1,
      locked: false,
      hidden: false,
      name: null,
      children: [...selection.selectedIds.value]
    }
    add(grouped)
    selection.setSelection([grouped.id])
  }

  function ungroup(): void {
    const groups = selection.selectedElements.value
      .filter((el) => el.kind === 'group')
      .map((el) => el.id)
    if (!groups.length) {
      return
    }
    mutate(() => setElements(elements.value.filter((el) => !groups.includes(el.id))))
    selection.clear()
  }

  /**
   * Put a top-level element down at ``to``. Writing a group's own x/y only moves
   * its outline, so the delta widens to its members -- the same widening the
   * drag path and ``nudge`` do.
   */
  function moveTo(el: PresentationElement, to: SlidePoint): void {
    const dx = to.x - el.x
    const dy = to.y - el.y
    for (const id of selection.withDescendants([el.id])) {
      const member = byId(id)
      if (member) {
        member.x += dx
        member.y += dy
      }
    }
  }

  function align(mode: AlignMode): void {
    const box = selectionBox.value
    if (!box) {
      return
    }
    mutate(() =>
      selection.selectedElements.value.forEach((el) => moveTo(el, alignedPosition(el, box, mode)))
    )
  }

  function distribute(axis: 'x' | 'y'): void {
    const positions = distributedPositions(selection.selectedElements.value, axis)
    if (!positions.size) {
      return
    }
    mutate(() =>
      selection.selectedElements.value.forEach((el) => {
        const at = positions.get(el.id)
        if (at !== undefined) {
          moveTo(el, axis === 'x' ? { x: at, y: el.y } : { x: el.x, y: at })
        }
      })
    )
  }

  /**
   * A template swaps theme and elements in ONE history step, so a single undo
   * puts the previous slide back.
   */
  function applyTemplate(template: PresentationTemplate): void {
    selection.clear()
    mutate(() => {
      view.value = { ...view.value, theme: template.theme, elements: template.build() }
    })
  }

  const canDistribute = computed(() => selection.selectedIds.value.length >= 3)

  return {
    insert,
    applyTemplate,
    add,
    remove,
    duplicate,
    copy,
    paste,
    nudge,
    patchSelection,
    patchElement,
    setText,
    toggleLock,
    toggleHidden,
    group,
    ungroup,
    align,
    distribute,
    canDistribute
  }
}
