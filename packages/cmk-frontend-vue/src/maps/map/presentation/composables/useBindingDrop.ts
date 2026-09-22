/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { PresentationElement, PresentationView } from '@/maps/types/api'

import {
  BINDING_DROP_MIME,
  applyBindingDrop,
  bindableElementAt,
  parseBindingDropPayload
} from '../bindingDrop'
import type { ElementById } from '../connectors'
import type { SlidePoint } from '../geometry'
import type { CanvasSelection } from './useCanvasSelection'

interface BindingDropOptions {
  interactive: Ref<boolean>
  view: Ref<PresentationView>
  elements: Ref<PresentationElement[]>
  byId: ElementById
  nextZ: Ref<number>
  selection: CanvasSelection
  screenToSlide: (clientX: number, clientY: number) => SlidePoint
  /** Adds a fresh element to the slide, as one history step. */
  add: (el: PresentationElement) => void
  /** Applies a binding to an element already on the slide. */
  patch: (el: PresentationElement, patch: Record<string, unknown>) => void
}

/**
 * Dragging a host, service, group or aggregation out of the data browser and
 * onto the slide. Dropping it on a bindable element binds that element;
 * dropping it anywhere else creates a live-status element there.
 *
 * The element under the pointer is highlighted while the drag is over the
 * slide, which is the same highlight a connector endpoint uses to show what it
 * would dock to -- so both share ``dockCandidateId``.
 */
export function useBindingDrop(options: BindingDropOptions) {
  const { interactive, view, elements, byId, nextZ, selection, screenToSlide, add, patch } = options

  const targetId = ref<string | null>(null)

  /** Where the binding lands; a drop on the gutter still hits the slide. */
  function point(e: DragEvent): SlidePoint {
    const p = screenToSlide(e.clientX, e.clientY)
    return {
      x: Math.min(view.value.width, Math.max(0, p.x)),
      y: Math.min(view.value.height, Math.max(0, p.y))
    }
  }

  function onDragOver(e: DragEvent): void {
    if (!interactive.value || !e.dataTransfer?.types.includes(BINDING_DROP_MIME)) {
      return
    }
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
    targetId.value = bindableElementAt(elements.value, point(e))?.id ?? null
  }

  function onDragLeave(): void {
    targetId.value = null
  }

  function onDrop(e: DragEvent): void {
    targetId.value = null
    if (!interactive.value) {
      return
    }
    const raw = e.dataTransfer?.getData(BINDING_DROP_MIME)
    const payload = raw ? parseBindingDropPayload(raw) : null
    if (!payload) {
      return
    }
    e.preventDefault()
    const result = applyBindingDrop(elements.value, point(e), payload, nextZ.value)
    if (result.kind === 'bind') {
      const el = byId(result.id)
      if (el) {
        patch(el, result.patch)
      }
      selection.setSelection([result.id])
    } else {
      add(result.element)
      selection.setSelection([result.element.id])
    }
  }

  return { targetId, onDragOver, onDragLeave, onDrop }
}
