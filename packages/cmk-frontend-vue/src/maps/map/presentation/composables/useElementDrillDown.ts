/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { Ref } from 'vue'

import type { MapElement, ObjectState, PresentationElement } from '@/maps/types/api'
import { objectAriaLabel } from '@/maps/utils/objectAria'

import { type BindableElement, isBoundElement } from '../binding'
import { mapElementFromElement } from '../objects'

/** What the view around the slide does with a drilled-down element. */
interface DrillDownEmits {
  (e: 'object-hover', object: MapElement, event: MouseEvent): void
  (e: 'object-hover-leave'): void
  (e: 'object-click', object: MapElement, event: MouseEvent | undefined): void
  (e: 'object-context', object: MapElement, event: MouseEvent): void
}

interface DrillDownOptions {
  /** True while the slide is being edited -- a drill-down would be in the way. */
  interactive: Ref<boolean>
  preview: () => boolean
  /** Effective connection of an element: its own override or the map default. */
  connectionFor: (el: PresentationElement) => string | null
  stateFor: (el: PresentationElement) => ObjectState | undefined
}

/**
 * Outside the editor a bound element behaves like a map object: hovering opens
 * the hover card, clicking follows the object-click contract, right-clicking
 * opens the navigation menu. Everything else on the slide stays decoration.
 *
 * The bridge is a transient ``MapElement`` synthesised from the element's
 * binding, so the shared surfaces work on presentation maps without knowing
 * anything about the slide model.
 */
export function useElementDrillDown(options: DrillDownOptions, emit: DrillDownEmits) {
  const { _t } = usei18n()
  const { interactive, preview, connectionFor, stateFor } = options

  /** Whether this element is a drill-down target at all. */
  function isLinked(el: PresentationElement): el is BindableElement {
    return !interactive.value && !preview() && isBoundElement(el)
  }

  function objectFor(el: PresentationElement): MapElement | null {
    if (!isLinked(el)) {
      return null
    }
    const obj = mapElementFromElement(el)
    return obj ? { ...obj, connection_id: connectionFor(el) } : null
  }

  function ariaLabel(el: PresentationElement): string | undefined {
    const obj = objectFor(el)
    return obj ? objectAriaLabel(_t, obj, stateFor(el)?.state) : undefined
  }

  function onHoverEnter(el: PresentationElement, event: MouseEvent): void {
    const obj = objectFor(el)
    if (obj) {
      emit('object-hover', obj, event)
    }
  }

  function onHoverLeave(el: PresentationElement): void {
    if (isLinked(el)) {
      emit('object-hover-leave')
    }
  }

  function onClick(el: PresentationElement, event?: MouseEvent): void {
    const obj = objectFor(el)
    if (obj) {
      emit('object-click', obj, event)
    }
  }

  function onKeydown(el: PresentationElement, event: KeyboardEvent): void {
    if (!isLinked(el) || (event.key !== 'Enter' && event.key !== ' ')) {
      return
    }
    event.preventDefault()
    onClick(el)
  }

  // Right-click drills down on bound elements; the editor keeps the browser
  // menu, since it has its own affordances for element actions.
  function onContextMenu(el: PresentationElement, event: MouseEvent): void {
    const obj = objectFor(el)
    if (!obj) {
      return
    }
    event.preventDefault()
    emit('object-context', obj, event)
  }

  return { isLinked, ariaLabel, onHoverEnter, onHoverLeave, onClick, onKeydown, onContextMenu }
}
